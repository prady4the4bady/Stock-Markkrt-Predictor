import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.data_manager import data_manager
from app.api.routes import quick_predict

try:
    df = data_manager.fetch_stock_data('IBM')
    print('Rows fetched:', len(df))
    res = quick_predict(df, 1, is_crypto=False)
    print('Quick predict result keys:', list(res.keys()))
    print('Current price:', res['current_price'])
except Exception as e:
    import traceback
    print('Error:', e)
    traceback.print_exc()
