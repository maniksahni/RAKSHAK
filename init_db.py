"""One-shot DB initialiser for RAKSHAK — run once to create all tables (MySQL)."""
import mysql.connector
import sys
import os
from dotenv import load_dotenv
load_dotenv()

SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    security_question VARCHAR(255) NOT NULL,
    security_answer_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    risk_level VARCHAR(10) DEFAULT 'low',
    last_ping TIMESTAMP NULL DEFAULT NULL,
    consecutive_missed_pings INT DEFAULT 0,
    profile_image VARCHAR(255) DEFAULT NULL,
    address TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS trusted_contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(150) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    relationship VARCHAR(50) DEFAULT 'Friend',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS sos_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address TEXT DEFAULT NULL,
    trigger_type VARCHAR(20) DEFAULT 'manual',
    status VARCHAR(20) DEFAULT 'active',
    message TEXT DEFAULT NULL,
    battery_level INT DEFAULT NULL,
    accuracy FLOAT DEFAULT NULL,
    resolved_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS danger_zones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reported_by INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    radius_meters INT DEFAULT 200,
    zone_type VARCHAR(20) DEFAULT 'other',
    description TEXT NOT NULL,
    severity VARCHAR(10) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'pending',
    approved_by INT DEFAULT NULL,
    upvotes INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS ping_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ping_type VARCHAR(20) DEFAULT 'heartbeat',
    latitude DECIMAL(10, 8) DEFAULT NULL,
    longitude DECIMAL(11, 8) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(20) DEFAULT 'system',
    is_read BOOLEAN DEFAULT FALSE,
    related_alert_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(50) DEFAULT NULL,
    record_id INT DEFAULT NULL,
    old_value JSON DEFAULT NULL,
    new_value JSON DEFAULT NULL,
    ip_address VARCHAR(45) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    """CREATE TABLE IF NOT EXISTS journeys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    start_lat DECIMAL(10, 8) NOT NULL,
    start_lng DECIMAL(11, 8) NOT NULL,
    dest_lat DECIMAL(10, 8) NOT NULL,
    dest_lng DECIMAL(11, 8) NOT NULL,
    current_lat DECIMAL(10, 8) DEFAULT NULL,
    current_lng DECIMAL(11, 8) DEFAULT NULL,
    eta_minutes INT NOT NULL DEFAULT 30,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expected_end TIMESTAMP NULL DEFAULT NULL,
    ended_at TIMESTAMP NULL DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'active',
    share_token VARCHAR(64) UNIQUE DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

# Seed data (passwords pre-hashed with bcrypt cost 12)
SEEDS = [
    # Admin: Manik — Password: Manik@123
    """INSERT IGNORE INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
       VALUES ('Manik Sahni','manik@rakshak.com','9999999999',
       '$2b$12$T4ttwopBuO1wR0ws/2wLge7NcQtKnu65WCL/Eb3rTqTMNGZsPUWp6',
       'admin','What is the system name?',
       '$2b$12$PB0tITPBC385UyYcri/8keGQQ4rkV5vNf9P8w/nS/NvIQcBVYDS1u')""",
    # User: Keshav — Password: Keshav@123
    """INSERT IGNORE INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
       VALUES ('Keshav','keshav@rakshak.com','9876543210',
       '$2b$12$9rWBSAdoP4./sqE3m.MCVecIg.e4nIbsjhu80yIQSdTGvJCoREqIC',
       'user','What is the system name?',
       '$2b$12$PB0tITPBC385UyYcri/8keGQQ4rkV5vNf9P8w/nS/NvIQcBVYDS1u')""",
]


def _get_conn_kwargs():
    host = os.environ.get('MYSQLHOST') or os.environ.get('DB_HOST', 'localhost')
    port = int(os.environ.get('MYSQLPORT') or os.environ.get('DB_PORT', '3306'))
    user = os.environ.get('MYSQLUSER') or os.environ.get('DB_USER', 'root')
    pw   = os.environ.get('MYSQLPASSWORD') or os.environ.get('DB_PASSWORD', '')
    db   = os.environ.get('MYSQLDATABASE') or os.environ.get('DB_NAME', 'rakshak')
    kwargs = dict(host=host, port=port, user=user, password=pw, database=db)
    if os.environ.get('DB_SSL', 'false').lower() in ('true', '1', 'yes'):
        for ca in ['/etc/ssl/certs/ca-certificates.crt', '/etc/ssl/cert.pem']:
            if os.path.exists(ca):
                kwargs['ssl_ca'] = ca
                kwargs['ssl_verify_cert'] = True
                break
        else:
            kwargs['ssl_ca'] = None
            kwargs['ssl_verify_cert'] = False
        kwargs['ssl_disabled'] = False
    return kwargs


try:
    conn = mysql.connector.connect(**_get_conn_kwargs())
    conn.autocommit = True
    cursor = conn.cursor()

    # Execute schema
    for stmt in SCHEMA_SQL:
        cursor.execute(stmt)
    print("✅ All tables created successfully.")

    # Clean old seed users (Priya, System Admin) if they exist
    try:
        cursor.execute("DELETE FROM users WHERE email IN ('priya@example.com', 'admin@rakshak.com') AND full_name IN ('Priya Sharma', 'System Admin')")
        print("  🧹 Cleaned old seed users.")
    except Exception as e:
        print(f"  ℹ️  Cleanup note: {e}")

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
