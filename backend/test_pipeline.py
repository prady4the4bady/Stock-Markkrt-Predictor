"""
Test script to debug the prediction pipeline
"""
import sys
sys.path.insert(0, '.')

print("=== Testing Market Oracle Backend ===\n")

# Test 1: Data fetching
print("[1] Testing Data Manager...")
try:
    from app.data_manager import DataManager
    dm = DataManager()
    df = dm.fetch_stock_data('AAPL', '1y')
    print(f"    ✓ Data fetched: {len(df)} rows")
    print(f"    Columns: {df.columns.tolist()}")
    print(f"    Sample: {df['close'].tail(5).tolist()}")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Technical Indicators
print("\n[2] Testing Technical Indicators...")
try:
    from app.indicators import TechnicalIndicators
    df_ind = TechnicalIndicators.calculate_all(df.copy())
    print(f"    ✓ Indicators calculated: {len(df_ind.columns)} columns")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: XGBoost Model
print("\n[3] Testing XGBoost Model...")
try:
    from app.models.xgboost_model import XGBoostModel
    xgb = XGBoostModel()
    metrics = xgb.train(df, verbose=False)
    print(f"    ✓ XGBoost trained: {metrics}")
    preds = xgb.predict(df, days=7)
    print(f"    ✓ Predictions: {preds}")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Prophet Model
print("\n[4] Testing Prophet Model...")
try:
    from app.models.prophet_model import ProphetModel
    prophet = ProphetModel()
    metrics = prophet.train(df)
    print(f"    ✓ Prophet trained: {metrics}")
    preds = prophet.predict(df, days=7)
    print(f"    ✓ Predictions: {preds}")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 5: LSTM Model
print("\n[5] Testing LSTM Model...")
try:
    from app.models.lstm_model import LSTMModel
    lstm = LSTMModel()
    metrics = lstm.train(df, epochs=5, verbose=0)
    print(f"    ✓ LSTM trained: {metrics}")
    preds = lstm.predict(df, days=7)
    print(f"    ✓ Predictions: {preds}")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Ensemble
print("\n[6] Testing Ensemble Model...")
try:
    from app.models.ensemble import EnsemblePredictor
    ensemble = EnsemblePredictor()
    result = ensemble.train(df)
    print(f"    ✓ Ensemble trained: {result.get('status')}")
    prediction = ensemble.predict(df, days=7)
    print(f"    ✓ Final prediction: ${prediction['predictions'][0]:.2f} -> ${prediction['predictions'][-1]:.2f}")
    print(f"    ✓ Confidence: {prediction['confidence']:.1f}%")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
