import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

client = TestClient(app)


def _handle_response(res):
    # If rate-limited by external provider, xfail the test to avoid CI flakiness
    if res.status_code == 429:
        pytest.xfail('External provider rate-limited the request (429)')
    assert res.status_code == 200, f"Unexpected status {res.status_code}: {res.text[:400]}"
    return res.json()


@pytest.mark.integration
def test_crypto_prediction_short_term_by_pair():
    """Crypto prediction using pair format (BTC/USDT) — short term quick prediction"""
    res = client.get('/api/predict/BTC/USDT?days=0.04')  # ~1 hour quick prediction
    j = _handle_response(res)
    assert 'prediction_type' in j
    assert j['prediction_type'].startswith('quick')
    assert isinstance(j.get('confidence'), (int, float))
    assert j.get('analysis', {}).get('note') == 'trade on your own risk'


@pytest.mark.integration
def test_crypto_prediction_short_term_by_symbol_auto_detection():
    """Crypto prediction when passing BTCUSDT (no slash) should auto-detect as crypto"""
    res = client.get('/api/predict/BTCUSDT?days=0.04')
    j = _handle_response(res)
    assert j['prediction_type'].startswith('quick')
    assert j.get('analysis', {}).get('note') == 'trade on your own risk'


@pytest.mark.integration
def test_stock_prediction_short_term():
    """Stock prediction uses quick_predict for short-term requests"""
    res = client.get('/api/predict/AAPL?days=0.04')
    j = _handle_response(res)
    assert j['prediction_type'].startswith('quick')
    assert j.get('analysis', {}).get('note') == 'trade on your own risk'
