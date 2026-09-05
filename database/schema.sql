-- ============================================================================
-- PayRoute AI - SQLite Relational Schema
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. Merchants Table
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id TEXT PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    merchant_category TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Payment Gateways / Aggregators
CREATE TABLE IF NOT EXISTS gateways (
    gateway_id TEXT PRIMARY KEY,
    gateway_name TEXT NOT NULL,
    supported_methods TEXT NOT NULL, -- JSON array e.g. '["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]'
    base_fee_pct REAL DEFAULT 1.50,
    is_active INTEGER DEFAULT 1
);

-- 3. Core Transactions Log
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'INR',
    payment_method TEXT NOT NULL,
    bank TEXT NOT NULL,
    merchant_category TEXT NOT NULL,
    hour INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    device_type TEXT NOT NULL,
    network_type TEXT NOT NULL,
    customer_age_days INTEGER NOT NULL,
    previous_transactions INTEGER NOT NULL,
    previous_failed_transactions INTEGER NOT NULL,
    previous_attempts INTEGER NOT NULL,
    transaction_velocity INTEGER NOT NULL,
    is_new_device INTEGER NOT NULL,
    bank_latency_ms INTEGER NOT NULL,
    gateway_latency_ms INTEGER NOT NULL,
    bank_success_rate REAL NOT NULL,
    gateway_success_rate REAL NOT NULL,
    payment_status INTEGER NOT NULL, -- 0 = SUCCESS, 1 = FAILED
    failure_reason TEXT,             -- NULL for SUCCESS, reason string for FAILED
    lifecycle_status TEXT DEFAULT 'SUCCESS', -- SUCCESS, PENDING, FAILED, REFUND_INITIATED
    customer_debit_status TEXT DEFAULT 'CONFIRMED', -- CONFIRMED, PENDING, FAILED, REVERSED
    merchant_confirmation_status TEXT DEFAULT 'CONFIRMED', -- CONFIRMED, PENDING, FAILED
    route_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 4. Smart Routing Decision Audits (ML Decision Log)
CREATE TABLE IF NOT EXISTS routing_decisions (
    decision_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL UNIQUE,
    primary_route_id TEXT NOT NULL,
    fallback_route_id TEXT,
    primary_fail_prob REAL NOT NULL,
    predicted_failure_reason TEXT,
    shap_summary TEXT, -- JSON serialized top feature attributions
    routing_strategy TEXT NOT NULL, -- "AI_OPTIMAL", "CIRCUIT_BREAKER_OVERRIDE", "EXPLORATION"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id),
    FOREIGN KEY(primary_route_id) REFERENCES gateways(gateway_id)
);

-- 5. Gateway Health & Outage Logs
CREATE TABLE IF NOT EXISTS gateway_health_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gateway_id TEXT NOT NULL,
    bank TEXT NOT NULL,
    rolling_5m_success_rate REAL NOT NULL,
    median_latency_ms INTEGER NOT NULL,
    circuit_state TEXT NOT NULL, -- "CLOSED", "OPEN", "HALF_OPEN"
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(gateway_id) REFERENCES gateways(gateway_id)
);

-- 6. User Accounts & Authentication Table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    organization TEXT,
    role TEXT DEFAULT 'MERCHANT_ADMIN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Payment Gateway API Credentials & Settings
CREATE TABLE IF NOT EXISTS gateway_credentials (
    provider_id TEXT PRIMARY KEY, -- 'RAZORPAY', 'PHONEPE', 'GPAY'
    provider_name TEXT NOT NULL,
    environment TEXT DEFAULT 'SANDBOX', -- 'SANDBOX' or 'PRODUCTION'
    api_key_id TEXT,
    api_key_secret TEXT,
    merchant_id TEXT,
    salt_key TEXT,
    salt_index TEXT DEFAULT '1',
    webhook_secret TEXT,
    merchant_vpa TEXT,
    is_enabled INTEGER DEFAULT 1,
    last_tested_at TIMESTAMP,
    test_status TEXT DEFAULT 'UNCONFIGURED', -- 'CONNECTED', 'FAILED', 'UNCONFIGURED'
    latency_ms INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for Fast Querying & Analytics
CREATE INDEX IF NOT EXISTS idx_txn_status ON transactions(payment_status);
CREATE INDEX IF NOT EXISTS idx_txn_bank ON transactions(bank);
CREATE INDEX IF NOT EXISTS idx_txn_method ON transactions(payment_method);
CREATE INDEX IF NOT EXISTS idx_gw_health_time ON gateway_health_logs(recorded_at);
CREATE INDEX IF NOT EXISTS idx_routing_txn ON routing_decisions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_gw_creds_env ON gateway_credentials(environment);


