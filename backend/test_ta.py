"""Quick test for technical analysis"""
import requests
import json

# Test fresh prediction (uncached)
r = requests.get('http://127.0.0.1:8000/api/predict/MSFT?days=7', timeout=120)
data = r.json()
print('MSFT Prediction (fresh):')
print(f'  Confidence: {data.get("confidence", 0)}%')
ta = data.get('technical_analysis')
print(f'  Technical Analysis present: {ta is not None}')
if ta:
    print('\n  Technical Analysis Details:')
    print(json.dumps(ta, indent=2, default=str)[:800])
else:
    print('\n  Technical Analysis NOT returned in response')
