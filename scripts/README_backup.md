# PostgreSQL Backup Documentation

This directory contains the PostgreSQL backup script for the ESG SCRM project, providing automated backups with WAL archiving for point-in-time recovery capability.

## Quick Start

```bash
# Set required environment variable
export DATABASE_URL="postgresql://user:password@host:5432/database"

# Run a full backup
./backup_pg.sh full

# Test restore integrity
./backup_pg.sh test_restore

# List available backups
./backup_pg.sh list_backups
```

## Environment Variables

| Variable          | Required | Default                  | Description                                                                      |
| ----------------- | -------- | ------------------------ | -------------------------------------------------------------------------------- |
| `DATABASE_URL`    | Yes      | -                        | PostgreSQL connection string (format: `postgresql://user:pass@host:port/dbname`) |
| `BACKUP_DIR`      | No       | `/backups/pg`            | Base directory for storing backups                                               |
| `WAL_DIR`         | No       | `/backups/pg/wal`        | Directory for WAL archives                                                       |
| `RETENTION_DAYS`  | No       | `30`                     | Number of days to retain backups                                                 |
| `BACKUP_LOG_FILE` | No       | `/var/log/pg_backup.log` | Path to log file                                                                 |

### Individual Connection Override Variables

You can override individual components of `DATABASE_URL` using these variables:

- `PGHOST` - Database host
- `PGPORT` - Database port
- `PGUSER` - Database user
- `PGPASSWORD` - Database password
- `PGDATABASE` - Database name

## Backup Script Commands

### `full` (Default)

Performs a full database backup using `pg_dump`, archives WAL files, and purges old backups based on retention policy.

```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/esg_scrm" ./backup_pg.sh full
```

### `test_restore`

Verifies backup integrity by restoring to a temporary test database. This does NOT modify the live database.

```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/esg_scrm" ./backup_pg.sh test_restore
```

The test:

1. Creates a temporary test database (`{database}_test_restore_{timestamp}`)
2. Restores the latest backup to it
3. Verifies table count
4. Cleans up the test database

### `list_backups`

Lists all available backups with metadata including size, date, and checksum.

```bash
./backup_pg.sh list_backups
```

### `purge_old`

Manually triggers purge of backups older than `RETENTION_DAYS`.

```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/esg_scrm" ./backup_pg.sh purge_old
```

### `verify`

Verifies the checksum of the latest backup without restoring.

```bash
./backup_pg.sh verify
```

## Backup Storage Structure

```
/backups/pg/
├── 20240115/
│   ├── full_backup_20240115_143022.dump
│   ├── full_backup_20240115_143022.checksum
│   └── full_backup_20240115_143022.meta
├── 20240116/
│   ├── full_backup_20240116_023010.dump
│   └── ...
├── 20240117/
│   └── ...
└── wal/
    ├── wal_20240115_143022.tar.gz
    ├── wal_20240116_023010.tar.gz
    └── ...
```

Each backup includes:

- `.dump` - PostgreSQL custom format backup file
- `.checksum` - SHA256 checksum for integrity verification
- `.meta` - Backup metadata (timestamp, database, host info)

## Automated Backup Setup (Cron)

### Setting Up Daily Backups

1. **Edit crontab:**

```bash
crontab -e
```

2. **Add entry for daily backup at 2 AM:**

```cron
# PostgreSQL Backup - Daily at 2:00 AM
0 2 * * * DATABASE_URL="postgresql://user:pass@host:5432/dbname" /path/to/backup_pg.sh full >> /var/log/pg_backup_cron.log 2>&1
```

3. **For more frequent WAL archiving (every 15 minutes):**

```cron
# WAL Archive - Every 15 minutes
*/15 * * * * DATABASE_URL="postgresql://user:pass@host:5432/dbname" /path/to/backup_pg.sh wal_archive >> /var/log/pg_backup_cron.log 2>&1
```

### Cron Schedule Examples

| Schedule      | Cron Expression | Description        |
| ------------- | --------------- | ------------------ |
| Daily at 2 AM | `0 2 * * *`     | Once per day       |
| Twice daily   | `0 2,14 * * *`  | Every 12 hours     |
| Every 6 hours | `0 */6 * * *`   | Four times per day |
| Every hour    | `0 * * * *`     | Every hour         |

### Systemd Timer (Alternative)

Create `/etc/systemd/system/pg-backup.service`:

```ini
[Unit]
Description=PostgreSQL Backup Service

[Service]
Type=oneshot
Environment=DATABASE_URL=postgresql://user:pass@host:5432/dbname
ExecStart=/path/to/backup_pg.sh full
User=postgres
```

Create `/etc/systemd/system/pg-backup.timer`:

```ini
[Unit]
Description=PostgreSQL Backup Timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pg-backup.timer
```

## Restore from Backup

### Full Restore (Overwrites Live Database)

**WARNING: This will overwrite your current database. Use `test_restore` first to verify backup integrity.**

```bash
# Stop application to prevent writes
sudo systemctl stop your-app

# Drop existing database
psql -h localhost -U postgres -c "DROP DATABASE esg_scrm;"

# Create empty database
psql -h localhost -U postgres -c "CREATE DATABASE esg_scrm;"

# Restore from backup
pg_restore -h localhost -U postgres -d esg_scrm /backups/pg/20240115/full_backup_20240115_143022.dump

# Restart application
sudo systemctl start your-app
```

### Point-in-Time Recovery (PITR)

Point-in-time recovery allows you to restore to any moment between the oldest backup and the latest WAL archive.

#### Prerequisites for PITR

1. PostgreSQL must have WAL archiving enabled
2. You have both base backups and WAL archives
3. PostgreSQL's `wal_level` is set to `replica` or higher

#### Steps for PITR

1. **Identify your recovery target time:**

```bash
# Example: Restore to 2024-01-15 at 3:30 PM
RECOVERY_TARGET_TIME="2024-01-15 15:30:00"
```

2. **Prepare recovery.conf on the PostgreSQL server:**

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Create recovery.conf (PostgreSQL 12 and earlier)
cat > /var/lib/postgresql/data/recovery.conf << EOF
restore_command = 'gunzip -c /backups/pg/wal/wal_%f.tar.gz > %p'
recovery_target_time = '$RECOVERY_TARGET_TIME'
recovery_target_action = 'promote'
EOF

# For PostgreSQL 13+, use standby.signal
touch /var/lib/postgresql/data/standby.signal
```

3. **Update postgresql.conf:**

```ini
# Add to postgresql.conf
restore_command = 'gunzip -c /backups/pg/wal/wal_%f.tar.gz > %p'
recovery_target_time = '2024-01-15 15:30:00'
recovery_target_action = 'promote'
```

4. **Start PostgreSQL:**

```bash
sudo systemctl start postgresql
```

5. **Verify recovery:**

```bash
# Check PostgreSQL logs for recovery status
sudo journalctl -u postgresql -n 50

# Connect and verify data
psql -h localhost -U postgres -d esg_scrm -c "SELECT COUNT(*) FROM your_table;"
```

### Restoring to a Different Server

1. Copy backup files to the new server:

```bash
scp -r /backups/pg/* newserver:/backups/pg/
```

2. Install PostgreSQL on the new server:

```bash
sudo apt install postgresql
```

3. Initialize and configure PostgreSQL data directory:

```bash
sudo systemctl stop postgresql
sudo rm -rf /var/lib/postgresql/data
sudo -u postgres /usr/lib/postgresql/*/bin/initdb -D /var/lib/postgresql/data
```

4. Restore the backup:

```bash
sudo -u postgres pg_restore -C -d postgres /backups/pg/20240115/full_backup_20240115_143022.dump
```

## Backup Verification

### Automated Verification

Add to crontab to verify backups daily:

```cron
# Verify backup integrity - Daily at 3 AM
0 3 * * * DATABASE_URL="postgresql://user:pass@host:5432/dbname" /path/to/backup_pg.sh verify >> /var/log/pg_backup_verify.log 2>&1
```

### Manual Verification

```bash
# List backups
./backup_pg.sh list_backups

# Test restore (non-destructive)
./backup_pg.sh test_restore

# Verify checksum
./backup_pg.sh verify
```

## Monitoring

### Check Last Backup Status

```bash
# View recent log entries
tail -20 /var/log/pg_backup.log

# Check backup file exists and is recent
ls -la /backups/pg/*/full_backup_*.dump | tail -5
```

### Alert on Failed Backups

Add monitoring to your cron job output:

```bash
# In cron - sends email on failure
0 2 * * * DATABASE_URL="..." /path/to/backup_pg.sh full 2>&1 | tee /tmp/backup.log
if grep -q ERROR /tmp/backup.log; then
    mail -s "PG Backup Failed" admin@example.com < /tmp/backup.log
fi
```

## Security Considerations

1. **Protect backup files:** Backups contain all database data, including sensitive information
   - Store backups on encrypted filesystems
   - Limit access to backup directory: `chmod 700 /backups/pg`
   - Consider encrypting backups: `./backup_pg.sh full | gpg -c > backup.gpg`

2. **Secure DATABASE_URL:**
   - Never commit DATABASE_URL to version control
   - Use a secrets manager for automation
   - Consider using PostgreSQL's `.pgpass` file for authentication

3. **Network security:**
   - Use SSL connections for remote databases
   - Add `sslmode=require` to DATABASE_URL for remote connections

## Troubleshooting

### "psql: command not found"

Install PostgreSQL client:

```bash
# Ubuntu/Debian
sudo apt install postgresql-client

# macOS
brew install postgresql
```

### "Cannot connect to database"

1. Verify DATABASE_URL format is correct
2. Check PostgreSQL is running: `sudo systemctl status postgresql`
3. Verify credentials: `PGPASSWORD=pass psql -h host -U user -d dbname -c "SELECT 1"`
4. Check firewall rules allow connection

### "Permission denied" on backup directory

Fix directory permissions:

```bash
sudo chown -R $(whoami) /backups/pg
chmod 700 /backups/pg
```

### Backup size unexpectedly large

- Ensure WAL archiving is working (WAL files should be ~16MB each)
- Check for bloat: `VACUUM FULL` before backup
- Consider incremental backups between full backups

## Support

For issues or questions about the backup system, check:

1. Log file: `/var/log/pg_backup.log`
2. Backup metadata: `/backups/pg/{date}/full_backup_{timestamp}.meta`
3. PostgreSQL logs: `sudo journalctl -u postgresql`
