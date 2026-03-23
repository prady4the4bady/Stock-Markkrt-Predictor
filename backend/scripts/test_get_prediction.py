import asyncio
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.api.routes import get_prediction

async def run():
    try:
        res = await get_prediction('IBM', days=0.04, is_crypto=False)
        print('Response keys:', res.keys())
    except Exception as e:
        print('Exception type:', e.__class__.__name__)
        print('Exception:', e)

asyncio.run(run())
