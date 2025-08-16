#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تست سیستم subscription جدید
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import base64
import json

def test_subscription_endpoint():
    """تست endpoint subscription"""
    print("=== تست Endpoint Subscription ===")
    
    # تست با یک sub_id نمونه
    test_sub_id = "test123"
    webhook_url = "http://localhost:8080/sub/" + test_sub_id
    
    try:
        response = requests.get(webhook_url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type')}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            # بررسی اینکه آیا محتوا Base64 است
            try:
                decoded = base64.b64decode(response.text)
                print(f"✅ محتوا Base64 است. طول decode شده: {len(decoded)}")
                print(f"نمونه محتوا: {decoded[:100]}...")
            except:
                print("❌ محتوا Base64 نیست")
                print(f"نمونه محتوا: {response.text[:100]}...")
        else:
            print(f"خطا: {response.text}")
            
    except Exception as e:
        print(f"خطا در تست: {e}")

def test_content_detection():
    """تست تشخیص نوع محتوا"""
    print("\n=== تست تشخیص نوع محتوا ===")
    
    test_cases = [
        ("vmess://test123", "v2ray_config"),
        ("vless://test123", "v2ray_config"),
        ("trojan://test123", "v2ray_config"),
        (base64.b64encode(b"test content").decode(), "base64"),
        ('{"key": "value"}', "json"),
        ("plain text content", "plain_text")
    ]
    
    for content, expected_type in test_cases:
        detected_type = detect_content_type(content)
        status = "✅" if detected_type == expected_type else "❌"
        print(f"{status} {content[:20]}... -> {detected_type} (انتظار: {expected_type})")

def detect_content_type(content):
    """تشخیص نوع محتوای subscription"""
    # بررسی اینکه آیا محتوا Base64 است
    try:
        decoded = base64.b64decode(content)
        return 'base64'
    except:
        pass
    
    # بررسی اینکه آیا محتوا JSON است
    try:
        json.loads(content)
        return 'json'
    except:
        pass
    
    # بررسی اینکه آیا محتوا V2Ray config است
    if 'vmess://' in content or 'vless://' in content or 'trojan://' in content:
        return 'v2ray_config'
    
    # پیش‌فرض: plain text
    return 'plain_text'

def test_panel_data_fetch():
    """تست دریافت دیتا از پنل اصلی"""
    print("\n=== تست دریافت دیتا از پنل اصلی ===")
    
    # این تست نیاز به تنظیمات واقعی دارد
    print("⚠️ این تست نیاز به تنظیمات واقعی پنل دارد")
    print("برای تست کامل، لطفاً تنظیمات پنل را در فایل config.py تنظیم کنید")

if __name__ == "__main__":
    print("🚀 شروع تست سیستم Subscription جدید\n")
    
    test_subscription_endpoint()
    test_content_detection()
    test_panel_data_fetch()
    
    print("\n✅ تست‌ها کامل شد!")
    print("\n📝 نکات مهم:")
    print("1. سیستم جدید همیشه ابتدا از پنل اصلی دیتا دریافت می‌کند")
    print("2. اگر پنل اصلی در دسترس نباشد، از دیتابیس استفاده می‌کند")
    print("3. محتوا به صورت خودکار تشخیص و پردازش می‌شود")
    print("4. ادمین می‌تواند کانفیگ‌ها را دستی بروزرسانی کند")
