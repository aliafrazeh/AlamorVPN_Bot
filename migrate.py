# migrate.py

import logging
import os
from dotenv import load_dotenv
from database.db_manager import DatabaseManager

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات اولیه برای نمایش لاگ‌ها در ترمینال
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migrations():
    """
    اسکریپت را برای اعمال تغییرات اسکیمای دیتابیس اجرا می‌کند.
    این اسکریپت به گونه‌ای طراحی شده که اجرای چندباره آن مشکلی ایجاد نکند.
    """
    logging.info("Starting database migration script...")
    
    db_type = os.getenv("DB_TYPE", "sqlite")
    logging.info(f"Database type: {db_type}")
    
    db_manager = DatabaseManager()
    conn = None
    
    try:
        conn = db_manager._get_connection()
        
        if db_type == "postgres":
            logging.info("Successfully connected to the PostgreSQL database.")
            
            # لیست دستورات SQL برای PostgreSQL
            migrations = [
                """
                ALTER TABLE server_inbounds 
                ADD COLUMN IF NOT EXISTS config_params JSONB;
                """,
                """
                ALTER TABLE profile_inbounds 
                ADD COLUMN IF NOT EXISTS config_params JSONB;
                """
            ]
        else:
            logging.info("Successfully connected to the SQLite database.")
            
            # لیست دستورات SQL برای SQLite
            migrations = [
                """
                ALTER TABLE server_inbounds 
                ADD COLUMN config_params TEXT;
                """,
                """
                ALTER TABLE profile_inbounds 
                ADD COLUMN config_params TEXT;
                """
            ]
        
        with conn.cursor() as cur:
            for i, migration_sql in enumerate(migrations, 1):
                try:
                    logging.info(f"Applying migration #{i}...")
                    cur.execute(migration_sql)
                    logging.info(f"Migration #{i} applied successfully.")
                except Exception as e:
                    # در SQLite، اگر ستون قبلاً وجود داشته باشد، خطا می‌دهد
                    if db_type == "sqlite" and "duplicate column name" in str(e).lower():
                        logging.info(f"Column already exists in SQLite. Skipping migration #{i}.")
                    else:
                        logging.error(f"Error applying migration #{i}: {e}")
                        # در صورت بروز خطا، تغییرات را به حالت قبل برمی‌گردانیم
                        if db_type == "postgres":
                            conn.rollback()
                        return

        # اگر تمام دستورات موفقیت‌آمیز بودند، تغییرات را نهایی می‌کنیم
        if db_type == "postgres":
            conn.commit()
        else:
            conn.commit()
        logging.info("All migrations completed successfully!")
        
    except Exception as e:
        logging.error(f"A critical error occurred during the migration process: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    run_migrations()