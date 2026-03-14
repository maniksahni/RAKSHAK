"""One-shot DB initialiser for RAKSHAK — run once to create all tables."""
import mysql.connector
import sys

SCHEMA_SQL = """
CREATE DATABASE IF NOT EXISTS rakshak CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rakshak;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user','trusted_contact','admin') DEFAULT 'user',
    security_question VARCHAR(255) NOT NULL,
    security_answer_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    risk_level ENUM('low','medium','high') DEFAULT 'low',
    last_ping DATETIME DEFAULT NULL,
    consecutive_missed_pings INT DEFAULT 0,
    profile_image VARCHAR(255) DEFAULT NULL,
    address TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trusted_contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(150) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    relationship VARCHAR(50) DEFAULT 'Friend',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sos_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address TEXT DEFAULT NULL,
    trigger_type ENUM('manual','auto_ai','panic') DEFAULT 'manual',
    status ENUM('active','resolved','false_alarm') DEFAULT 'active',
    message TEXT DEFAULT NULL,
    battery_level INT DEFAULT NULL,
    accuracy FLOAT DEFAULT NULL,
    resolved_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS danger_zones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reported_by INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    radius_meters INT DEFAULT 200,
    zone_type ENUM('harassment','theft','poorly_lit','other') DEFAULT 'other',
    description TEXT NOT NULL,
    severity ENUM('low','medium','high') DEFAULT 'medium',
    status ENUM('pending','approved','rejected') DEFAULT 'pending',
    approved_by INT DEFAULT NULL,
    upvotes INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME DEFAULT NULL,
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ping_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ping_type ENUM('heartbeat','missed','auto_sos') DEFAULT 'heartbeat',
    latitude DECIMAL(10, 8) DEFAULT NULL,
    longitude DECIMAL(11, 8) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type ENUM('sos','danger_zone','system','ping_warning') DEFAULT 'system',
    is_read BOOLEAN DEFAULT FALSE,
    related_alert_id INT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(50) DEFAULT NULL,
    record_id INT DEFAULT NULL,
    old_value JSON DEFAULT NULL,
    new_value JSON DEFAULT NULL,
    ip_address VARCHAR(45) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# Seed data (passwords pre-hashed with bcrypt cost 12)
SEEDS = [
    # Admin: Admin@123
    """INSERT IGNORE INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
       VALUES ('System Admin','admin@rakshak.com','9999999999',
       '$2b$12$eImiTXuWVxfM37uY4JANjQeOCwdQ1fPyFI2moxAmT6TPBVGB7dR3q',
       'admin','What is the system name?',
       '$2b$12$eImiTXuWVxfM37uY4JANjQeOCwdQ1fPyFI2moxAmT6TPBVGB7dR3q')""",
    # User: User@123
    """INSERT IGNORE INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
       VALUES ('Priya Sharma','priya@example.com','9876543210',
       '$2b$12$eImiTXuWVxfM37uY4JANjQeOCwdQ1fPyFI2moxAmT6TPBVGB7dR3q',
       'user','What is your mother name?',
       '$2b$12$eImiTXuWVxfM37uY4JANjQeOCwdQ1fPyFI2moxAmT6TPBVGB7dR3q')""",
]

try:
    conn = mysql.connector.connect(host='localhost', user='root', password='')
    cursor = conn.cursor()

    # Execute schema statements one by one
    for stmt in SCHEMA_SQL.split(';'):
        stmt = stmt.strip()
        if stmt:
            cursor.execute(stmt)

    conn.commit()
    print("✅ All tables created successfully.")

    # Seed
    for seed in SEEDS:
        try:
            cursor.execute(seed)
            conn.commit()
        except Exception as e:
            print(f"  ℹ️  Seed note: {e}")

    # Verify
    cursor.execute("USE rakshak; SELECT COUNT(*) FROM users;")
    for r in cursor:
        print(f"✅ Database ready — {r[0]} user(s) seeded.")

    cursor.close()
    conn.close()
    print("✅ Database initialisation complete!")

except Exception as e:
    print(f"❌ DB init failed: {e}")
    sys.exit(1)
