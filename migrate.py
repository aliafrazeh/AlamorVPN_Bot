# migrate.py

import logging
from database.db_manager import DatabaseManager

# تنظیمات اولیه برای نمایش لاگ‌ها در ترمینال
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migrations():
    """
    اسکریپت را برای اعمال تغییرات اسکیمای دیتابیس اجرا می‌کند.
    این اسکریپت به گونه‌ای طراحی شده که اجرای چندباره آن مشکلی ایجاد نکند.
    """
    logging.info("Starting database migration script...")
    
    db_manager = DatabaseManager()
    conn = None
    
    # لیست تمام دستورات SQL برای مهاجرت
    # از عبارت IF NOT EXISTS استفاده می‌کنیم تا اسکریپت ایمن باشد
    migrations = [
        """
        ALTER TABLE server_inbounds 
        ADD COLUMN IF NOT EXISTS config_params JSONB;
        """,
        """
        ALTER TABLE profile_inbounds 
        ADD COLUMN IF NOT EXISTS config_params JSONB;
        """
        # ... در آینده می‌توان دستورات دیگری را به این لیست اضافه کرد ...
    ]
    
    try:
        conn = db_manager._get_connection()
        logging.info("Successfully connected to the PostgreSQL database.")
        
        with conn.cursor() as cur:
            for i, migration_sql in enumerate(migrations, 1):
                try:
                    logging.info(f"Applying migration #{i}...")
                    cur.execute(migration_sql)
                    logging.info(f"Migration #{i} applied successfully.")
                except Exception as e:
                    logging.error(f"Error applying migration #{i}: {e}")
                    # در صورت بروز خطا، تغییرات را به حالت قبل برمی‌گردانیم
                    conn.rollback()
                    return

        # اگر تمام دستورات موفقیت‌آمیز بودند، تغییرات را نهایی می‌کنیم
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