# 📊 راهنمای لاگ‌های بهبود یافته برای بروزرسانی Subscription

## 🎯 **هدف:**

لاگ‌های دقیق‌تر برای عیب‌یابی مشکلات بروزرسانی subscription، شامل:
- آدرس‌های دقیق درخواست‌ها
- اطلاعات دامنه‌ها
- جزئیات سرورها و پنل‌ها
- وضعیت fallback mechanism

## 🔍 **لاگ‌های جدید:**

### **1. اطلاعات دامنه‌ها:**
```
INFO: 🌐 Webhook Domain: yourdomain.com
INFO: 🔗 Active Domain (User Subscriptions): userdomain.com
```

### **2. جزئیات درخواست به پنل:**
```
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Subscription Path: sub
INFO:    Sub ID: abc123def456
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123def456
```

### **3. جزئیات پروفایل:**
```
INFO: 📋 Profile Details:
INFO:    Profile ID: 1
INFO:    Total Inbounds: 5
INFO:    Sub ID: abc123def456
INFO:    Servers involved:
INFO:      - Server 1: Germany-Hetzner (2 inbounds)
INFO:      - Server 2: Netherlands-OVH (3 inbounds)
```

### **4. پردازش هر سرور:**
```
INFO: 🔄 Processing Server Germany-Hetzner (ID: 1)
INFO:    Inbounds on this server: 2
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Subscription Path: sub
INFO:    Sub ID: abc123def456
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123def456
INFO:    ✅ Success: Added 2 configs from server Germany-Hetzner
```

### **5. اطلاعات دیتای دریافت شده:**
```
INFO: ✅ Successfully fetched subscription data for purchase 1
INFO:    📄 Data length: 2048 characters
INFO:    📊 Data source: Panel
INFO:    🔓 Content type: Base64 (decoded)
INFO: ✅ Found 5 valid configs for purchase 1
INFO:    📋 Config types: vmess, vless, trojan
```

### **6. استفاده از دیتای cached:**
```
WARNING: ⚠️ Could not fetch subscription data from panel for purchase 1, using cached data
INFO: ✅ Using cached configs for purchase 1: 5 configs
INFO:    📄 Cached data length: 2048 characters
```

### **7. ذخیره در دیتابیس:**
```
INFO: 💾 Saving configs to database for purchase 1
INFO: ✅ Successfully updated cached configs for purchase 1
INFO:    📊 Summary: 5 configs saved to database
```

## 🚀 **مزایای لاگ‌های جدید:**

### **1. عیب‌یابی دقیق:**
- آدرس‌های کامل درخواست‌ها
- تشخیص مشکلات شبکه
- شناسایی سرورهای مشکل‌دار

### **2. نظارت بر عملکرد:**
- تعداد config های پردازش شده
- نوع محتوای دریافتی
- سرعت پردازش

### **3. مدیریت دامنه:**
- نمایش دامنه webhook فعلی
- نمایش دامنه subscription کاربران
- تشخیص مشکلات دامنه

## 📋 **نحوه استفاده:**

### **1. بررسی لاگ‌ها:**
```bash
# بررسی لاگ‌های webhook server
tail -f /var/log/webhook_server.log | grep "📡\|🌐\|🔗\|📋\|🔄\|✅\|❌\|⚠️"
```

### **2. فیلتر کردن لاگ‌ها:**
```bash
# فقط لاگ‌های مربوط به purchase خاص
grep "purchase 1" /var/log/webhook_server.log

# فقط لاگ‌های مربوط به سرور خاص
grep "Germany-Hetzner" /var/log/webhook_server.log

# فقط خطاها
grep "❌" /var/log/webhook_server.log
```

### **3. بررسی مشکلات:**
```bash
# بررسی درخواست‌های ناموفق
grep "Could not fetch" /var/log/webhook_server.log

# بررسی استفاده از cached data
grep "using cached data" /var/log/webhook_server.log

# بررسی مشکلات دامنه
grep "Webhook Domain\|Active Domain" /var/log/webhook_server.log
```

## 🔧 **نمونه عیب‌یابی:**

### **مشکل: HTTP 500 در بروزرسانی**
```
INFO: Starting update_cached_configs_from_panel for purchase 1
INFO: 🌐 Webhook Domain: yourdomain.com
INFO: 🔗 Active Domain (User Subscriptions): userdomain.com
INFO: Processing normal purchase 1 with server_id 1
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Subscription Path: sub
INFO:    Sub ID: abc123def456
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123def456
ERROR: Error fetching subscription data from panel: Connection timeout
WARNING: ⚠️ Could not fetch subscription data from panel for purchase 1, using cached data
INFO: ✅ Using cached configs for purchase 1: 5 configs
```

### **راه‌حل:**
1. بررسی دسترسی به پنل: `http://1.2.3.4:54321`
2. بررسی وجود sub_id در پنل
3. بررسی تنظیمات شبکه

## 🎉 **نتیجه:**

**حالا می‌تونید دقیقاً ببینید:**
- به کدام آدرس درخواست می‌زنه
- کدام دامنه‌ها تنظیم شدن
- کجا مشکل داره
- چرا از cached data استفاده می‌کنه

---
**تاریخ بروزرسانی:** $(date)
**وضعیت:** ✅ پیاده‌سازی شده و آماده استفاده
