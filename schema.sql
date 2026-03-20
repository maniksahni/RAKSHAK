-- RAKSHAK Database Schema
-- Run: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS rakshak CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rakshak;

-- 1. Users Table
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
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_risk_level (risk_level)
);

-- 2. Trusted Contacts Table
CREATE TABLE IF NOT EXISTS trusted_contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(150) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    relationship VARCHAR(50) DEFAULT 'Friend',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    UNIQUE KEY unique_user_contact (user_id, contact_email)
);

-- 3. SOS Alerts Table
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_location (latitude, longitude)
);

-- 4. Danger Zones Table
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
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_status (status),
    INDEX idx_location (latitude, longitude)
);

-- 5. Ping Logs Table
CREATE TABLE IF NOT EXISTS ping_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ping_type ENUM('heartbeat','missed','auto_sos') DEFAULT 'heartbeat',
    latitude DECIMAL(10, 8) DEFAULT NULL,
    longitude DECIMAL(11, 8) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

-- 6. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type ENUM('sos','danger_zone','system','ping_warning') DEFAULT 'system',
    is_read BOOLEAN DEFAULT FALSE,
    related_alert_id INT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_read (is_read)
);

-- 7. Audit Logs Table
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
);

-- Default Admin User (password: Admin@123)
INSERT INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
VALUES (
    'System Admin',
    'admin@rakshak.com',
    '9999999999',
    '$2b$12$rgywUnAd5WUKqFjZRKSaw.ynmlcHJTlnKuv7AOozwzPlOKVp0s436',
    'admin',
    'What is the system name?',
    '$2b$12$rgywUnAd5WUKqFjZRKSaw.ynmlcHJTlnKuv7AOozwzPlOKVp0s436'
) ON DUPLICATE KEY UPDATE id=id;

-- Demo Regular User (password: User@123)
INSERT INTO users (full_name, email, phone, password_hash, role, security_question, security_answer_hash)
VALUES (
    'Priya Sharma',
    'priya@example.com',
    '9876543210',
    '$2b$12$pENR5GsVTvye66GYZ5YQlO8nPuVeajZxHdvDux/oWWUoTeellPLrq',
    'user',
    'What is your mother name?',
    '$2b$12$pENR5GsVTvye66GYZ5YQlO8nPuVeajZxHdvDux/oWWUoTeellPLrq'
) ON DUPLICATE KEY UPDATE id=id;
