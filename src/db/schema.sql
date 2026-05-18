-- ESG+SCRM Platform — SQLite Schema
-- Initial migration: metrics, evidence_chain, risk_flags, suppliers, questionnaire_responses

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factory_id TEXT NOT NULL DEFAULT 'factory_bd_001',
    cluster TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'MEDIUM',
    source TEXT NOT NULL,
    period TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evidence_chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER NOT NULL,
    cluster TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    prev_hash TEXT,
    value REAL NOT NULL,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    source_system TEXT NOT NULL DEFAULT 'manual',
    FOREIGN KEY (metric_id) REFERENCES metrics(id)
);

CREATE TABLE IF NOT EXISTS risk_flags (
    id TEXT PRIMARY KEY,
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
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    industry TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('tier1', 'tier2', 'tier3')),
    annual_spend_usd REAL NOT NULL,
    preferred_channel TEXT NOT NULL DEFAULT 'whatsapp',
    relationship_status TEXT NOT NULL DEFAULT 'active',
    questionnaire_status TEXT NOT NULL DEFAULT 'not_sent',
    risk_tier TEXT CHECK (risk_tier IN ('A', 'B', 'C')),
    risk_score REAL,
    active_flags INTEGER NOT NULL DEFAULT 0,
    certifications TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS supplier_scope3 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    supplier_id TEXT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3, 4)),
    question_id TEXT NOT NULL,
    response_text TEXT,
    response_value REAL,
    responded_at TEXT NOT NULL DEFAULT (datetime('now')),
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE INDEX IF NOT EXISTS idx_metrics_cluster ON metrics(cluster);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded ON metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_evidence_metric ON evidence_chain(metric_id);
CREATE INDEX IF NOT EXISTS idx_risk_acknowledged ON risk_flags(acknowledged);
CREATE INDEX IF NOT EXISTS idx_risk_priority ON risk_flags(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_suppliers_status ON suppliers(questionnaire_status);
CREATE INDEX IF NOT EXISTS idx_scope3_supplier ON supplier_scope3(supplier_id);

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT '',
    employee_count INTEGER NOT NULL DEFAULT 0,
    primary_buyer TEXT,
    annual_revenue_usd REAL,
    connected_since TEXT,
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

CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_apikeys_org ON api_keys(org_id);
