#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تست تابع calculate_days_remaining
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import helpers
from datetime import datetime, timedelta

def test_calculate_days_remaining():
    """تست تابع محاسبه روزهای باقی‌مانده"""
    print("=== تست تابع calculate_days_remaining ===")
    
    # تست 1: تاریخ آینده
    future_date = datetime.now() + timedelta(days=5)
    result = helpers.calculate_days_remaining(future_date)
    print(f"تاریخ آینده (5 روز): {result} روز باقی‌مانده")
    
    # تست 2: تاریخ گذشته
    past_date = datetime.now() - timedelta(days=3)
    result = helpers.calculate_days_remaining(past_date)
    print(f"تاریخ گذشته (3 روز): {result} روز باقی‌مانده")
    
    # تست 3: تاریخ امروز
    today = datetime.now()
    result = helpers.calculate_days_remaining(today)
    print(f"تاریخ امروز: {result} روز باقی‌مانده")
    
    # تست 4: رشته تاریخ
    date_str = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
    result = helpers.calculate_days_remaining(date_str)
    print(f"رشته تاریخ (10 روز): {result} روز باقی‌مانده")
    
    # تست 5: None
    result = helpers.calculate_days_remaining(None)
    print(f"None: {result}")
    
    # تست 6: تاریخ با timezone (اگر pytz موجود باشد)
    try:
        import pytz
        tz = pytz.timezone('UTC')
        tz_date = datetime.now(tz)
        result = helpers.calculate_days_remaining(tz_date)
        print(f"تاریخ با timezone: {result} روز باقی‌مانده")
    except ImportError:
        print("pytz موجود نیست، تست timezone رد شد")

def test_traffic_formatting():
    """تست تابع تبدیل حجم"""
    print("\n=== تست تابع format_traffic_size ===")
    
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

if __name__ == "__main__":
    print("🚀 شروع تست توابع helpers\n")
    
    test_calculate_days_remaining()
    test_traffic_formatting()
    
    print("\n✅ تست‌ها کامل شد!")
