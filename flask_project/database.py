"""
AgriNiramaya - Database Module
SQLite Database connection, schema initialization, and migration management.
Project: First-Year Engineering EDI Project
"""

import sqlite3
import os
from contextlib import contextmanager

# Base directory for database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "plant_doctor.db")


def get_db_path():
    """Return absolute path to plant_doctor.db."""
    return DB_PATH


@contextmanager
def get_db_connection():
    """Context manager providing a database connection with dict-like row access."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all required tables with proper constraints and relationships."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                security_question TEXT DEFAULT 'What is your favorite crop or plant?',
                security_answer_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Farms Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                size REAL NOT NULL DEFAULT 1.0,
                crop_name TEXT NOT NULL,
                crop_variety TEXT DEFAULT '',
                soil_type TEXT DEFAULT 'Alluvial',
                irrigation_method TEXT DEFAULT 'Drip Irrigation',
                field_info TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 3. Plant Image Uploads Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plant_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER,
                crop_name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                mime_type TEXT DEFAULT 'image/jpeg',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE SET NULL
            );
        """)

        # 4. Disease Analysis Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disease_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                disease_name TEXT DEFAULT 'Model Pending',
                confidence REAL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'model_integration_pending',
                symptoms TEXT DEFAULT '',
                disease_info TEXT DEFAULT '',
                care_suggestions TEXT DEFAULT '',
                preventive_measures TEXT DEFAULT '',
                model_version TEXT DEFAULT 'AgriNiramaya-CNN-Ready-v1.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (upload_id) REFERENCES plant_uploads(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 5. Soil Readings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS soil_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                farm_id INTEGER,
                device_id TEXT DEFAULT 'ESP32_AGRI_NODE_01',
                moisture REAL NOT NULL,
                temperature REAL NOT NULL,
                ph REAL NOT NULL,
                humidity REAL DEFAULT NULL,
                nitrogen REAL DEFAULT NULL,
                phosphorus REAL DEFAULT NULL,
                potassium REAL DEFAULT NULL,
                soil_classification TEXT DEFAULT 'Balanced Loam',
                is_test_data INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE SET NULL
            );
        """)

        # 6. Assistant Messages Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assistant_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sender TEXT NOT NULL CHECK(sender IN ('user', 'assistant')),
                message TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 7. Contact Inquiries Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create indexes for fast filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_farms_user ON farms(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_user ON plant_uploads(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_soil_user ON soil_readings(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_soil_time ON soil_readings(created_at);")

        conn.commit()
        print(f"[AgriNiramaya] Database initialized successfully at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
