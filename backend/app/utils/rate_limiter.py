import threading
import time
from collections import deque

class RateLimiter:
    """Simple token-bucket-like rate limiter using timestamps.
    Allows up to `max_calls` within `period_seconds`.
    `acquire()` will block until a slot is available.
    """
    def __init__(self, max_calls: int, period_seconds: int):
        self.max_calls = max_calls
        self.period = period_seconds
        self.lock = threading.Lock()
        self.calls = deque()

    def acquire(self):
        with self.lock:
            now = time.time()
            # Remove old timestamps
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return
            # Need to wait until earliest call falls out
            wait_time = self.period - (now - self.calls[0])
        time.sleep(wait_time)
        # Try again recursively
        self.acquire()
