"""
Simple test script to verify backend API functionality
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:5000/api"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_protocols():
    """Test the protocols endpoint"""
    print("Testing protocols endpoint...")
    response = requests.get(f"{BASE_URL}/protocols")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        protocols = response.json()
        print(f"Protocols: {list(protocols['protocols'].keys())}")
    print()

def test_register():
    """Test merchant registration"""
    print("Testing merchant registration...")
    merchant_data = {
        "merchant_name": "Test Merchant",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = requests.post(f"{BASE_URL}/register", json=merchant_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_login():
    """Test merchant login"""
    print("Testing merchant login...")
    credentials = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = requests.post(f"{BASE_URL}/login", json=credentials)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    return response.cookies

if __name__ == "__main__":
    print("Payment Terminal API Test")
    print("=" * 30)
    
    # Test health check
    test_health_check()
    
    # Test protocols endpoint
    test_protocols()
    
    # Test registration
    test_register()
    
    # Test login
    session_cookies = test_login()
    
    print("API tests completed.")