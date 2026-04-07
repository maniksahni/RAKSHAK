"""
Migration: Add Guardian Angel Network columns to users table
and create ai_chat_logs table.
Run once on Railway: python migrate_guardian.py
"""
import os
import sys
import mysql.connector
from dotenv import load_dotenv
load_dotenv()


def get_conn():
    host = os.environ.get('MYSQLHOST', os.environ.get('DB_HOST', 'localhost'))
    port = int(os.environ.get('MYSQLPORT', os.environ.get('DB_PORT', '3306')))
    user = os.environ.get('MYSQLUSER', os.environ.get('DB_USER', 'root'))
    pw   = os.environ.get('MYSQLPASSWORD', os.environ.get('DB_PASSWORD', ''))
    db   = os.environ.get('MYSQLDATABASE', os.environ.get('DB_NAME', 'rakshak'))
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
    return mysql.connector.connect(**kwargs)


MIGRATIONS = [
    # Guardian Angel columns on users table
    ("guardian_active",      "ALTER TABLE users ADD COLUMN IF NOT EXISTS guardian_active BOOLEAN DEFAULT FALSE"),
    ("guardian_lat",         "ALTER TABLE users ADD COLUMN IF NOT EXISTS guardian_lat DECIMAL(10,8) DEFAULT NULL"),
    ("guardian_lng",         "ALTER TABLE users ADD COLUMN IF NOT EXISTS guardian_lng DECIMAL(11,8) DEFAULT NULL"),
    ("guardian_radius_km",   "ALTER TABLE users ADD COLUMN IF NOT EXISTS guardian_radius_km DECIMAL(4,2) DEFAULT 1.0"),
    ("guardian_since",       "ALTER TABLE users ADD COLUMN IF NOT EXISTS guardian_since TIMESTAMP NULL DEFAULT NULL"),
    # AI Chat Logs table
    ("ai_chat_logs", """CREATE TABLE IF NOT EXISTS ai_chat_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    role VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""),
]

# MySQL < 8 does not support IF NOT EXISTS on ALTER TABLE ADD COLUMN
# Use this fallback for MySQL 5.7 / MariaDB
FALLBACK_COLUMN_CHECK = """
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users' AND COLUMN_NAME=%s
"""

if __name__ == '__main__':
    try:
        conn = get_conn()
        conn.autocommit = True
        cursor = conn.cursor()
        print("✅ Connected to database")

        for name, sql in MIGRATIONS:
            try:
                if sql.startswith('ALTER TABLE users ADD COLUMN IF NOT EXISTS'):
                    # Safe fallback: check column existence first
                    col_name = sql.split('ADD COLUMN IF NOT EXISTS ')[1].split()[0]
                    cursor.execute(FALLBACK_COLUMN_CHECK, (col_name,))
                    exists = cursor.fetchone()[0]
                    if exists:
                        print(f"  ⏭  Column '{col_name}' already exists — skipping")
                        continue
                    # Execute without IF NOT EXISTS for broader MySQL compatibility
                    sql_compat = sql.replace(' IF NOT EXISTS', '')
                    cursor.execute(sql_compat)
                else:
                    cursor.execute(sql)
                print(f"  ✅ Migration '{name}' applied")
            except mysql.connector.Error as e:
                if e.errno in (1060, 1050):  # Duplicate column / table already exists
                    print(f"  ⏭  '{name}' already exists — skipping")
                else:
                    print(f"  ❌ Migration '{name}' failed: {e}")

        cursor.close()
        conn.close()
        print("\n✅ All migrations complete!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
