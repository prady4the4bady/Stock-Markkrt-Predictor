"""API Endpoint Test Script"""
import requests
import json

BASE = 'http://127.0.0.1:8000/api'

def test_all():
    print('='*60)
    print('API ENDPOINT VERIFICATION')
    print('='*60)
    
    # Test Health
    try:
        r = requests.get(f'{BASE}/health')
        print(f'✅ Health Check: {r.status_code}')
    except Exception as e:
        print(f'❌ Health Check: {e}')
    
    # Test Assets
    try:
        r = requests.get(f'{BASE}/assets')
        data = r.json()
        print(f'✅ Assets: {r.status_code} - {len(data)} assets loaded')
    except Exception as e:
        print(f'❌ Assets: {e}')
    
    # Test Quote
    try:
        r = requests.get(f'{BASE}/quote/AAPL')
        data = r.json()
        print(f'✅ Quote AAPL: ${data.get("price", 0):.2f}')
    except Exception as e:
        print(f'❌ Quote: {e}')
    
    # Test Historical
    try:
        r = requests.get(f'{BASE}/historical/AAPL?period=1mo')
        data = r.json()
        print(f'✅ Historical: {r.status_code} - {len(data)} data points')
    except Exception as e:
        print(f'❌ Historical: {e}')
    
    # Test News
    try:
        r = requests.get(f'{BASE}/news/AAPL')
        data = r.json()
        print(f'✅ News: {r.status_code} - {len(data)} articles')
    except Exception as e:
        print(f'❌ News: {e}')
    
    # Test Prediction
    try:
        r = requests.get(f'{BASE}/predict/AAPL?days=7', timeout=120)
        data = r.json()
        conf = data.get('confidence', 0)
        ind = data.get('individual_predictions', {})
        print(f'✅ Prediction AAPL: {conf:.1f}% confidence')
        print(f'   → LSTM: {ind.get("lstm", {}).get("confidence", 0):.1f}%')
        print(f'   → Prophet: {ind.get("prophet", {}).get("confidence", 0):.1f}%')
        print(f'   → XGBoost: {ind.get("xgboost", {}).get("confidence", 0):.1f}%')
        print(f'   → ARIMA: {ind.get("arima", {}).get("confidence", 0):.1f}%')
        
        # Show predictions
        preds = data.get('predictions', [])
        if preds:
            print(f'   → 7-day forecast: ${preds[0]:.2f} → ${preds[-1]:.2f}')
        
        # Check technical analysis
        ta = data.get('technical_analysis')
        if ta:
            print(f'   → Technical Analysis: ✓ present')
            ts = ta.get('trading_signals', {})
            signals = ts.get('signals', [])
            print(f'   → Trading Signals: {len(signals)} found')
            for i, sig in enumerate(signals):
                if i >= 3:
                    break
                print(f'      • {sig.get("signal", "N/A")}: {sig.get("type", "N/A")}')
            
            # Support/Resistance
            sr = ta.get('support_resistance', {})
            if sr:
                print(f'   → Support/Resistance levels found')
            
            # Trend strength
            trend = ta.get('trend_strength', {})
            if trend:
                print(f'   → Trend: {trend.get("trend_direction", "N/A")} ({trend.get("adx", 0):.1f} ADX)')
            
            # Confidence boost
            boost = ta.get('confidence_boost', 0)
            print(f'   → Confidence boost from TA: {boost:+.1f}%')
        else:
            print(f'   → Technical Analysis: Not available')
    except Exception as e:
        print(f'❌ Prediction: {e}')
    
    # Test Scan Opportunities
    try:
        r = requests.get(f'{BASE}/scan/opportunities?asset_type=stock', timeout=120)
        data = r.json()
        print(f'✅ Scan Opportunities: {len(data)} found')
    except Exception as e:
        print(f'❌ Scan: {e}')
    
    print('='*60)
    print('All tests complete!')

if __name__ == '__main__':
    test_all()
