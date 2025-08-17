# 🚀 راهنمای تست سریع Webhook Server

## 🔍 **مراحل تست:**

### **1. تست ساده webhook server:**
```bash
# روی سرور اجرا کنید
curl -X GET "https://YOUR_DOMAIN/test"
```

**انتظار:** JSON response با status "ok"

### **2. تست endpoint اطلاعات purchase:**
```bash
# تست purchase با ID 1
curl -X GET "https://YOUR_DOMAIN/admin/test/1"
```

**انتظار:** JSON response با اطلاعات purchase

### **3. بررسی لاگ‌های webhook server:**
```bash
# لاگ‌های سیستم
tail -f /var/log/syslog | grep webhook

# یا لاگ‌های خاص
tail -f /var/log/syslog | grep "🔍\|✅\|❌\|⚠️"
```

### **4. تست دکمه "بروزرسانی همه لینک‌ها":**
1. در ربات، منوی ادمین برید
2. دکمه "🔄 بروزرسانی همه لینک‌ها" رو بزنید
3. لاگ‌ها رو بررسی کنید

## 📋 **نتایج مورد انتظار:**

### **✅ موفق:**
```
INFO: 🔍 Simple test endpoint called
INFO: ✅ Simple test successful
INFO: 🌐 Webhook Domain: yourdomain.com
INFO: 🔗 Active Domain (User Subscriptions): userdomain.com
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123
INFO: ✅ Successfully fetched subscription data for purchase 1
```

### **❌ مشکل:**
```
ERROR: ❌ Error in get_profile_subscription_data: 'sub_id' is not defined
ERROR: ❌ Traceback: ...
```

## 🛠️ **راه‌حل مشکلات:**

### **مشکل 1: Webhook server کار نمی‌کنه**
```bash
# بررسی process
ps aux | grep webhook

# اجرای مجدد
cd /var/www/alamorvpn_bot
python3 webhook_server.py
```

### **مشکل 2: خطای sub_id**
- مشکل حل شده در کد جدید
- webhook server رو restart کنید

### **مشکل 3: لاگ‌ها نشون نمی‌دن**
```bash
# بررسی لاگ‌های سیستم
journalctl -u your-bot-service -f

# یا لاگ‌های مستقیم
tail -f /var/log/syslog | grep python3
```

## 🎯 **مرحله بعدی:**

بعد از تست‌های بالا، نتایج رو بگید تا مشکل دقیق مشخص بشه.

---
**تاریخ:** $(date)
**وضعیت:** آماده برای تست
