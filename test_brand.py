#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.db_manager import DatabaseManager

def test_brand_name():
    try:
        db = DatabaseManager()
        brand = db.get_setting('brand_name')
        print(f"Brand name in DB: '{brand}'")
        
        if brand is None:
            print("Brand name is None - not set in database")
        elif brand == "":
            print("Brand name is empty string")
        else:
            print(f"Brand name is set to: {brand}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_brand_name()
