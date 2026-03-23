import sys
from pathlib import Path
# ensure project root is on sys.path for script execution
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data.commodities import COMMODITIES
from app.data_manager import data_manager, ExternalRateLimitError

def load_grouped(group_by='country'):
    grouped = {}
    for item in COMMODITIES:
        symbol = item['symbol']
        price = None
        ts = None
        try:
            df = data_manager.fetch_stock_data(symbol, period='5d', interval='1d')
            if not df.empty:
                price = float(df['close'].iloc[-1])
                ts = df['timestamp'].iloc[-1]
        except ExternalRateLimitError as e:
            print('Rate limited for', symbol)
        except Exception as e:
            print('Error fetching', symbol, e)
        enriched = {**item, 'price': price, 'timestamp': ts}
        key = item.get(group_by) or 'Unknown'
        grouped.setdefault(key, []).append(enriched)
    return grouped

if __name__ == '__main__':
    g = load_grouped()
    for country, items in g.items():
        print(country, len(items))
        for it in items[:3]:
            print('  ', it['symbol'], it['price'], it['timestamp'])
