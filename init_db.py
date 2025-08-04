import logging
from database.db_manager import DatabaseManager

# تنظیمات لاگ برای دیدن خروجی
logging.basicConfig(level=logging.INFO)

print("Attempting to connect to PostgreSQL and create tables...")

try:
    db = DatabaseManager()
    db.create_tables()
    print("\n✅ Success! Tables were created or already exist in your PostgreSQL database.")
except Exception as e:
    print(f"\n❌ An error occurred: {e}")