"""One-shot DB initialiser for RAKSHAK — run once to create all tables (PostgreSQL)."""
import psycopg2
import sys
import os
from dotenv import load_dotenv
load_dotenv()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user','trusted_contact','admin')),
    security_question VARCHAR(255) NOT NULL,
    security_answer_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    risk_level VARCHAR(10) DEFAULT 'low' CHECK (risk_level IN ('low','medium','high')),
    last_ping TIMESTAMP DEFAULT NULL,
    consecutive_missed_pings INT DEFAULT 0,
    profile_image VARCHAR(255) DEFAULT NULL,
    address TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trusted_contacts (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(150) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    relationship VARCHAR(50) DEFAULT 'Friend',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sos_alerts (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address TEXT DEFAULT NULL,
    trigger_type VARCHAR(20) DEFAULT 'manual' CHECK (trigger_type IN ('manual','auto_ai','panic')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','resolved','false_alarm')),
    message TEXT DEFAULT NULL,
    battery_level INT DEFAULT NULL,
    accuracy FLOAT DEFAULT NULL,
    resolved_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS danger_zones (
    id SERIAL PRIMARY KEY,
    reported_by INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    radius_meters INT DEFAULT 200,
    zone_type VARCHAR(20) DEFAULT 'other' CHECK (zone_type IN ('harassment','theft','poorly_lit','other')),
    description TEXT NOT NULL,
    severity VARCHAR(10) DEFAULT 'medium' CHECK (severity IN ('low','medium','high')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
    approved_by INT DEFAULT NULL,
    upvotes INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ping_logs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    ping_type VARCHAR(20) DEFAULT 'heartbeat' CHECK (ping_type IN ('heartbeat','missed','auto_sos')),
    latitude DECIMAL(10, 8) DEFAULT NULL,
    longitude DECIMAL(11, 8) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(20) DEFAULT 'system' CHECK (notification_type IN ('sos','danger_zone','system','ping_warning')),
    is_read BOOLEAN DEFAULT FALSE,
    related_alert_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT NULL,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(50) DEFAULT NULL,
    record_id INT DEFAULT NULL,
    old_value JSONB DEFAULT NULL,
    new_value JSONB DEFAULT NULL,
    ip_address VARCHAR(45) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Create updated_at trigger function for PostgreSQL
TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$ BEGIN
    CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
"""

# Seed data (passwords pre-hashed with bcrypt cost 12)
SEEDS = [
    # Admin: Admin@123
    """INSERT INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
       VALUES ('System Admin','admin@rakshak.com','9999999999',
       '$2b$12$OJ/YZ5mnmP3GSdF8rou.iuq/7PmWIgUrQcB7uzE28GtIBZmh/f1pi',
       'admin','What is the system name?',
       '$2b$12$lCTx6wgXfHGyQxgDsEyBLOkAyZ/yJQJovUfYCKA.jogKyHiFozeAe')
       ON CONFLICT (email) DO NOTHING""",
    # User: User@123
    """INSERT INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
       VALUES ('Priya Sharma','priya@example.com','9876543210',
       '$2b$12$xIgo6mm/SnEmom75hQ.A3.4/FuIrGi9cdfNYemHRcFNgTTZPSeaQK',
       'user','What is your mother name?',
       '$2b$12$lCTx6wgXfHGyQxgDsEyBLOkAyZ/yJQJovUfYCKA.jogKyHiFozeAe')
       ON CONFLICT (email) DO NOTHING""",
]


def _get_dsn():
    url = os.environ.get('DATABASE_URL', '')
    if url:
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    user = os.environ.get('DB_USER', 'postgres')
    pw   = os.environ.get('DB_PASSWORD', '')
    db   = os.environ.get('DB_NAME', 'rakshak')
    return f"host={host} port={port} user={user} password={pw} dbname={db}"


try:
    conn = psycopg2.connect(_get_dsn())
    conn.autocommit = True
    cursor = conn.cursor()

    # Execute schema
    cursor.execute(SCHEMA_SQL)
    print("✅ All tables created successfully.")

    # Execute trigger for updated_at
    cursor.execute(TRIGGER_SQL)
    print("✅ Trigger for updated_at created.")

    # Seed
    for seed in SEEDS:
        try:
            cursor.execute(seed)
        except Exception as e:
            print(f"  ℹ️  Seed note: {e}")

    # Verify
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"✅ Database ready — {count} user(s) seeded.")

    cursor.close()
    conn.close()
    print("✅ Database initialisation complete!")

except Exception as e:
    print(f"❌ DB init failed: {e}")
    sys.exit(1)
