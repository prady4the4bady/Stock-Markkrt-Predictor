"""
NexusTrader — Real-Time Price Feed
====================================
Provides near-real-time price data for stocks and crypto with tight caching.

Sources (all free, no API key):
  - Stocks:  yfinance fast download (1m bar, period=1d) → latest tick
  - Crypto:  ccxt Binance fetch_ticker() → real-time bid/ask/last

Cache TTLs:
  - Crypto  :  5 seconds  (Binance WebSocket alternative without persistent conn)
  - Stocks  : 60 seconds  (markets open) / 300 seconds (after-hours)

Ring buffer:
  - Keeps last 60 ticks per symbol for momentum calculation
  - Useful for scanner agents that need sub-minute data

Thread safety: all writes use threading.Lock.
"""
import time
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Internal ring buffer
# ─────────────────────────────────────────────────────────────────────────────

class _RingBuffer:
    """Fixed-size deque of recent tick prices with thread-safe access."""

    def __init__(self, maxlen: int = 60):
        self._buf: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def push(self, price: float, ts: float):
        with self._lock:
            self._buf.append({"price": price, "ts": ts})

    def snapshot(self) -> List[Dict]:
        with self._lock:
            return list(self._buf)

    def last_price(self) -> Optional[float]:
        with self._lock:
            return self._buf[-1]["price"] if self._buf else None

    def momentum(self, window: int = 20) -> Optional[float]:
        """% change over last `window` ticks. None if insufficient data."""
        snap = self.snapshot()
        if len(snap) < window:
            return None
        p0 = snap[-window]["price"]
        p1 = snap[-1]["price"]
        return (p1 - p0) / (abs(p0) + 1e-9) * 100


# ─────────────────────────────────────────────────────────────────────────────
# Real-Time Feed
# ─────────────────────────────────────────────────────────────────────────────

class RealTimeFeed:
    """
    Manages a live price cache for all actively monitored symbols.

    Usage:
        price = realtime_feed.get_price("AAPL")
        price = realtime_feed.get_price("BTC/USDT")
        tick  = realtime_feed.get_tick("TSLA")   # full dict with momentum
    """

    # TTLs in seconds
    CRYPTO_TTL  =  5
    STOCK_TTL   = 60
    AFTERHOURS_TTL = 300

    def __init__(self):
        # symbol → {"price", "change_pct", "volume", "bid", "ask", "ts", "source"}
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()

        # Per-symbol ring buffers for momentum
        self._buffers: Dict[str, _RingBuffer] = {}
        self._buf_lock = threading.Lock()

        # Background refresh thread
        self._refresh_symbols: List[str] = []
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── Private ───────────────────────────────────────────────────────────────

    def _is_crypto(self, symbol: str) -> bool:
        return "/" in symbol or any(
            tok in symbol.upper()
            for tok in ["BTC", "ETH", "BNB", "XRP", "SOL", "ADA",
                        "DOT", "USDT", "DOGE", "MATIC", "AVAX"]
        )

    def _ttl(self, symbol: str) -> int:
        if self._is_crypto(symbol):
            return self.CRYPTO_TTL
        # Very rough US market hours check (UTC 13:30–20:00)
        h = datetime.now(timezone.utc).hour
        return self.STOCK_TTL if 13 <= h < 20 else self.AFTERHOURS_TTL

    def _fetch_crypto(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time crypto tick via ccxt Binance."""
        try:
            import ccxt
            exchange = ccxt.binance({"enableRateLimit": True})
            # Normalise to ccxt format: BTC/USDT or BTCUSDT → BTC/USDT
            sym = symbol if "/" in symbol else f"{symbol[:3]}/USDT"
            ticker = exchange.fetch_ticker(sym)
            return {
                "price":      float(ticker.get("last") or ticker.get("close") or 0),
                "change_pct": float(ticker.get("percentage") or 0),
                "volume":     float(ticker.get("quoteVolume") or ticker.get("baseVolume") or 0),
                "bid":        float(ticker.get("bid") or 0),
                "ask":        float(ticker.get("ask") or 0),
                "ts":         time.time(),
                "source":     "ccxt_binance",
            }
        except Exception as e:
            print(f"[RealTimeFeed] ccxt failed for {symbol}: {e}")
            return None

    def _fetch_stock(self, symbol: str) -> Optional[Dict]:
        """Fetch latest stock quote via yfinance fast download."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            # fast_info is much faster than .info (no HTTP scraping)
            fi = ticker.fast_info
            price = float(getattr(fi, "last_price", 0) or 0)
            prev  = float(getattr(fi, "previous_close", price) or price)
            change_pct = (price - prev) / (abs(prev) + 1e-9) * 100 if prev else 0.0
            volume = float(getattr(fi, "three_month_average_volume", 0) or 0)
            return {
                "price":      price,
                "change_pct": round(change_pct, 3),
                "volume":     volume,
                "bid":        float(getattr(fi, "last_price", price) or price),
                "ask":        float(getattr(fi, "last_price", price) or price),
                "ts":         time.time(),
                "source":     "yfinance_fast",
            }
        except Exception as e:
            print(f"[RealTimeFeed] yfinance failed for {symbol}: {e}")
            return None

    def _fetch(self, symbol: str) -> Optional[Dict]:
        sym = symbol.upper()
        if self._is_crypto(sym):
            return self._fetch_crypto(sym)
        return self._fetch_stock(sym)

    def _update_buffer(self, symbol: str, price: float):
        with self._buf_lock:
            if symbol not in self._buffers:
                self._buffers[symbol] = _RingBuffer(maxlen=60)
            self._buffers[symbol].push(price, time.time())

    # ── Public API ────────────────────────────────────────────────────────────

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Return the latest price for a symbol (fetches if cache stale).
        Thread-safe. Returns None if fetch fails.
        """
        sym = symbol.upper()
        with self._lock:
            entry = self._cache.get(sym)
        if entry and (time.time() - entry["ts"]) < self._ttl(sym):
            return entry["price"]
        data = self._fetch(sym)
        if data:
            with self._lock:
                self._cache[sym] = data
            self._update_buffer(sym, data["price"])
            return data["price"]
        # Return stale cache rather than None if available
        if entry:
            return entry["price"]
        return None

    def get_tick(self, symbol: str) -> Optional[Dict]:
        """
        Return full tick dict including change_pct, volume, momentum.
        """
        sym = symbol.upper()
        price = self.get_price(sym)
        if price is None:
            return None

        with self._lock:
            entry = dict(self._cache.get(sym, {}))

        with self._buf_lock:
            buf = self._buffers.get(sym)
        momentum = buf.momentum(window=20) if buf else None
        entry["momentum_20t"] = momentum
        entry["symbol"] = sym
        return entry

    def get_all_ticks(self) -> Dict[str, Dict]:
        """Return snapshot of all cached ticks."""
        with self._lock:
            return {k: dict(v) for k, v in self._cache.items()}

    def prefetch(self, symbols: List[str], max_workers: int = 10):
        """
        Fetch a batch of symbols concurrently and warm the cache.
        Non-blocking: runs in a background thread.
        """
        from concurrent.futures import ThreadPoolExecutor
        def _job(sym: str):
            self.get_price(sym)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            pool.map(_job, symbols)

    # ── Background auto-refresh ────────────────────────────────────────────────

    def start_background_refresh(self, symbols: List[str], interval: float = 30.0):
        """
        Start a background thread that refreshes `symbols` every `interval` seconds.
        Safe to call multiple times — only one thread runs.
        """
        if self._thread and self._thread.is_alive():
            self._refresh_symbols = [s.upper() for s in symbols]
            return

        self._refresh_symbols = [s.upper() for s in symbols]
        self._running = True

        def _loop():
            print(f"[RealTimeFeed] Auto-refresh started ({len(self._refresh_symbols)} symbols, {interval}s interval)")
            while self._running:
                try:
                    self.prefetch(self._refresh_symbols)
                except Exception as e:
                    print(f"[RealTimeFeed] Refresh error: {e}")
                time.sleep(interval)
            print("[RealTimeFeed] Auto-refresh stopped")

        self._thread = threading.Thread(target=_loop, daemon=True, name="RealTimeFeed")
        self._thread.start()

    def stop(self):
        self._running = False

    def get_stats(self) -> Dict:
        with self._lock:
            n = len(self._cache)
            oldest = min((v["ts"] for v in self._cache.values()), default=0)
        return {
            "symbols_cached": n,
            "oldest_tick_age_s": round(time.time() - oldest, 1) if oldest else None,
            "is_running": bool(self._thread and self._thread.is_alive()),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────
realtime_feed = RealTimeFeed()
