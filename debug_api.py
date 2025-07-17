#!/usr/bin/env python3
"""
Debug script to test the staging API endpoints.
"""

import requests
import json

def test_staging_api():
    """Test if the staging API is accessible."""
    base_url = "https://staging.dashboard.kernelci.org:9000/api/"
    
    print("🔍 Testing staging API accessibility...")
    
    try:
        # Test a simple endpoint first
        response = requests.get(f"{base_url}test/", timeout=10)
        print(f"  API Base Response: {response.status_code}")
        
        # Test with a known test ID (this will likely fail but shows the API structure)
        test_id = "test_example_id"
        history_url = f"{base_url}test/{test_id}/status_history/"
        
        print(f"  Testing: {history_url}")
        response = requests.get(history_url, timeout=10)
        print(f"  Status History Response: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ API is accessible and responding")
        elif response.status_code == 404:
            print("  ⚠️ API is accessible but test ID not found (expected)")
        else:
            print(f"  ❌ API returned unexpected status: {response.status_code}")
            
    except requests.exceptions.SSLError as e:
        print(f"  ❌ SSL Error: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Connection Error: {e}")
    except requests.exceptions.Timeout as e:
        print(f"  ❌ Timeout Error: {e}")
    except Exception as e:
        print(f"  ❌ Unexpected Error: {e}")

def test_production_api():
    """Test if the production API is accessible."""
    base_url = "https://dashboard.kernelci.org/api/"
    
    print("\n🔍 Testing production API accessibility...")
    
    try:
        # Test a simple endpoint first
        response = requests.get(f"{base_url}test/", timeout=10)
        print(f"  API Base Response: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Production API is accessible")
        else:
            print(f"  ❌ Production API returned status: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Production API Error: {e}")

if __name__ == "__main__":
    test_staging_api()
    test_production_api()