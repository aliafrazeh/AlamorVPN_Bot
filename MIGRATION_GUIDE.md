# راهنمای مهاجرت از SQLite به PostgreSQL

## مقدمه
این راهنما به شما کمک می‌کند تا داده‌های خود را از دیتابیس SQLite به PostgreSQL منتقل کنید.

## پیش‌نیازها

### 1. نصب PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server postgresql-contrib

# Windows
# از سایت رسمی PostgreSQL دانلود و نصب کنید
```

### 2. نصب psycopg2
```bash
pip install psycopg2-binary
```

### 3. ایجاد دیتابیس PostgreSQL
```sql
-- ورود به PostgreSQL
sudo -u postgres psql

-- ایجاد کاربر
CREATE USER alamor_user WITH PASSWORD 'your_password';

-- ایجاد دیتابیس
CREATE DATABASE alamor_vpn OWNER alamor_user;

-- اعطای مجوزها
GRANT ALL PRIVILEGES ON DATABASE alamor_vpn TO alamor_user;

-- خروج
\q
```

## مراحل مهاجرت

### مرحله 1: تنظیم فایل .env
فایل `.env` خود را ویرایش کنید:

```env
# تغییر نوع دیتابیس
DB_TYPE=postgres

# تنظیمات PostgreSQL
DB_NAME=alamor_vpn
DB_USER=alamor_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# نگه داشتن مسیر SQLite برای مهاجرت
DATABASE_NAME_ALAMOR=database/alamor_vpn.db
```

### مرحله 2: ایجاد جداول PostgreSQL
```bash
python init_db.py
```

### مرحله 3: اجرای مهاجرت
```bash
python migrate_sqlite_to_postgres.py
```

### مرحله 4: بررسی نتایج
```bash
# بررسی لاگ مهاجرت
cat migration.log

# تست اتصال
python -c "
from database.db_manager import DatabaseManager
db = DatabaseManager()
print('✅ Database connection successful')
print(f'Database type: {db.db_type}')
"
```

## عیب‌یابی

### خطای اتصال به PostgreSQL
```
❌ PostgreSQL connection failed: connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**راه‌حل:**
1. بررسی کنید PostgreSQL در حال اجرا باشد:
   ```bash
   sudo systemctl status postgresql
   ```

2. اگر اجرا نیست، آن را شروع کنید:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

### خطای مجوز
```
❌ permission denied for database alamor_vpn
```

**راه‌حل:**
```sql
-- ورود به PostgreSQL
sudo -u postgres psql

-- اعطای مجوزهای بیشتر
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO alamor_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO alamor_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO alamor_user;
```

### خطای فایل SQLite
```
❌ SQLite database file not found
```

**راه‌حل:**
1. بررسی کنید فایل SQLite وجود دارد:
   ```bash
   ls -la database/alamor_vpn.db
   ```

2. مسیر صحیح را در `.env` تنظیم کنید:
   ```env
   DATABASE_NAME_ALAMOR=/path/to/your/alamor_vpn.db
   ```

## بررسی پس از مهاجرت

### 1. بررسی تعداد رکوردها
```sql
-- در PostgreSQL
SELECT 
    'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'servers', COUNT(*) FROM servers
UNION ALL
SELECT 'plans', COUNT(*) FROM plans
UNION ALL
SELECT 'purchases', COUNT(*) FROM purchases;
```

### 2. تست عملکرد ربات
```bash
python main.py
```

### 3. بررسی تنظیمات برندینگ
- وارد پنل ادمین شوید
- به بخش تنظیمات برندینگ بروید
- نام برند را تغییر دهید
- بررسی کنید که در پیام‌های ربات نمایش داده می‌شود

## بازگشت به SQLite (در صورت نیاز)

اگر نیاز به بازگشت به SQLite داشتید:

```env
# تغییر نوع دیتابیس
DB_TYPE=sqlite

# تنظیمات SQLite
DATABASE_NAME_ALAMOR=database/alamor_vpn.db

# غیرفعال کردن متغیرهای PostgreSQL
# DB_NAME=
# DB_USER=
# DB_PASSWORD=
# DB_HOST=
# DB_PORT=
```

## نکات مهم

1. **پشتیبان‌گیری:** قبل از مهاجرت، حتماً از دیتابیس SQLite پشتیبان تهیه کنید:
   ```bash
   cp database/alamor_vpn.db database/alamor_vpn_backup.db
   ```

2. **تست:** ابتدا مهاجرت را در محیط تست انجام دهید.

3. **زمان‌بندی:** مهاجرت را در ساعات کم‌ترافیک انجام دهید.

4. **مانیتورینگ:** در حین مهاجرت، فایل `migration.log` را بررسی کنید.

## پشتیبانی

در صورت بروز مشکل:
1. فایل `migration.log` را بررسی کنید
2. پیام‌های خطا را کپی کنید
3. با تیم پشتیبانی تماس بگیرید
