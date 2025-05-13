#!/usr/bin/env python3
"""
Test script to verify the reorganized tools are working correctly.
This is a simple smoke test to ensure imports are working.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

def test_common_imports():
    """Test imports from the common module."""
    print("Testing common module imports...")
    try:
        from tools.common.utils import setup_path, get_random_user_agent
        from tools.common.config import COOKIE_FILE, FETCH_OUTPUT_DIR, SEARCH_OUTPUT_DIR
        print("✓ Common module imports successful!")
        return True
    except Exception as e:
        print(f"✗ Error importing from common module: {e}")
        return False

def test_fetch_imports():
    """Test imports from the fetch module."""
    print("Testing fetch module imports...")
    try:
        from tools.fetch.fetch import fetch_page
        from tools.fetch.extract import extract_job_data_from_html
        from tools.fetch.db_access import DatabaseInterface
        print("✓ Fetch module imports successful!")
        return True
    except Exception as e:
        print(f"✗ Error importing from fetch module: {e}")
        return False

def test_search_imports():
    """Test imports from the search module."""
    print("Testing search module imports...")
    try:
        from tools.search.search import search_jobs, fetch_job_details
        print("✓ Search module imports successful!")
        return True
    except Exception as e:
        print(f"✗ Error importing from search module: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("Running tests for reorganized tools")
    print("=" * 50)
    
    test_results = []
    test_results.append(("Common module imports", test_common_imports()))
    test_results.append(("Fetch module imports", test_fetch_imports()))
    test_results.append(("Search module imports", test_search_imports()))
    
    print("\nTest Results:")
    print("-" * 50)
    all_passed = True
    for name, result in test_results:
        status = "PASS" if result else "FAIL"
        if not result:
            all_passed = False
        print(f"{name}: {status}")
    
    print("-" * 50)
    if all_passed:
        print("All tests passed! The reorganized tools should be working correctly.")
        return 0
    else:
        print("Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())