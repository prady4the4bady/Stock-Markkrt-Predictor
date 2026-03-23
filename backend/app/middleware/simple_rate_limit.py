from fastapi import Request, HTTPException
from time import time
from collections import deque
from typing import Dict

# Simple per-IP sliding window limiter
ip_calls: Dict[str, deque] = {}

def rate_limit(max_calls: int = 10, period_seconds: int = 60):
    def dependency(request: Request):
        ip = request.client.host if request.client else 'unknown'
        now = time()
        calls = ip_calls.setdefault(ip, deque())
        # Remove old
        while calls and now - calls[0] > period_seconds:
            calls.popleft()
        if len(calls) >= max_calls:
            raise HTTPException(status_code=429, detail='Too many requests from your IP, slow down.')
        calls.append(now)
    return dependency
