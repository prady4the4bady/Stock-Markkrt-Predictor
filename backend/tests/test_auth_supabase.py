import sys
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_register_and_persist_user():
    # Check DB connectivity first. If DB is unreachable, skip this test (avoids CI flakiness)
    ping = client.get('/api/internal/db/ping')
    if ping.status_code != 200:
        pytest.xfail('Database appears unreachable; skipping Supabase-backed auth test')

    unique_email = f"test+{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "password123",
        "full_name": "Integration Tester",
        "privacy_consent": True,
        "terms_accepted": True,
        "activity_tracking_consent": False
    }

    # Register
    res = client.post('/api/auth/register', json=payload)
    assert res.status_code == 200, f"Register failed: {res.status_code} {res.text}"
    j = res.json()
    assert 'access_token' in j
    assert j['user']['email'] == unique_email

    # Confirm user present in users table via internal endpoint
    users_res = client.get('/api/internal/users')
    assert users_res.status_code == 200, f"Users query failed: {users_res.status_code} {users_res.text}"
    rows = users_res.json().get('rows', [])
    assert any(r['email'] == unique_email for r in rows), "Registered user not found in DB rows"

    # Test login with form-encoded credentials
    data = {
        "username": unique_email,
        "password": "password123"
    }
    token_res = client.post('/api/auth/token', data=data)
    assert token_res.status_code == 200, f"Token request failed: {token_res.status_code} {token_res.text}"
    tj = token_res.json()
    assert 'access_token' in tj
    assert tj['user']['email'] == unique_email
