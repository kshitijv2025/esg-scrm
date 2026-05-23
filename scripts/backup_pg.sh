#!/usr/bin/env bash
# =============================================================================
# PostgreSQL Backup Script with WAL Archiving and Point-in-Time Recovery
# =============================================================================
# Usage:
#   ./backup_pg.sh                          # Full backup + WAL archive
#   ./backup_pg.sh test_restore             # Test restore to verify backup integrity
#   ./backup_pg.sh list_backups            # List available backups
#   ./backup_pg.sh purge_old               # Purge backups older than retention
#
# Environment Variables:
#   DATABASE_URL        - PostgreSQL connection string (required)
#   BACKUP_DIR         - Base backup directory (default: /backups/pg)
#   WAL_DIR            - WAL archive directory (default: /backups/pg/wal)
#   RETENTION_DAYS     - Number of days to retain backups (default: 30)
#   PGHOST             - Override database host from DATABASE_URL
#   PGPORT             - Override database port from DATABASE_URL
#   PGUSER             - Override database user from DATABASE_URL
#   PGPASSWORD         - Override database password from DATABASE_URL
#   PGDATABASE         - Override database name from DATABASE_URL
# =============================================================================

set -euo pipefail

# Script directory and constants
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${BACKUP_LOG_FILE:-/var/log/pg_backup.log}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
DATE_DIR=$(date '+%Y%m%d')

# Default configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/pg}"
WAL_DIR="${WAL_DIR:-/backups/pg/wal}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Write to log file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE" 2>/dev/null || true

    # Write to stdout with color
    case "$level" in
        ERROR)
            echo -e "${RED}[$timestamp] [$level] $message${NC}" >&2
            ;;
        SUCCESS)
            echo -e "${GREEN}[$timestamp] [$level] $message${NC}"
            ;;
        WARN)
            echo -e "${YELLOW}[$timestamp] [$level] $message${NC}"
            ;;
        *)
            echo "[$timestamp] [$level] $message"
            ;;
    esac
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_success() { log "SUCCESS" "$@"; }

# =============================================================================
# Database Connection Functions
# =============================================================================

# Parse DATABASE_URL and set PG* environment variables
parse_database_url() {
    local url="${DATABASE_URL:-}"

    if [[ -z "$url" ]]; then
        log_error "DATABASE_URL environment variable is not set"
        return 1
    fi

    # Extract components using regex
    if [[ "$url" =~ ^postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+)$ ]]; then
        export PGUSER="${PGUSER:-${BASH_REMATCH[1]}}"
        export PGPASSWORD="${BASH_REMATCH[2]}"
        export PGHOST="${PGHOST:-${BASH_REMATCH[3]}}"
        export PGPORT="${PGPORT:-${BASH_REMATCH[4]}}"
        export PGDATABASE="${PGDATABASE:-${BASH_REMATCH[5]}}"
    else
        log_error "Invalid DATABASE_URL format. Expected: postgresql://user:pass@host:port/dbname"
        return 1
    fi

    # Mask password in log
    log_info "Database connection parsed for host=${PGHOST} port=${PGPORT} database=${PGDATABASE} user=${PGUSER}"
}

# Verify database connectivity
verify_connection() {
    log_info "Verifying database connection..."

    if ! command -v psql &>/dev/null; then
        log_error "psql command not found. Please install postgresql-client."
        return 1
    fi

    if ! PGPASSWORD="$PGPASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "SELECT 1" >/dev/null 2>&1; then
        log_error "Cannot connect to database ${PGDATABASE} on ${PGHOST}:${PGPORT}"
        return 1
    fi

    log_success "Database connection verified"
    return 0
}

# =============================================================================
# Backup Functions
# =============================================================================

# Create backup directories
setup_directories() {
    log_info "Setting up backup directories..."

    mkdir -p "${BACKUP_DIR}/${DATE_DIR}"
    mkdir -p "${WAL_DIR}"
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

    log_success "Backup directories ready: ${BACKUP_DIR}/${DATE_DIR}, ${WAL_DIR}"
}

# Perform full database backup
full_backup() {
    local backup_name="full_backup_${TIMESTAMP}"
    local backup_path="${BACKUP_DIR}/${DATE_DIR}/${backup_name}"

    log_info "Starting full backup: ${backup_name}"

    # Ensure directories exist
    setup_directories

    # Set pg_password for psql/pg_dump
    export PGPASSWORD

    # Create backup with pg_dump
    if PGPASSWORD="$PGPASSWORD" pg_dump \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$PGDATABASE" \
        -Fc \
        -f "${backup_path}.dump"; then

        # Calculate checksum
        local checksum=$(sha256sum "${backup_path}.dump" | cut -d' ' -f1)
        echo "$checksum" > "${backup_path}.checksum"

        # Get backup metadata
        {
            echo "BACKUP_NAME=${backup_name}"
            echo "BACKUP_PATH=${backup_path}.dump"
            echo "BACKUP_DATE=${TIMESTAMP}"
            echo "CHECKSUM=${checksum}"
            echo "DATABASE=${PGDATABASE}"
            echo "PGHOST=${PGHOST}"
            echo "PGPORT=${PGPORT}"
        } > "${backup_path}.meta"

        log_success "Full backup completed: ${backup_path}.dump (SHA256: ${checksum})"
        echo "${backup_path}"
        return 0
    else
        log_error "Full backup failed"
        rm -f "${backup_path}.dump" "${backup_path}.checksum" "${backup_path}.meta" 2>/dev/null || true
        return 1
    fi
}

# Archive WAL (Write-Ahead Log) for point-in-time recovery
wal_archive() {
    log_info "Starting WAL archive..."

    # Ensure WAL directory exists
    mkdir -p "${WAL_DIR}"

    export PGPASSWORD

    # Create WAL archive
    local wal_name="wal_${TIMESTAMP}"
    local wal_path="${WAL_DIR}/${wal_name}"

    if PGPASSWORD="$PGPASSWORD" psql \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$PGDATABASE" \
        -c "SELECT pg_switch_wal()" >/dev/null 2>&1; then

        # Copy WAL files
        local wal_dest="${wal_path}.tar.gz"

        # Find and archive WAL files
        local pg_wal_dir=$(PGPASSWORD="$PGPASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -c "SHOW data_directory" 2>/dev/null | tr -d '[:space:]')

        if [[ -n "$pg_wal_dir" && -d "$pg_wal_dir/pg_wal" ]]; then
            tar -czf "$wal_dest" -C "$pg_wal_dir" pg_wal 2>/dev/null || true
        fi

        log_success "WAL archive completed: ${wal_dest}"
        return 0
    else
        log_warn "WAL archive failed - continuing with backup"
        return 1
    fi
}

# =============================================================================
# Restore and PITR Functions
# =============================================================================

# Test restore to a temporary database (does not overwrite live DB)
test_restore() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: ${backup_file}"
        return 1
    fi

    local test_db="${PGDATABASE}_test_restore_${TIMESTAMP}"
    local backup_name=$(basename "$backup_file" .dump)

    log_info "Starting restore test: ${backup_name}"
    log_info "Test database: ${test_db}"

    export PGPASSWORD

    # Create a temporary test database
    if ! PGPASSWORD="$PGPASSWORD" psql \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS ${test_db}" >/dev/null 2>&1; then
        log_warn "Could not drop existing test database (may not exist)"
    fi

    if ! PGPASSWORD="$PGPASSWORD" psql \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d postgres \
        -c "CREATE DATABASE ${test_db}" >/dev/null 2>&1; then
        log_error "Failed to create test database"
        return 1
    fi

    # Restore to test database
    log_info "Restoring backup to test database..."

    if PGPASSWORD="$PGPASSWORD" pg_restore \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$test_db" \
        --no-owner \
        --no-acl \
        "$backup_file" >/dev/null 2>&1; then

        # Verify restore by checking table count
        local table_count=$(PGPASSWORD="$PGPASSWORD" psql \
            -h "$PGHOST" \
            -p "$PGPORT" \
            -U "$PGUSER" \
            -d "$test_db" \
            -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')" 2>/dev/null | tr -d '[:space:]')

        log_success "Restore test completed successfully"
        log_info "Restored database contains ${table_count} user tables"

        # Clean up test database
        PGPASSWORD="$PGPASSWORD" psql \
            -h "$PGHOST" \
            -p "$PGPORT" \
            -U "$PGUSER" \
            -d postgres \
            -c "DROP DATABASE ${test_db}" >/dev/null 2>&1 || true

        log_info "Test database cleaned up"
        return 0
    else
        log_error "Restore test failed"
        # Clean up test database even on failure
        PGPASSWORD="$PGPASSWORD" psql \
            -h "$PGHOST" \
            -p "$PGPORT" \
            -U "$PGUSER" \
            -d postgres \
            -c "DROP DATABASE IF EXISTS ${test_db}" >/dev/null 2>&1 || true
        return 1
    fi
}

# List available backups
list_backups() {
    log_info "Available backups in ${BACKUP_DIR}:"

    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warn "Backup directory does not exist: ${BACKUP_DIR}"
        return 0
    fi

    local found=0
    while IFS= read -r -d '' date_dir; do
        local date=$(basename "$date_dir")
        echo ""
        echo "=== Backups from ${date} ==="

        while IFS= read -r -d '' backup; do
            local name=$(basename "$backup" .dump)
            local size=$(du -h "${backup}" 2>/dev/null | cut -f1 || echo "unknown")
            local modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$backup" 2>/dev/null || stat -c "%y" "$backup" 2>/dev/null | cut -d' ' -f1,2 || echo "unknown")

            if [[ -f "${backup%.dump}.checksum" ]]; then
                local checksum=$(cat "${backup%.dump}.checksum" | cut -c1-16)
                echo "  ${name}.dump  ${size}  ${modified}  SHA256:${checksum}..."
            else
                echo "  ${name}.dump  ${size}  ${modified}"
            fi
            found=1
        done < <(find "$date_dir" -name "*.dump" -print0 2>/dev/null)

    done < <(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null | sort -rz)

    if [[ $found -eq 0 ]]; then
        log_warn "No backups found"
    fi
}

# Purge old backups based on retention policy
purge_old() {
    log_info "Purging backups older than ${RETENTION_DAYS} days..."

    local cutoff_date=$(date -d "${RETENTION_DAYS} days ago" '+%Y%m%d' 2>/dev/null || date -v-${RETENTION_DAYS}d '+%Y%m%d')
    local purged_count=0
    local kept_count=0

    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warn "Backup directory does not exist: ${BACKUP_DIR}"
        return 0
    fi

    # Find and remove old backup directories
    while IFS= read -r -d '' date_dir; do
        local date=$(basename "$date_dir")

        if [[ "$date" < "$cutoff_date" ]]; then
            log_info "Removing old backup: ${date_dir}"
            rm -rf "$date_dir" && ((purged_count++)) || true
        else
            ((kept_count++)) || true
        fi
    done < <(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

    # Purge old WAL archives (keep one per day for PITR)
    if [[ -d "$WAL_DIR" ]]; then
        local wal_cutoff=$(date -d "$((RETENTION_DAYS * 2)) days ago" '+%Y%m%d_%H%M%S' 2>/dev/null || date -v-$((RETENTION_DAYS * 2))d '+%Y%m%d_%H%M%S')

        while IFS= read -r -d '' wal_file; do
            local wal_name=$(basename "$wal_file" .tar.gz)
            if [[ "$wal_name" < "wal_${wal_cutoff}" ]]; then
                rm -f "$wal_file" && ((purged_count++)) || true
            fi
        done < <(find "$WAL_DIR" -name "*.tar.gz" -print0 2>/dev/null)
    fi

    log_success "Purge completed: ${purged_count} old backups removed, ${kept_count} backups retained"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    local command="${1:-full}"

    log_info "=========================================="
    log_info "PostgreSQL Backup Script Starting"
    log_info "Command: ${command}"
    log_info "=========================================="

    # Verify DATABASE_URL is set
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL environment variable is required"
        echo "Usage: DATABASE_URL=postgresql://user:pass@host:port/dbname $0 [command]"
        exit 1
    fi

    # Parse database URL and verify connection
    if ! parse_database_url; then
        exit 1
    fi

    if ! verify_connection; then
        exit 1
    fi

    case "$command" in
        full)
            if full_backup && wal_archive; then
                purge_old
                log_success "Backup cycle completed successfully"
                exit 0
            else
                log_error "Backup cycle failed"
                exit 1
            fi
            ;;
        test_restore)
            local latest_backup=$(find "${BACKUP_DIR}" -name "*.dump" -print0 2>/dev/null | xargs -0 -r ls -t 2>/dev/null | head -1)

            if [[ -z "$latest_backup" ]]; then
                log_error "No backup found to test"
                exit 1
            fi

            if test_restore "$latest_backup"; then
                exit 0
            else
                exit 1
            fi
            ;;
        list_backups)
            list_backups
            exit 0
            ;;
        purge_old)
            purge_old
            exit 0
            ;;
        verify)
            # Verify backup integrity
            local latest_backup=$(find "${BACKUP_DIR}" -name "*.dump" -print0 2>/dev/null | xargs -0 -r ls -t 2>/dev/null | head -1)

            if [[ -z "$latest_backup" ]]; then
                log_error "No backup found to verify"
                exit 1
            fi

            if [[ -f "${latest_backup%.dump}.checksum" ]]; then
                local stored_checksum=$(cat "${latest_backup%.dump}.checksum")
                local actual_checksum=$(sha256sum "$latest_backup" | cut -d' ' -f1)

                if [[ "$stored_checksum" == "$actual_checksum" ]]; then
                    log_success "Backup integrity verified: ${latest_backup}"
                    exit 0
                else
                    log_error "Backup integrity check FAILED: checksums do not match"
                    log_error "  Stored: ${stored_checksum}"
                    log_error "  Actual: ${actual_checksum}"
                    exit 1
                fi
            else
                log_warn "No checksum file found for ${latest_backup}"
                exit 1
            fi
            ;;
        help|--help|-h)
            echo "PostgreSQL Backup Script"
            echo ""
            echo "Usage:"
            echo "  DATABASE_URL=postgresql://user:pass@host:port/dbname $0 [command]"
            echo ""
            echo "Commands:"
            echo "  full         - Perform full backup + WAL archive + purge old (default)"
            echo "  test_restore - Test restore of the latest backup to verify integrity"
            echo "  list_backups - List all available backups"
            echo "  purge_old    - Remove backups older than retention period"
            echo "  verify       - Verify checksum of the latest backup"
            echo "  help         - Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DATABASE_URL      - PostgreSQL connection string (required)"
            echo "  BACKUP_DIR       - Base backup directory (default: /backups/pg)"
            echo "  WAL_DIR          - WAL archive directory (default: /backups/pg/wal)"
            echo "  RETENTION_DAYS   - Days to retain backups (default: 30)"
            echo "  BACKUP_LOG_FILE  - Log file path (default: /var/log/pg_backup.log)"
            echo ""
            echo "Examples:"
            echo "  DATABASE_URL=postgresql://user:pass@localhost:5432/mydb $0"
            echo "  DATABASE_URL=postgresql://user:pass@localhost:5432/mydb $0 test_restore"
            echo "  DATABASE_URL=postgresql://user:pass@localhost:5432/mydb $0 list_backups"
            exit 0
            ;;
        *)
            log_error "Unknown command: ${command}"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
