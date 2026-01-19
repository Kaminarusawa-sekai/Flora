#!/usr/bin/env python3
"""
Test script to verify text_to_sql capability can be found correctly
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from tasks.capabilities import get_capability
from tasks.capabilities.text_to_sql.text_to_sql import ITextToSQLCapability

def test_text_to_sql_capability():
    """Test that text_to_sql capability can be found"""
    print("Testing text_to_sql capability...")
    
    try:
        # This should work now
        text_to_sql_cap = get_capability("text_to_sql", ITextToSQLCapability)
        print("✅ SUCCESS: text_to_sql capability found!")
        print(f"   Capability type: {text_to_sql_cap.get_capability_type()}")
        return True
    except Exception as e:
        print(f"❌ FAILURE: text_to_sql capability not found: {e}")
        return False

if __name__ == "__main__":
    success = test_text_to_sql_capability()
    sys.exit(0 if success else 1)