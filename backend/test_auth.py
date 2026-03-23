import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/auth"

def test_register():
    print(f"Testing Registration against {BASE_URL}/register...")
    payload = {
        "email": f"test_{int(time.time())}@example.com",
        "password": "securepassword123",
        "full_name": "Test User"
    }
    try:
        response = requests.post(f"{BASE_URL}/register", json=payload, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error: {e}")
    return None

def test_login(email):
    print(f"\nTesting Login against {BASE_URL}/token...")
    payload = {
        "username": email,
        "password": "securepassword123"
    }
    try:
        response = requests.post(f"{BASE_URL}/token", data=payload, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    result = test_register()
    if result:
        test_login(result['user']['email'])
