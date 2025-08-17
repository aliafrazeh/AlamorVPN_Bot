#!/usr/bin/env python3
"""
Test script to verify fixes for the reported errors:
1. TypeError: '>' not supported between instances of 'NoneType' and 'int'
2. string indices must be integers
3. HTTP 500 errors from webhook server
"""

import sys
import os
import logging

# Add project path to sys.path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

from utils.helpers import calculate_days_remaining
from database.db_manager import DatabaseManager
import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_calculate_days_remaining():
    """Test the calculate_days_remaining function with various inputs"""
    print("Testing calculate_days_remaining function...")
    
    # Test with None
    result = calculate_days_remaining(None)
    print(f"None input: {result}")
    assert result is None, "Should return None for None input"
    
    # Test with empty string
    result = calculate_days_remaining("")
    print(f"Empty string input: {result}")
    assert result is None, "Should return None for empty string"
    
    # Test with valid date string
    future_date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
    result = calculate_days_remaining(future_date)
    print(f"Future date input: {result}")
    assert isinstance(result, int), "Should return integer for valid date"
    assert result > 0, "Should return positive number for future date"
    
    # Test with past date
    past_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
    result = calculate_days_remaining(past_date)
    print(f"Past date input: {result}")
    assert isinstance(result, int), "Should return integer for valid date"
    assert result < 0, "Should return negative number for past date"
    
    print("✅ calculate_days_remaining tests passed!")

def test_database_functions():
    """Test database functions that were causing string indices errors"""
    print("\nTesting database functions...")
    
    try:
        db_manager = DatabaseManager()
        
        # Test get_purchase_by_client_uuid with None
        result = db_manager.get_purchase_by_client_uuid(None)
        print(f"get_purchase_by_client_uuid(None): {result}")
        assert result is None, "Should return None for None input"
        
        # Test get_purchase_by_client_uuid with empty string
        result = db_manager.get_purchase_by_client_uuid("")
        print(f"get_purchase_by_client_uuid(''): {result}")
        assert result is None, "Should return None for empty string"
        
        # Test get_all_client_uuids_for_user with invalid user_id
        result = db_manager.get_all_client_uuids_for_user(999999)
        print(f"get_all_client_uuids_for_user(999999): {result}")
        assert isinstance(result, list), "Should return list"
        
        print("✅ Database function tests passed!")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True

def test_webhook_functions():
    """Test webhook server functions"""
    print("\nTesting webhook server functions...")
    
    try:
        from webhook_server import process_subscription_content
        
        # Test with None
        result = process_subscription_content(None)
        print(f"process_subscription_content(None): {result}")
        assert result is None, "Should return None for None input"
        
        # Test with empty string
        result = process_subscription_content("")
        print(f"process_subscription_content(''): {result}")
        assert result is None, "Should return None for empty string"
        
        # Test with valid Base64 content
        import base64
        test_content = base64.b64encode("test content".encode('utf-8')).decode('utf-8')
        result = process_subscription_content(test_content)
        print(f"process_subscription_content(Base64): {result is not None}")
        assert result is not None, "Should return result for valid Base64"
        assert result.get('is_base64') is True, "Should detect Base64 content"
        
        # Test with plain text
        result = process_subscription_content("plain text content")
        print(f"process_subscription_content(plain text): {result is not None}")
        assert result is not None, "Should return result for plain text"
        assert result.get('is_base64') is False, "Should detect plain text"
        
        print("✅ Webhook function tests passed!")
        
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🧪 Running tests for AlamorVPN Bot fixes...\n")
    
    # Test 1: calculate_days_remaining function
    try:
        test_calculate_days_remaining()
    except Exception as e:
        print(f"❌ calculate_days_remaining test failed: {e}")
        return False
    
    # Test 2: Database functions
    if not test_database_functions():
        return False
    
    # Test 3: Webhook functions
    if not test_webhook_functions():
        return False
    
    print("\n🎉 All tests passed! The fixes should resolve the reported errors.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
