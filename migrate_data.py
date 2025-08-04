# migrate_data.py
import sqlite3
import psycopg2
import psycopg2.extras
import json
import logging
import os
from dotenv import load_dotenv

# --- تنظیمات اولیه ---
# بارگذاری متغیرها از فایل .env
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- اطلاعات اتصال به دیتابیس‌ها ---
# SQLite (منبع)
SQLITE_DB_PATH = os.getenv("DATABASE_NAME_ALAMOR", "database/alamor_vpn.db")

# PostgreSQL (مقصد)
PG_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# ترتیب جداول برای رعایت وابستگی‌ها (Foreign Keys)
TABLES_IN_ORDER = [
    'users',
    'settings',
    'servers',
    'plans',
    'server_inbounds',
    'payment_gateways',
    'free_test_usage',
    'payments',
    'purchases',
    'tutorials'
]

def migrate_data():
    """
    داده‌ها را از دیتابیس SQLite به PostgreSQL منتقل می‌کند.
    """
    try:
        # اتصال به دیتابیس منبع (SQLite)
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cur = sqlite_conn.cursor()
        logging.info(f"✅ Connected to source SQLite database: {SQLITE_DB_PATH}")

        # اتصال به دیتابیس مقصد (PostgreSQL)
        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_cur = pg_conn.cursor()
        logging.info(f"✅ Connected to destination PostgreSQL database: {PG_CONFIG['dbname']}")

    except Exception as e:
        logging.error(f"❌ Database connection failed: {e}")
        return

    # شروع فرآیند مهاجرت جدول به جدول
    for table_name in TABLES_IN_ORDER:
        try:
            logging.info(f"--- Starting migration for table: {table_name} ---")
            
            # 1. خواندن تمام داده‌ها از جدول مبدا
            sqlite_cur.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cur.fetchall()
            
            if not rows:
                logging.info(f"Table '{table_name}' is empty. Skipping.")
                continue

            # 2. دریافت نام ستون‌ها
            columns = [description[0] for description in sqlite_cur.description]
            
            # 3. ساخت کوئری INSERT برای PostgreSQL
            placeholders = ', '.join(['%s'] * len(columns))
            pg_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # 4. تبدیل داده‌ها به لیست تاپِل برای psycopg2
            data_to_insert = [tuple(row) for row in rows]
            
            # 5. اجرای کوئری با تمام داده‌ها به صورت یکجا
            pg_cur.executemany(pg_query, data_to_insert)
            
            logging.info(f"✅ Migrated {len(rows)} rows to table '{table_name}'.")

        except Exception as e:
            logging.error(f"❌ FAILED to migrate table '{table_name}'. Error: {e}")
            logging.error("Rolling back all changes. Aborting migration.")
            pg_conn.rollback() # در صورت بروز خطا در یک جدول، تمام تغییرات لغو می‌شود
            return # خروج از فرآیند
            
    # اگر تمام جداول با موفقیت منتقل شدند، تغییرات را نهایی کن
    logging.info("\n🎉 All tables migrated successfully! Committing changes.")
    pg_conn.commit()

    # تنظیم مجدد sequence ها برای ID های auto-increment
    try:
        logging.info("--- Resetting primary key sequences in PostgreSQL ---")
        for table in TABLES_IN_ORDER:
            # این دستور فقط برای جداولی که ستون id دارند اجرا می‌شود
            pg_cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'id'")
            if pg_cur.fetchone():
                # دنباله را به آخرین مقدار id تنظیم می‌کند
                pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table};")
        pg_conn.commit()
        logging.info("✅ Sequences reset successfully.")
    except Exception as e:
        logging.warning(f"⚠️ Could not reset sequences. This is usually not critical. Error: {e}")
        pg_conn.rollback()

    # بستن تمام اتصالات
    sqlite_conn.close()
    pg_conn.close()
    logging.info("--- Migration process finished. ---")


if __name__ == "__main__":
    migrate_data()