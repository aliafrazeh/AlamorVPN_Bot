#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug script for webhook server issues
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN')
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')

def test_purchase_info(purchase_id):
    """Test purchase info endpoint"""
    if not WEBHOOK_DOMAIN:
        print("❌ WEBHOOK_DOMAIN not set")
        return
    
    url = f"https://{WEBHOOK_DOMAIN}/admin/test/{purchase_id}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"🔍 Testing purchase {purchase_id}:")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Purchase found:")
            print(f"      - Profile ID: {data.get('profile_id')}")
            print(f"      - Server ID: {data.get('server_id')}")
            print(f"      - Sub ID: {data.get('sub_id')}")
            print(f"      - Active: {data.get('is_active')}")
            print(f"      - Has Configs: {data.get('has_configs')}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

def test_update_configs(purchase_id):
    """Test update configs endpoint"""
    if not WEBHOOK_DOMAIN or not ADMIN_API_KEY:
        print("❌ WEBHOOK_DOMAIN or ADMIN_API_KEY not set")
        return
    
    url = f"https://{WEBHOOK_DOMAIN}/admin/update_configs/{purchase_id}"
    headers = {
        'Authorization': f'Bearer {ADMIN_API_KEY}'
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        print(f"🔄 Testing update configs for purchase {purchase_id}:")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Success: {response.text}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

def main():
    """Main test function"""
    print("🔧 Webhook Server Debug Tool")
    print("=" * 50)
    
    # Test configuration
    print(f"🌐 Webhook Domain: {WEBHOOK_DOMAIN or 'Not set'}")
    print(f"🔑 Admin API Key: {'Set' if ADMIN_API_KEY else 'Not set'}")
    print()
    
    # Test purchase IDs from the error logs
    purchase_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    
    print("📋 Testing purchase information:")
    for purchase_id in purchase_ids[:3]:  # Test first 3
        test_purchase_info(purchase_id)
        print()
    
    print("🔄 Testing config updates:")
    for purchase_id in purchase_ids[:3]:  # Test first 3
        test_update_configs(purchase_id)
        print()

if __name__ == "__main__":
    main()
