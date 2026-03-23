import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.api.routes import get_available_assets
import asyncio

async def run():
    res = await get_available_assets()
    print('Stocks loaded:', len(res['stocks']))
    print('Crypto loaded:', len(res['crypto']))
    print('Forex loaded:', len(res['forex']))
    print('Indices loaded:', len(res['indices']))
    print('Commodities loaded:', len(res['commodities']))

asyncio.run(run())
