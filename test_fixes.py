#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تست رفع مشکلات
"""

import os
import sys
import logging

# اضافه کردن مسیر پروژه
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import *
from database.db_manager import DatabaseManager
from utils.helpers import calculate_days_remaining

# تنظیم لاگینگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_days_remaining():
    """تست تابع calculate_days_remaining"""
    print("🔍 تست تابع calculate_days_remaining...")
    
    from datetime import datetime, timedelta
    
    # تست 1: تاریخ آینده
    future_date = datetime.now() + timedelta(days=5)
    result = calculate_days_remaining(future_date)
    print(f"تاریخ آینده (5 روز): {result}")
    
    # تست 2: تاریخ گذشته
    past_date = datetime.now() - timedelta(days=3)
    result = calculate_days_remaining(past_date)
    print(f"تاریخ گذشته (3 روز): {result}")
    
    # تست 3: None
    result = calculate_days_remaining(None)
    print(f"None: {result}")
    
    # تست 4: رشته
    date_str = "2024-12-31 23:59:59"
    result = calculate_days_remaining(date_str)
    print(f"رشته تاریخ: {result}")

def test_database_connection():
    """تست اتصال دیتابیس"""
    print("\n🔍 تست اتصال دیتابیس...")
    
    try:
        db = DatabaseManager()
        print("✅ اتصال دیتابیس موفق")
        
        # تست دریافت خریدهای فعال
        active_purchases = db.get_all_active_purchases()
        print(f"تعداد خریدهای فعال: {len(active_purchases)}")
        
        if active_purchases:
            purchase = active_purchases[0]
            print(f"نمونه خرید: ID={purchase['id']}, sub_id={purchase.get('sub_id')}")
            
            # تست دریافت اطلاعات ترافیک
            if purchase.get('client_uuid'):
                traffic_info = db.get_client_traffic_info(purchase['client_uuid'])
                print(f"اطلاعات ترافیک: {traffic_info}")
        
    except Exception as e:
        print(f"❌ خطا در اتصال دیتابیس: {e}")

def test_webhook_endpoint():
    """تست endpoint webhook"""
    print("\n🔍 تست endpoint webhook...")
    
    import requests
    
    try:
        # تست endpoint اصلی
        webhook_domain = os.getenv('WEBHOOK_DOMAIN', 'localhost:8080')
        test_url = f"https://{webhook_domain}/admin/update_configs/1"
        
        print(f"تست URL: {test_url}")
        
        # تست بدون API key
        response = requests.post(test_url, timeout=10)
        print(f"بدون API key - Status: {response.status_code}")
        
        # تست با API key اشتباه
        headers = {'Authorization': 'Bearer wrong-key'}
        response = requests.post(test_url, headers=headers, timeout=10)
        print(f"با API key اشتباه - Status: {response.status_code}")
        
    except Exception as e:
        print(f"❌ خطا در تست webhook: {e}")

def main():
    """تابع اصلی"""
    print("🚀 شروع تست رفع مشکلات...\n")
    
    # تست 1: تابع calculate_days_remaining
    test_days_remaining()
    
    # تست 2: اتصال دیتابیس
    test_database_connection()
    
    # تست 3: endpoint webhook
    test_webhook_endpoint()
    
    print("\n✅ تست‌ها کامل شد!")

if __name__ == "__main__":
    main()
