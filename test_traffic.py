#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تست قابلیت‌های جدید ترافیک
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import helpers
from database.db_manager import DatabaseManager

def test_traffic_formatting():
    """تست تابع تبدیل حجم"""
    print("=== تست تبدیل حجم ===")
    
    test_cases = [
        0,
        1024,
        1024 * 1024,
        1024 * 1024 * 1024,
        1024 * 1024 * 1024 * 2.5,
        None
    ]
    
    for value in test_cases:
        formatted = helpers.format_traffic_size(value)
        print(f"{value} -> {formatted}")

def test_days_calculation():
    """تست محاسبه روزهای باقی‌مانده"""
    print("\n=== تست محاسبه روزهای باقی‌مانده ===")
    
    from datetime import datetime, timedelta
    
    # تست تاریخ‌های مختلف
    now = datetime.now()
    test_cases = [
        now + timedelta(days=5),  # 5 روز آینده
        now + timedelta(days=1),  # فردا
        now,                      # امروز
        now - timedelta(days=1),  # دیروز
        None                      # بدون تاریخ
    ]
    
    for date in test_cases:
        days = helpers.calculate_days_remaining(date)
        print(f"{date} -> {days} روز باقی‌مانده")

def test_database_functions():
    """تست توابع دیتابیس"""
    print("\n=== تست توابع دیتابیس ===")
    
    try:
        db = DatabaseManager()
        
        # تست دریافت UUID های کلاینت
        user_id = 1  # تست با کاربر ID 1
        uuids = db.get_all_client_uuids_for_user(user_id)
        print(f"UUID های کلاینت برای کاربر {user_id}: {len(uuids)} مورد")
        
        for uuid_info in uuids:
            print(f"  - UUID: {uuid_info['client_uuid']}, Server: {uuid_info['server_id']}")
            
            # تست دریافت اطلاعات ترافیک
            traffic_info = db.get_client_traffic_info(uuid_info['client_uuid'])
            if traffic_info:
                print(f"    ترافیک: {traffic_info}")
            else:
                print(f"    ترافیک: در دسترس نیست")
                
    except Exception as e:
        print(f"خطا در تست دیتابیس: {e}")

if __name__ == "__main__":
    print("🚀 شروع تست قابلیت‌های ترافیک\n")
    
    test_traffic_formatting()
    test_days_calculation()
    test_database_functions()
    
    print("\n✅ تست‌ها کامل شد!")
