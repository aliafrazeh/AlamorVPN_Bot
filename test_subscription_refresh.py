#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تست سیستم بروزرسانی لینک subscription
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def test_webhook_endpoint():
    """تست endpoint بروزرسانی کانفیگ‌ها"""
    print("=== تست Endpoint بروزرسانی کانفیگ‌ها ===")
    
    # تست با یک purchase_id نمونه
    test_purchase_id = "1"
    webhook_url = f"http://localhost:8080/admin/update_configs/{test_purchase_id}"
    headers = {
        'Authorization': 'Bearer your-secret-key'
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ بروزرسانی موفق بود")
        else:
            print("❌ بروزرسانی ناموفق بود")
            
    except Exception as e:
        print(f"خطا در تست: {e}")

def test_subscription_endpoint():
    """تست endpoint subscription"""
    print("\n=== تست Endpoint Subscription ===")
    
    # تست با یک sub_id نمونه
    test_sub_id = "test123"
    webhook_url = f"http://localhost:8080/sub/{test_sub_id}"
    
    try:
        response = requests.get(webhook_url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type')}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            print("✅ لینک subscription در دسترس است")
            print(f"نمونه محتوا: {response.text[:100]}...")
        else:
            print(f"❌ خطا: {response.text}")
            
    except Exception as e:
        print(f"خطا در تست: {e}")

def test_admin_api_key():
    """تست API key ادمین"""
    print("\n=== تست API Key ادمین ===")
    
    # تست با API key اشتباه
    test_purchase_id = "1"
    webhook_url = f"http://localhost:8080/admin/update_configs/{test_purchase_id}"
    headers = {
        'Authorization': 'Bearer wrong-key'
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, timeout=10)
        print(f"Status Code (wrong key): {response.status_code}")
        
        if response.status_code == 401:
            print("✅ احراز هویت درست کار می‌کند")
        else:
            print("❌ احراز هویت مشکل دارد")
            
    except Exception as e:
        print(f"خطا در تست: {e}")

def test_missing_auth():
    """تست بدون احراز هویت"""
    print("\n=== تست بدون احراز هویت ===")
    
    test_purchase_id = "1"
    webhook_url = f"http://localhost:8080/admin/update_configs/{test_purchase_id}"
    
    try:
        response = requests.post(webhook_url, timeout=10)
        print(f"Status Code (no auth): {response.status_code}")
        
        if response.status_code == 401:
            print("✅ احراز هویت اجباری است")
        else:
            print("❌ احراز هویت اجباری نیست")
            
    except Exception as e:
        print(f"خطا در تست: {e}")

if __name__ == "__main__":
    print("🚀 شروع تست سیستم بروزرسانی لینک Subscription\n")
    
    test_webhook_endpoint()
    test_subscription_endpoint()
    test_admin_api_key()
    test_missing_auth()
    
    print("\n✅ تست‌ها کامل شد!")
    print("\n📝 نکات مهم:")
    print("1. سیستم بروزرسانی لینک از پنل اصلی دیتا دریافت می‌کند")
    print("2. ادمین می‌تواند همه لینک‌ها را یکجا بروزرسانی کند")
    print("3. کاربران می‌توانند لینک خود را جداگانه بروزرسانی کنند")
    print("4. احراز هویت با API key انجام می‌شود")
    print("5. در صورت خطا، سیستم از دیتای کش استفاده می‌کند")
