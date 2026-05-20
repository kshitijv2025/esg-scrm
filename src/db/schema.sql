-- ESG+SCRM Platform — SQLite Schema
-- Supports both single-tenant (dev) and multi-tenant (production) usage.
-- org_id columns are nullable for backward compatibility with existing seeds.

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    employee_count INTEGER NOT NULL DEFAULT 0,
    primary_buyer TEXT,
    annual_revenue_usd REAL,
    connected_since TEXT,
    retention_period_months INTEGER NOT NULL DEFAULT 84,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
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
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
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
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT,
    factory_id TEXT NOT NULL DEFAULT 'factory_bd_001',
    cluster TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'MEDIUM',
    source TEXT NOT NULL,
    period TEXT,
    production_volume REAL,
    renewable_kwh REAL,
    wastewater_discharge REAL,
    water_stress_level TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rec_certificates (
    id TEXT PRIMARY KEY,
    org_id TEXT,
    source TEXT NOT NULL,
    kwh_certified REAL NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    certificate_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evidence_chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER NOT NULL,
    org_id TEXT NOT NULL DEFAULT '',
    cluster TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    prev_hash TEXT,
    value REAL NOT NULL,
    raw_value REAL,
    calculated_value REAL,
    emission_factor_id INTEGER,
    methodology TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT '',
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
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
    org_id TEXT NOT NULL DEFAULT '',
    cluster TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    prev_hash TEXT,
    value REAL NOT NULL,
    raw_value REAL,
    calculated_value REAL,
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
    org_id TEXT,
    factory_id TEXT NOT NULL DEFAULT 'factory_bd_001',
    flag_text TEXT NOT NULL,
    cluster TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('CRITICAL', 'WARNING', 'INFO')),
    days_overdue INTEGER NOT NULL DEFAULT 0,
    priority_score REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    acknowledged INTEGER NOT NULL DEFAULT 0,
    acknowledged_at TEXT,
    acknowledged_by TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    org_id TEXT,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    industry TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('tier1', 'tier2', 'tier3')),
    annual_spend_usd REAL NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    preferred_channel TEXT NOT NULL DEFAULT 'whatsapp',
    relationship_status TEXT NOT NULL DEFAULT 'active',
    questionnaire_status TEXT NOT NULL DEFAULT 'not_sent',
    questionnaire_sent_at TEXT,
    email_reminder_sent INTEGER NOT NULL DEFAULT 0,
    risk_tier TEXT CHECK (risk_tier IN ('A', 'B', 'C', 'D')),
    risk_score REAL,
    esg_score REAL,
    active_flags INTEGER NOT NULL DEFAULT 0,
    certifications TEXT,
    portal_token TEXT,
    portal_token_expires TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outbound_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    supplier_id TEXT,
    direction TEXT NOT NULL DEFAULT 'outbound',
    to_address TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    smtp_message_id TEXT,
    channel TEXT NOT NULL DEFAULT 'email',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS supplier_scope3 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT,
    supplier_id TEXT NOT NULL,
    category TEXT NOT NULL,
    annual_spend_usd REAL NOT NULL,
    scope3_tco2e REAL NOT NULL,
    calculation_method TEXT NOT NULL,
    emission_factor TEXT,
    confidence TEXT NOT NULL DEFAULT 'LOW',
    data_source TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT,
    supplier_id TEXT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3, 4)),
    question_id TEXT NOT NULL,
    response_text TEXT,
    response_value REAL,
    responded_at TEXT NOT NULL DEFAULT (datetime('now')),
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    validation_status TEXT NOT NULL DEFAULT 'pending' CHECK (validation_status IN ('verified', 'pending', 'flagged', 'rejected')),
    validation_notes TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS emission_factors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT,
    factor_name TEXT NOT NULL,
    category TEXT NOT NULL,
    factor_value REAL NOT NULL,
    unit TEXT NOT NULL,
    country_code TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'GHG Protocol',
    year INTEGER NOT NULL DEFAULT 2024,
    table_or_equation TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS framework_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    cluster TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    framework TEXT NOT NULL,
    disclosure_code TEXT NOT NULL,
    disclosure_name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    field_name TEXT,
    unit TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alert_thresholds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT,
    cluster TEXT NOT NULL,
    metric_cluster TEXT NOT NULL,
    operator TEXT NOT NULL DEFAULT '>',
    threshold_value REAL NOT NULL,
    severity TEXT NOT NULL DEFAULT 'WARNING',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT '',
    ip_address TEXT NOT NULL DEFAULT '',
    archived_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- C3.9: Archive table for audit_log (soft-delete, retention policy)
CREATE TABLE IF NOT EXISTS audit_log_archive (
    id INTEGER PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT '',
    ip_address TEXT NOT NULL DEFAULT '',
    archived_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archive_reason TEXT NOT NULL DEFAULT 'retention'
);

CREATE TABLE IF NOT EXISTS questionnaire_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tier INTEGER NOT NULL DEFAULT 0,
    category TEXT NOT NULL DEFAULT '',
    questions TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_metrics_cluster ON metrics(cluster);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded ON metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_org ON metrics(org_id);
CREATE INDEX IF NOT EXISTS idx_evidence_metric ON evidence_chain(metric_id);
CREATE INDEX IF NOT EXISTS idx_risk_acknowledged ON risk_flags(acknowledged);
CREATE INDEX IF NOT EXISTS idx_risk_priority ON risk_flags(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_risk_org ON risk_flags(org_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_status ON suppliers(questionnaire_status);
CREATE INDEX IF NOT EXISTS idx_suppliers_org ON suppliers(org_id);
CREATE INDEX IF NOT EXISTS idx_scope3_supplier ON supplier_scope3(supplier_id);
CREATE INDEX IF NOT EXISTS idx_scope3_org ON supplier_scope3(org_id);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_apikeys_org ON api_keys(org_id);
CREATE INDEX IF NOT EXISTS idx_emission_factors_name ON emission_factors(factor_name);
CREATE INDEX IF NOT EXISTS idx_emission_factors_country ON emission_factors(country_code);
CREATE INDEX IF NOT EXISTS idx_framework_cluster ON framework_mappings(cluster);
CREATE INDEX IF NOT EXISTS idx_framework_framework ON framework_mappings(framework);
CREATE INDEX IF NOT EXISTS idx_alert_thresholds_cluster ON alert_thresholds(cluster);
CREATE INDEX IF NOT EXISTS idx_alert_thresholds_org ON alert_thresholds(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_org ON audit_log(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_questionnaire_templates_org ON questionnaire_templates(org_id);
CREATE INDEX IF NOT EXISTS idx_questionnaire_templates_tier ON questionnaire_templates(tier);

CREATE TABLE IF NOT EXISTS factories (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    name TEXT NOT NULL,
    location TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_factories_org ON factories(org_id);

CREATE TABLE IF NOT EXISTS questionnaire_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL DEFAULT '',
    supplier_id TEXT NOT NULL DEFAULT '',
    template_id INTEGER NOT NULL DEFAULT 0,
    direction TEXT NOT NULL DEFAULT 'outbound',
    phone TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    twilio_message_sid TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_supplier ON whatsapp_messages(supplier_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_direction ON whatsapp_messages(direction);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_created ON whatsapp_messages(created_at);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
