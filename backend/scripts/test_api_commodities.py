import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
res = client.get('/api/commodities')
print('Status:', res.status_code)
if res.status_code == 200:
    j = res.json()
    print('Groups:', list(j.keys())[:5])
    for country, items in j.items():
        print(country, len(items))
        print(items[0])
        break
else:
    print('Error:', res.text)
