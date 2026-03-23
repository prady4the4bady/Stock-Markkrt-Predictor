import yfinance as yf
import json

try:
    ticker = yf.Ticker("AAPL")
    news = ticker.news
    if news:
        item = news[0]
        print(f"Type: {type(item)}")
        if isinstance(item, dict):
            print(f"Keys: {list(item.keys())}")
            if 'content' in item:
                print(f"Content Type: {type(item['content'])}")
                print(f"Content: {item['content']}")
            else:
                print(f"Item: {item}")
    else:
        print("No news found")
except Exception as e:
    print(f"Error: {e}")
