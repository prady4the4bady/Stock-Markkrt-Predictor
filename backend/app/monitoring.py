"""Simple in-memory metrics and alerting stub.
Expose increment functions to count 429s and provide a /api/metrics endpoint.
"""
from threading import Lock

_metrics = {
    'external_429s': 0,
    'cache_hits': 0,
    'fetch_attempts': 0
}
_metrics_lock = Lock()


def incr(key: str, amount: int = 1):
    with _metrics_lock:
        if key not in _metrics:
            _metrics[key] = 0
        _metrics[key] += amount


def get_metrics():
    with _metrics_lock:
        return dict(_metrics)
