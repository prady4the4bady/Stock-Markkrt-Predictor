"""Test BTC and Forex specifically"""
import requests

# Test BTC/USDT
print("Testing BTC/USDT...")
try:
    r = requests.get('http://127.0.0.1:8000/api/predict/BTC/USDT?days=7&is_crypto=true', timeout=120)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"  Confidence: {d.get('confidence', 'N/A')}%")
    else:
        print(f"  Error: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# Test EUR/USD
print("\nTesting EURUSD=X...")
try:
    r = requests.get('http://127.0.0.1:8000/api/predict/EURUSD=X?days=7', timeout=120)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"  Confidence: {d.get('confidence', 'N/A')}%")
    else:
        print(f"  Error: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# Test Gold (commodity)
print("\nTesting GC=F (Gold)...")
try:
    r = requests.get('http://127.0.0.1:8000/api/predict/GC=F?days=7', timeout=120)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"  Confidence: {d.get('confidence', 'N/A')}%")
        print(f"  Current Price: ${d.get('current_price', 'N/A')}")
    else:
        print(f"  Error: {r.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# Test Assets endpoint
print("\nTesting /api/assets...")
try:
    r = requests.get('http://127.0.0.1:8000/api/assets')
    d = r.json()
    print(f"  Stocks: {len(d.get('stocks', []))}")
    print(f"  Crypto: {len(d.get('crypto', []))}")
    print(f"  Forex: {len(d.get('forex', []))}")
    print(f"  Indices: {len(d.get('indices', []))}")
    print(f"  Commodities: {len(d.get('commodities', []))}")
    print(f"  Commodities list: {d.get('commodities', [])}")
except Exception as e:
    print(f"  Error: {e}")
