-- ESG+SCRM Platform — PostgreSQL Schema
-- Production schema for multi-tenant deployment

CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    factory_id TEXT NOT NULL DEFAULT 'factory_bd_001',
    cluster TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'MEDIUM',
    source TEXT NOT NULL,
    period TEXT,
    production_volume DOUBLE PRECISION,
    renewable_kwh DOUBLE PRECISION,
    wastewater_discharge DOUBLE PRECISION,
    water_stress_level TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE TABLE IF NOT EXISTS rec_certificates (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    source TEXT NOT NULL,
    kwh_certified DOUBLE PRECISION NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    certificate_url TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE TABLE IF NOT EXISTS evidence_chain (
    id SERIAL PRIMARY KEY,
    metric_id INTEGER NOT NULL,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    cluster TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    prev_hash TEXT,
    value DOUBLE PRECISION NOT NULL,
    raw_value DOUBLE PRECISION,
    calculated_value DOUBLE PRECISION,
    emission_factor_id INTEGER,
    methodology TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT '',
    computed_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    recorded_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    recorded_by TEXT NOT NULL DEFAULT '',
    source_system TEXT NOT NULL DEFAULT 'manual',
    parent_id INTEGER,
    archived_at TEXT,
    FOREIGN KEY (metric_id) REFERENCES metrics(id),
    FOREIGN KEY (emission_factor_id) REFERENCES emission_factors(id)
);

-- C3.9: Archive table for evidence_chain (soft-delete, retention policy)
CREATE TABLE IF NOT EXISTS evidence_chain_archive (
    id INTEGER PRIMARY KEY,
    metric_id INTEGER NOT NULL,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    cluster TEXT NOT NULL,
    hash TEXT NOT NULL,
    prev_hash TEXT,
    value DOUBLE PRECISION NOT NULL,
    raw_value DOUBLE PRECISION,
    calculated_value DOUBLE PRECISION,
    emission_factor_id INTEGER,
    methodology TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT '',
    computed_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    recorded_by TEXT NOT NULL DEFAULT '',
    source_system TEXT NOT NULL DEFAULT 'manual',
    parent_id INTEGER,
    archived_at TEXT NOT NULL,
    archive_reason TEXT NOT NULL DEFAULT 'retention'
);

CREATE TABLE IF NOT EXISTS risk_flags (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    factory_id TEXT NOT NULL DEFAULT 'factory_bd_001',
    flag_text TEXT NOT NULL,
    cluster TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('CRITICAL', 'WARNING', 'INFO')),
    days_overdue INTEGER NOT NULL DEFAULT 0,
    priority_score DOUBLE PRECISION NOT NULL,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    acknowledged INTEGER NOT NULL DEFAULT 0,
    acknowledged_at TEXT,
    acknowledged_by TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    industry TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('tier1', 'tier2', 'tier3')),
    annual_spend_usd DOUBLE PRECISION NOT NULL,
    phone TEXT,
    email TEXT NOT NULL DEFAULT '',
    preferred_channel TEXT NOT NULL DEFAULT 'whatsapp',
    relationship_status TEXT NOT NULL DEFAULT 'active',
    questionnaire_status TEXT NOT NULL DEFAULT 'not_sent',
    questionnaire_sent_at TEXT,
    email_reminder_sent INTEGER NOT NULL DEFAULT 0,
    risk_tier TEXT CHECK (risk_tier IN ('A', 'B', 'C', 'D')),
    risk_score DOUBLE PRECISION,
    esg_score DOUBLE PRECISION,
    active_flags INTEGER NOT NULL DEFAULT 0,
    certifications TEXT,
    portal_token TEXT,
    portal_token_expires TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    updated_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE TABLE IF NOT EXISTS outbound_emails (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    supplier_id TEXT,
    direction TEXT NOT NULL DEFAULT 'outbound',
    to_address TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    smtp_message_id TEXT,
    channel TEXT NOT NULL DEFAULT 'email',
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS supplier_scope3 (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    supplier_id TEXT NOT NULL,
    category TEXT NOT NULL,
    annual_spend_usd DOUBLE PRECISION NOT NULL,
    scope3_tco2e DOUBLE PRECISION NOT NULL,
    calculation_method TEXT NOT NULL,
    emission_factor TEXT,
    confidence TEXT NOT NULL DEFAULT 'LOW',
    data_source TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    supplier_id TEXT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3, 4)),
    question_id TEXT NOT NULL,
    response_text TEXT,
    response_value DOUBLE PRECISION,
    responded_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    validation_status TEXT NOT NULL DEFAULT 'pending' CHECK (validation_status IN ('verified', 'pending', 'flagged', 'rejected')),
    validation_notes TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    employee_count INTEGER NOT NULL DEFAULT 0,
    primary_buyer TEXT,
    annual_revenue_usd DOUBLE PRECISION,
    connected_since TEXT,
    retention_period_months INTEGER NOT NULL DEFAULT 84,
    plan TEXT NOT NULL DEFAULT 'starter',
    trial_end TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
    is_active INTEGER NOT NULL DEFAULT 1,
    token_version INTEGER NOT NULL DEFAULT 1,
    reset_token TEXT,
    reset_token_expires TEXT,
    email_verified INTEGER NOT NULL DEFAULT 0,
    email_verify_token TEXT,
    invited_by TEXT,
    invite_token TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    last_login TEXT,
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    last_used TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS emission_factors (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    factor_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    factor_value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    source TEXT NOT NULL,
    country_code TEXT,
    year INTEGER,
    table_or_equation TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE TABLE IF NOT EXISTS framework_mappings (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    cluster TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    framework TEXT NOT NULL,
    disclosure_code TEXT NOT NULL,
    disclosure_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    field_name TEXT,
    unit TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    UNIQUE(cluster, framework, disclosure_code)
);

CREATE TABLE IF NOT EXISTS alert_thresholds (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    cluster TEXT NOT NULL,
    metric_cluster TEXT,
    operator TEXT NOT NULL DEFAULT '>' CHECK (operator IN ('>', '<', '>=', '<=', '==', '!=')),
    threshold_value DOUBLE PRECISION NOT NULL,
    severity TEXT NOT NULL DEFAULT 'WARNING' CHECK (severity IN ('CRITICAL', 'WARNING', 'INFO')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    updated_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    archived_at TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

-- C3.9: Archive table for audit_log (soft-delete, retention policy)
CREATE TABLE IF NOT EXISTS audit_log_archive (
    id INTEGER PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    archived_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archive_reason TEXT NOT NULL DEFAULT 'retention'
);

CREATE TABLE IF NOT EXISTS questionnaire_templates (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT 'org_bd_001',
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tier INTEGER NOT NULL DEFAULT 0,
    category TEXT NOT NULL,
    questions TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    updated_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_metrics_org_cluster ON metrics(org_id, cluster);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded ON metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_evidence_metric ON evidence_chain(metric_id);
CREATE INDEX IF NOT EXISTS idx_risk_acknowledged ON risk_flags(org_id, acknowledged);
CREATE INDEX IF NOT EXISTS idx_risk_priority ON risk_flags(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_suppliers_org ON suppliers(org_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_status ON suppliers(org_id, questionnaire_status);
CREATE INDEX IF NOT EXISTS idx_scope3_supplier ON supplier_scope3(org_id, supplier_id);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_apikeys_org ON api_keys(org_id);
CREATE INDEX IF NOT EXISTS idx_emission_factors_name ON emission_factors(factor_name);
CREATE INDEX IF NOT EXISTS idx_framework_cluster ON framework_mappings(cluster);
CREATE INDEX IF NOT EXISTS idx_thresholds_org ON alert_thresholds(org_id, cluster);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_log(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id);

CREATE TABLE IF NOT EXISTS factories (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    name TEXT NOT NULL,
    location TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_factories_org ON factories(org_id);

CREATE TABLE IF NOT EXISTS questionnaire_questions (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    question_text_bn TEXT,
    question_text_vi TEXT,
    question_type TEXT NOT NULL CHECK (question_type IN ('number', 'choice', 'text')),
    choices TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    required INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (template_id) REFERENCES questionnaire_templates(id)
);

CREATE INDEX IF NOT EXISTS idx_questions_template ON questionnaire_questions(template_id);

CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT '',
    supplier_id TEXT NOT NULL DEFAULT '',
    template_id INTEGER NOT NULL DEFAULT 0,
    direction TEXT NOT NULL DEFAULT 'outbound',
    phone TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    twilio_message_sid TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_supplier ON whatsapp_messages(supplier_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_direction ON whatsapp_messages(direction);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_created ON whatsapp_messages(created_at);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type TEXT,
    uploaded_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE TABLE IF NOT EXISTS buyer_portal_access (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    buyer_org_id TEXT NOT NULL DEFAULT '',
    buyer_org_name TEXT NOT NULL DEFAULT '',
    scope_filter TEXT NOT NULL DEFAULT '{}',
    token TEXT NOT NULL UNIQUE,
    token_expires TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE INDEX IF NOT EXISTS idx_buyer_portal_token ON buyer_portal_access(token);
CREATE INDEX IF NOT EXISTS idx_buyer_portal_org ON buyer_portal_access(org_id);

CREATE TABLE IF NOT EXISTS metric_metadata (
    cluster TEXT PRIMARY KEY,
    trend TEXT NOT NULL DEFAULT '',
    calculation_method TEXT NOT NULL DEFAULT '',
    emission_factor TEXT NOT NULL DEFAULT '',
    emission_factor_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    coverage_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
    responding_suppliers INTEGER NOT NULL DEFAULT 0,
    total_suppliers INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    stripe_customer_id TEXT NOT NULL DEFAULT '',
    stripe_subscription_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'inactive',
    plan_id TEXT NOT NULL DEFAULT 'starter',
    current_period_start TEXT,
    current_period_end TEXT,
    trial_end TEXT,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_org ON subscriptions(org_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);

CREATE TABLE IF NOT EXISTS weight_changes (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    old_weights_json TEXT NOT NULL,
    new_weights_json TEXT NOT NULL,
    feedback_count INTEGER NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE INDEX IF NOT EXISTS idx_weight_changes_org ON weight_changes(org_id);
CREATE INDEX IF NOT EXISTS idx_weight_changes_user ON weight_changes(user_id);

CREATE TABLE IF NOT EXISTS gdpr_export_jobs (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    file_path TEXT,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_gdpr_jobs_org ON gdpr_export_jobs(org_id);
CREATE INDEX IF NOT EXISTS idx_gdpr_jobs_user ON gdpr_export_jobs(user_id);

CREATE TABLE IF NOT EXISTS notification_log (
    id SERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'email',
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    status TEXT NOT NULL DEFAULT 'sent'
);

CREATE INDEX IF NOT EXISTS idx_notification_org ON notification_log(org_id);
CREATE INDEX IF NOT EXISTS idx_notification_user ON notification_log(user_id);

CREATE TABLE IF NOT EXISTS compliance_deadlines (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    framework TEXT NOT NULL,
    requirement TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    deadline TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'upcoming',
    submission_date TEXT,
    evidence_required INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    updated_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_org ON compliance_deadlines(org_id);
CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_deadline ON compliance_deadlines(deadline);
CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_framework ON compliance_deadlines(framework);

CREATE TABLE IF NOT EXISTS country_risk_scores (
    country_code TEXT PRIMARY KEY,
    country_name TEXT NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL DEFAULT 'Kailash Internal'
);

CREATE TABLE IF NOT EXISTS user_orgs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer',
    is_primary INTEGER NOT NULL DEFAULT 0,
    joined_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_user_orgs_user ON user_orgs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_orgs_org ON user_orgs(org_id);

CREATE TABLE IF NOT EXISTS scheduled_reports (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    report_type TEXT NOT NULL,
    schedule TEXT NOT NULL,
    next_run TEXT,
    last_run TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    recipients TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    created_by TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scheduled_reports_org ON scheduled_reports(org_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_next_run ON scheduled_reports(next_run);

CREATE TABLE IF NOT EXISTS webhooks (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    events TEXT NOT NULL DEFAULT '[]',
    secret TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_triggered TEXT,
    last_status INTEGER,
    last_response TEXT,
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')),
    created_by TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_webhooks_org ON webhooks(org_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_events ON webhooks(events);

-- Auditor token store for time-limited auditor access links
CREATE TABLE IF NOT EXISTS auditor_tokens (
    token TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'read_only',
    expires_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
);

CREATE INDEX IF NOT EXISTS idx_auditor_tokens_org ON auditor_tokens(org_id);
CREATE INDEX IF NOT EXISTS idx_auditor_tokens_expires ON auditor_tokens(expires_at);

-- ============================================================================
-- SPEC 05: DataPoint Missing Fields — metrics table extensions
-- These ALTER TABLE statements add fields required for derived calculations,
-- framework reporting, audit trail, and version control.
-- ============================================================================

-- Add upstream_data_points for derived metric calculations (FK[] to DataPoint)
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS upstream_data_points INTEGER[];

-- Add reported_in_frameworks for CSRD/ISSB/GRI/TCFD disclosure tracking
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS reported_in_frameworks TEXT[];

-- Add reported_at timestamp for when data was reported
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS reported_at TIMESTAMP;

-- Add reported_by FK reference to users table
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS reported_by INTEGER REFERENCES users(id);

-- Add version for optimistic locking / audit trail
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

-- Add calculation_method for transparency on how metric was derived
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS calculation_method TEXT;

-- ============================================================================
-- SPEC 03: Evidence Vault — evidence_chain table extensions
-- These ALTER TABLE statements add fields required for chain-of-custody,
-- cryptographic verification, and CSRD compliance.
-- ============================================================================

-- Add evidence_type for chain of custody tracking
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS evidence_type TEXT;

-- Add raw_source_reference for API response ID, file path, message ID
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS raw_source_reference TEXT;

-- Add raw_source_hash for SHA-256 of raw source at extraction time
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS raw_source_hash TEXT;

-- Add calculation_formula for human-readable audit trail
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS calculation_formula TEXT;

-- Add confidence_rationale for why confidence level was assigned
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS confidence_rationale TEXT;

-- Add chain_valid flag for cryptographic chain verification
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS chain_valid BOOLEAN DEFAULT TRUE;

-- Add retention_policy for CSRD 7-year compliance
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS retention_policy TEXT DEFAULT 'csrd_7yr';

-- Add retained_until for CSRD retention deadline (created_at + 7 years)
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS retained_until TIMESTAMP;

-- Add unit for metric type context
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS unit TEXT;

-- Add metric_type for evidence classification
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS metric_type TEXT;

-- Add cryptographic_hash for SHA-256(data_point_id + value + methodology + timestamp)
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS cryptographic_hash TEXT;

-- Add included_in_report for DisclosureReport linkage
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS included_in_report UUID;

-- Add reported_at for when evidence was reported in a disclosure
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS reported_at TIMESTAMP;

-- Add reported_by for user who included in report
ALTER TABLE evidence_chain ADD COLUMN IF NOT EXISTS reported_by UUID;
