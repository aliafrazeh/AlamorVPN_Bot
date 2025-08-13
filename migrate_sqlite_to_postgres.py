#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت مهاجرت کامل از SQLite به PostgreSQL
این اسکریپت تمام داده‌ها را از دیتابیس SQLite به PostgreSQL منتقل می‌کند.
"""

import sqlite3
import psycopg2
import psycopg2.extras
import json
import logging
import os
import sys
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def check_environment():
    """بررسی تنظیمات محیطی"""
    logging.info("🔍 Checking environment configuration...")
    
    # بررسی نوع دیتابیس
    db_type = os.getenv("DB_TYPE", "sqlite")
    if db_type != "postgres":
        logging.error("❌ DB_TYPE must be set to 'postgres' for migration")
        return False
    
    # بررسی متغیرهای PostgreSQL
    pg_vars = {
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": os.getenv("DB_PORT", "5432")
    }
    
    missing_vars = [k for k, v in pg_vars.items() if not v]
    if missing_vars:
        logging.error(f"❌ Missing PostgreSQL environment variables: {', '.join(missing_vars)}")
        return False
    
    # بررسی وجود فایل SQLite
    sqlite_path = os.getenv("DATABASE_NAME_ALAMOR", "database/alamor_vpn.db")
    if not os.path.exists(sqlite_path):
        logging.error(f"❌ SQLite database file not found: {sqlite_path}")
        return False
    
    logging.info("✅ Environment configuration is valid")
    return True

def test_connections():
    """تست اتصال به هر دو دیتابیس"""
    logging.info("🔌 Testing database connections...")
    
    # تست اتصال SQLite
    sqlite_path = os.getenv("DATABASE_NAME_ALAMOR", "database/alamor_vpn.db")
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.close()
        logging.info("✅ SQLite connection successful")
    except Exception as e:
        logging.error(f"❌ SQLite connection failed: {e}")
        return False
    
    # تست اتصال PostgreSQL
    pg_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
    
    try:
        pg_conn = psycopg2.connect(**pg_config)
        pg_conn.close()
        logging.info("✅ PostgreSQL connection successful")
    except Exception as e:
        logging.error(f"❌ PostgreSQL connection failed: {e}")
        return False
    
    return True

def get_table_info(sqlite_conn):
    """دریافت اطلاعات جداول SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    table_info = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        table_info[table] = [col[1] for col in columns]  # نام ستون‌ها
    
    return table_info

def migrate_table(sqlite_conn, pg_conn, table_name, columns):
    """مهاجرت یک جدول"""
    logging.info(f"📦 Migrating table: {table_name}")
    
    # خواندن داده‌ها از SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        logging.info(f"   Table '{table_name}' is empty, skipping")
        return True
    
    # آماده‌سازی کوئری PostgreSQL
    placeholders = ', '.join(['%s'] * len(columns))
    pg_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    
    # تبدیل داده‌ها
    data_to_insert = []
    for row in rows:
        # تبدیل None به NULL برای PostgreSQL
        converted_row = [None if val is None else val for val in row]
        data_to_insert.append(tuple(converted_row))
    
    # درج داده‌ها در PostgreSQL
    pg_cursor = pg_conn.cursor()
    try:
        pg_cursor.executemany(pg_query, data_to_insert)
        logging.info(f"   ✅ Migrated {len(rows)} rows to '{table_name}'")
        return True
    except Exception as e:
        logging.error(f"   ❌ Failed to migrate '{table_name}': {e}")
        return False

def reset_sequences(pg_conn, tables):
    """تنظیم مجدد sequence ها"""
    logging.info("🔄 Resetting PostgreSQL sequences...")
    
    pg_cursor = pg_conn.cursor()
    for table in tables:
        try:
            # بررسی وجود ستون id
            pg_cursor.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table}' AND column_name = 'id'
            """)
            if pg_cursor.fetchone():
                pg_cursor.execute(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                    COALESCE(MAX(id), 1)) FROM {table}
                """)
                logging.info(f"   ✅ Reset sequence for '{table}'")
        except Exception as e:
            logging.warning(f"   ⚠️ Could not reset sequence for '{table}': {e}")

def main():
    """تابع اصلی مهاجرت"""
    logging.info("🚀 Starting SQLite to PostgreSQL migration...")
    
    # بررسی محیط
    if not check_environment():
        sys.exit(1)
    
    # تست اتصالات
    if not test_connections():
        sys.exit(1)
    
    # اتصال به دیتابیس‌ها
    sqlite_path = os.getenv("DATABASE_NAME_ALAMOR", "database/alamor_vpn.db")
    pg_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
    
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        pg_conn = psycopg2.connect(**pg_config)
        
        # دریافت اطلاعات جداول
        table_info = get_table_info(sqlite_conn)
        logging.info(f"📋 Found {len(table_info)} tables in SQLite")
        
        # ترتیب مهاجرت (برای رعایت foreign keys)
        migration_order = [
            'users', 'settings', 'servers', 'plans', 'server_inbounds',
            'payment_gateways', 'free_test_usage', 'payments', 'purchases', 'tutorials'
        ]
        
        # فیلتر کردن جداول موجود
        tables_to_migrate = [t for t in migration_order if t in table_info]
        
        # شروع مهاجرت
        success_count = 0
        for table in tables_to_migrate:
            if migrate_table(sqlite_conn, pg_conn, table, table_info[table]):
                success_count += 1
            else:
                logging.error(f"❌ Migration failed for table '{table}', rolling back...")
                pg_conn.rollback()
                break
        
        if success_count == len(tables_to_migrate):
            # تنظیم مجدد sequence ها
            reset_sequences(pg_conn, tables_to_migrate)
            
            # commit تغییرات
            pg_conn.commit()
            logging.info("🎉 Migration completed successfully!")
            logging.info(f"📊 Migrated {success_count}/{len(tables_to_migrate)} tables")
        else:
            logging.error("❌ Migration failed!")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"❌ Critical error during migration: {e}")
        sys.exit(1)
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_conn.close()
        logging.info("🔌 Database connections closed")

if __name__ == "__main__":
    main()
