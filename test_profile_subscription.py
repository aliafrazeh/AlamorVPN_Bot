#!/usr/bin/env python3
"""
Test script to verify the new profile subscription system
که از تمام سرورهای پروفایل دیتا جمع‌آوری می‌کند
"""

import sys
import os
import logging
import json

# Add project path to sys.path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

from database.db_manager import DatabaseManager
from webhook_server import get_profile_subscription_data, get_normal_subscription_data

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_profile_subscription_system():
    """Test the new profile subscription system"""
    print("🧪 Testing Profile Subscription System...\n")
    
    try:
        db_manager = DatabaseManager()
        
        # دریافت تمام خریدهای پروفایل
        profile_purchases = db_manager.get_all_purchases_by_type('profile')
        print(f"Found {len(profile_purchases)} profile purchases")
        
        if not profile_purchases:
            print("❌ No profile purchases found in database")
            return False
        
        # تست اولین خرید پروفایل
        test_purchase = profile_purchases[0]
        print(f"\n📋 Testing purchase ID: {test_purchase['id']}")
        print(f"   Profile ID: {test_purchase.get('profile_id')}")
        print(f"   Sub ID: {test_purchase.get('sub_id')}")
        
        # تست تابع جدید
        subscription_data = get_profile_subscription_data(test_purchase)
        
        if subscription_data:
            print(f"✅ Successfully collected subscription data")
            print(f"   Data length: {len(subscription_data)} characters")
            
            # شمارش تعداد کانفیگ‌ها
            configs = subscription_data.strip().split('\n')
            configs = [c for c in configs if c.strip()]
            print(f"   Number of configs: {len(configs)}")
            
            # نمایش نمونه کانفیگ
            if configs:
                print(f"   Sample config: {configs[0][:100]}...")
            
            return True
        else:
            print("❌ Failed to collect subscription data")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_normal_subscription_system():
    """Test the normal subscription system"""
    print("\n🧪 Testing Normal Subscription System...\n")
    
    try:
        db_manager = DatabaseManager()
        
        # دریافت تمام خریدهای عادی
        normal_purchases = db_manager.get_all_purchases_by_type('normal')
        print(f"Found {len(normal_purchases)} normal purchases")
        
        if not normal_purchases:
            print("❌ No normal purchases found in database")
            return False
        
        # تست اولین خرید عادی
        test_purchase = normal_purchases[0]
        print(f"\n📋 Testing purchase ID: {test_purchase['id']}")
        print(f"   Server ID: {test_purchase.get('server_id')}")
        print(f"   Sub ID: {test_purchase.get('sub_id')}")
        
        # تست تابع جدید
        subscription_data = get_normal_subscription_data(test_purchase)
        
        if subscription_data:
            print(f"✅ Successfully collected subscription data")
            print(f"   Data length: {len(subscription_data)} characters")
            
            # شمارش تعداد کانفیگ‌ها
            configs = subscription_data.strip().split('\n')
            configs = [c for c in configs if c.strip()]
            print(f"   Number of configs: {len(configs)}")
            
            return True
        else:
            print("❌ Failed to collect subscription data")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_profile_inbounds():
    """Test profile inbounds retrieval"""
    print("\n🧪 Testing Profile Inbounds...\n")
    
    try:
        db_manager = DatabaseManager()
        
        # دریافت تمام پروفایل‌ها
        profiles = db_manager.get_all_profiles(only_active=True)
        print(f"Found {len(profiles)} active profiles")
        
        if not profiles:
            print("❌ No profiles found in database")
            return False
        
        # تست اولین پروفایل
        test_profile = profiles[0]
        print(f"\n📋 Testing profile ID: {test_profile['id']}")
        print(f"   Name: {test_profile['name']}")
        
        # دریافت اینباندهای پروفایل
        profile_inbounds = db_manager.get_inbounds_for_profile(test_profile['id'], with_server_info=True)
        print(f"   Found {len(profile_inbounds)} inbounds")
        
        # گروه‌بندی بر اساس سرور
        inbounds_by_server = {}
        for inbound_info in profile_inbounds:
            server_id = inbound_info['server']['id']
            if server_id not in inbounds_by_server:
                inbounds_by_server[server_id] = []
            inbounds_by_server[server_id].append(inbound_info)
        
        print(f"   Servers involved: {len(inbounds_by_server)}")
        
        for server_id, server_inbounds in inbounds_by_server.items():
            server_name = server_inbounds[0]['server']['name']
            print(f"     - Server {server_name}: {len(server_inbounds)} inbounds")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Profile Subscription System Tests...\n")
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Profile subscription system
    if test_profile_subscription_system():
        success_count += 1
    
    # Test 2: Normal subscription system  
    if test_normal_subscription_system():
        success_count += 1
    
    # Test 3: Profile inbounds
    if test_profile_inbounds():
        success_count += 1
    
    print(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! The new profile subscription system is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
