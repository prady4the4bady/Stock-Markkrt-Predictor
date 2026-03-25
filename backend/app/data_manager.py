"""
Market Oracle - Data Manager
Fetches and caches stock/crypto data using free APIs (yfinance)
"""
import sqlite3
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from io import StringIO

import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler

from .config import (
    DATA_DIR, CACHE_EXPIRY_HOURS, STOCK_PERIOD,
    CRYPTO_TIMEFRAME, CRYPTO_LIMIT, DAILY_CACHE_HOURS
)

# Local utilities
from .utils.rate_limiter import RateLimiter

# YFinance: limit to 60 requests per minute
_yf_rate_limiter = RateLimiter(max_calls=60, period_seconds=60)



class ExternalRateLimitError(Exception):
    """Raised when an external data provider (yfinance) rate limits us."""

class DataManager:
    """
    Manages data fetching from free APIs with SQLite caching.
    Supports stocks (yfinance) and crypto (ccxt/Binance public API).

    Features added:
    - Request coalescing: concurrent requests for the same symbol will wait for a single upstream fetch.
    - In-memory metrics counters: track cache_hits, fetch_attempts, external_429s.
    """
    def __init__(self):
        self.db_path = DATA_DIR / "cache.db"
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self._init_database()

        # Coalescing helpers: key -> threading.Event, result
        self._ongoing_fetches = {}
        self._ongoing_lock = threading.Lock()

        # Basic metrics
        self.metrics = {
            'cache_hits': 0,
            'fetch_attempts': 0,
            'external_429s': 0
        }
    

    def _init_database(self):
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                headlines TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_cache_key(self, symbol: str, data_type: str) -> str:
        """Generate unique cache key"""
        key = f"{symbol}_{data_type}_{datetime.now().strftime('%Y-%m-%d')}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Retrieve data from cache if not expired"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data, expires_at FROM price_cache 
            WHERE cache_key = ? AND expires_at > ?
        ''', (cache_key, datetime.now().isoformat()))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            data_json = result[0]
            df = pd.read_json(StringIO(data_json))
            return df
        return None
    
    def _cache_data(self, cache_key: str, df: pd.DataFrame):
        """Store data in cache (default expiry based on CACHE_EXPIRY_HOURS)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=CACHE_EXPIRY_HOURS)
        data_json = df.to_json()
        
        cursor.execute('''
            INSERT OR REPLACE INTO price_cache (cache_key, data, expires_at)
            VALUES (?, ?, ?)
        ''', (cache_key, data_json, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        
    def _cache_data_with_ttl(self, cache_key: str, df: pd.DataFrame, ttl_seconds: int = 60):
        """Store data in cache with a custom TTL in seconds (useful for intraday data)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        data_json = df.to_json()
        
        cursor.execute('''
            INSERT OR REPLACE INTO price_cache (cache_key, data, expires_at)
            VALUES (?, ?, ?)
        ''', (cache_key, data_json, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
    
    def fetch_stock_data(self, ticker: str, period: str = None, interval: str = None) -> pd.DataFrame:
        """
        Fetch stock OHLCV data using yfinance (100% free, no API key)
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL', 'TSLA')
            period: Time period (e.g., '1y', '2y', 'max')
            interval: Data interval (e.g., '1m', '5m', '1h', '1d')
        
        Returns:
            DataFrame with OHLCV data
        """
        period = period or STOCK_PERIOD
        interval = interval or '1d'
        cache_key = self._get_cache_key(ticker, f"stock_{period}_{interval}")
        
        # Check cache first (shorter cache for intraday)
        if interval in ['1m', '5m', '15m', '1h']:
            # Don't cache intraday data
            cached_df = None
        else:
            cached_df = self._get_cached_data(cache_key)
        
        if cached_df is not None:
            print(f"[Cache Hit] Returning cached data for {ticker}")
            return cached_df
        
        print(f"[Fetching] Downloading {ticker} from Yahoo Finance (period={period}, interval={interval})...")
        
        # Enforce global rate limit for yfinance (prevent >60/min)
        _yf_rate_limiter.acquire()
        
        # Robust retry with exponential backoff for yfinance rate limits
        import time
        retries = 5
        backoff = 1
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period=period, interval=interval)
                break
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                # Detect yfinance rate limit errors
                if 'too many requests' in msg or 'rate limit' in msg or e.__class__.__name__ == 'YFRateLimitError':
                    print(f"[RateLimit] yfinance rate limit for {ticker}, attempt {attempt}/{retries}, waiting {backoff}s")
                    if attempt == retries:
                        # Exhausted retries, surface a clear error
                        raise ExternalRateLimitError(f"YFinance rate limit for {ticker}: {e}")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    print(f"[Error] Failed to fetch {ticker}: {e}")
                    raise
        else:
            # Retries exhausted
            raise ExternalRateLimitError(f"Failed to fetch data for {ticker} after {retries} attempts. Last error: {last_err}")
        
        if df.empty:
            raise ValueError(f"No data found for ticker: {ticker}")
        
        # Clean and prepare data
        df = df.reset_index()
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # Handle both 'date' and 'datetime' column names
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'timestamp'})
        elif 'date' in df.columns:
            df = df.rename(columns={'date': 'timestamp'})
        
        # Ensure required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0
        
        df = df[required_cols]
        
        # Format timestamp based on interval
        if interval in ['1m', '5m', '15m', '1h']:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')
        
        # Clean NaN values to avoid JSON serialization issues
        df = df.ffill().bfill().fillna(0)

        # Replace infinity values
        df = df.replace([np.inf, -np.inf], 0)
        
        # Cache the data (only for daily+)
        if interval not in ['1m', '5m', '15m', '1h']:
            # Use a longer TTL for daily data (configurable via DAILY_CACHE_HOURS)
            try:
                ttl_hours = int(DAILY_CACHE_HOURS)
            except Exception:
                ttl_hours = 24
            # Use _cache_data_with_ttl by converting hours to seconds
            self._cache_data_with_ttl(cache_key, df, ttl_seconds=ttl_hours * 3600)
        
        return df
    
    @staticmethod
    def _crypto_symbol_to_yf(symbol: str) -> str:
        """Convert 'BTC/USDT' or 'BTC-USDT' → 'BTC-USD' for yfinance."""
        base = symbol.replace('/', '-').replace('_', '-').split('-')[0]
        return f"{base}-USD"

    def fetch_crypto_data(self, symbol: str, timeframe: str = None, limit: int = None, period: str = None, interval: str = None) -> pd.DataFrame:
        """
        Fetch crypto OHLCV data via yfinance (BTC-USD format).
        Works from any server location — no geographic restrictions.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT', 'ETH/USDT', 'BTC-USD')
            timeframe: Candle timeframe (e.g., '1d', '1h') — mapped to yfinance interval
            limit: Number of candles (used to derive period when no explicit period given)
            period: yfinance period string ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y')
            interval: Alias for timeframe

        Returns:
            DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)
        """
        # Normalise timeframe
        tf = interval or timeframe or CRYPTO_TIMEFRAME
        # Map CCXT-style timeframes to yfinance intervals
        tf_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '60m', '4h': '60m', '1d': '1d', '1w': '1wk', '1M': '1mo',
        }
        yf_interval = tf_map.get(tf, '1d')
        is_intraday = yf_interval in ('1m', '5m', '15m', '30m', '60m')

        # Derive yfinance period from limit or explicit period
        if not period:
            lim = limit or CRYPTO_LIMIT
            if yf_interval == '1d':
                days = lim
            elif yf_interval in ('1m',):
                days = max(1, lim // 1440)
            elif yf_interval in ('5m', '15m', '30m'):
                days = max(1, lim // (288 if yf_interval == '5m' else 96 if yf_interval == '15m' else 48))
            elif yf_interval == '60m':
                days = max(1, lim // 24)
            else:
                days = lim
            # yfinance max intraday history: 60d for 1h, 7d for <1h
            if yf_interval == '60m':
                days = min(days, 60)
            elif is_intraday:
                days = min(days, 7)
            period = f"{days}d"

        yf_symbol = self._crypto_symbol_to_yf(symbol)
        base_cache_key = self._get_cache_key(yf_symbol, f"crypto_{yf_interval}_{period}")
        cache_key_to_use = base_cache_key

        if is_intraday:
            minute_key = f"{base_cache_key}_{datetime.now().strftime('%Y%m%d%H%M')}"
            cache_key_to_use = minute_key
            cached_df = self._get_cached_data(minute_key)
            if cached_df is not None:
                print(f"[Cache Hit] Returning intraday cached data for {symbol}")
                self.metrics['cache_hits'] += 1
                return cached_df
        else:
            cached_df = self._get_cached_data(base_cache_key)
            if cached_df is not None:
                print(f"[Cache Hit] Returning cached data for {symbol}")
                self.metrics['cache_hits'] += 1
                return cached_df

        # Coalescing: wait if another thread is already fetching this key
        with self._ongoing_lock:
            if cache_key_to_use in self._ongoing_fetches:
                event, _ = self._ongoing_fetches[cache_key_to_use]
                print(f"[Coalesce] Waiting for ongoing fetch of {symbol}")
                event.wait(timeout=30)
                cached_after = self._get_cached_data(cache_key_to_use)
                if cached_after is not None:
                    self.metrics['cache_hits'] += 1
                    return cached_after
            else:
                event = threading.Event()
                self._ongoing_fetches[cache_key_to_use] = (event, None)

        print(f"[Fetching] Downloading {symbol} ({yf_symbol}) from Yahoo Finance (period={period}, interval={yf_interval})...")

        import time
        retries = 5
        backoff = 1
        df = None
        for attempt in range(1, retries + 1):
            try:
                with _yf_rate_limiter:
                    ticker = yf.Ticker(yf_symbol)
                    raw = ticker.history(period=period, interval=yf_interval, auto_adjust=True)
                if raw.empty:
                    raise ValueError(f"yfinance returned empty data for {yf_symbol}")
                df = raw.reset_index()
                break
            except Exception as e:
                msg = str(e).lower()
                if 'too many requests' in msg or '429' in msg or 'rate limit' in msg:
                    print(f"[RateLimit] yfinance rate limit for {yf_symbol}, attempt {attempt}/{retries}, waiting {backoff}s")
                    if attempt == retries:
                        raise ExternalRateLimitError(f"yfinance rate limit for {yf_symbol}: {e}")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    print(f"[Error] Unexpected error fetching {symbol}: {e}")
                    raise

        try:
            # Normalise column names from yfinance
            df.columns = [c.lower() for c in df.columns]
            date_col = 'datetime' if 'datetime' in df.columns else 'date'
            df = df.rename(columns={date_col: 'timestamp'})
            # Keep only the columns we need
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col not in df.columns:
                    df[col] = 0.0
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()

            # Format timestamp
            if is_intraday:
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')

            # Clean NaN values
            df = df.ffill().bfill().fillna(0)

            # Cache the data
            if is_intraday:
                # short TTL to avoid repeated hits
                self._cache_data_with_ttl(minute_key, df, ttl_seconds=60)
            else:
                # Use daily TTL configured
                try:
                    ttl_hours = int(DAILY_CACHE_HOURS)
                except Exception:
                    ttl_hours = 24
                self._cache_data_with_ttl(base_cache_key, df, ttl_seconds=ttl_hours * 3600)

            return df
        finally:
            # Clear coalescing event so waiting threads can proceed
            with self._ongoing_lock:
                if cache_key_to_use in self._ongoing_fetches:
                    ev, _ = self._ongoing_fetches[cache_key_to_use]
                    self._ongoing_fetches[cache_key_to_use] = (ev, df)
                    ev.set()
    
    def normalize_data(self, df: pd.DataFrame, column: str = 'close') -> Tuple[np.ndarray, MinMaxScaler]:
        """
        Normalize data using MinMaxScaler for ML models
        
        Args:
            df: DataFrame with price data
            column: Column to normalize
        
        Returns:
            Tuple of (normalized array, fitted scaler for inverse transform)
        """
        values = df[column].values.reshape(-1, 1)
        scaler = MinMaxScaler(feature_range=(0, 1))
        normalized = scaler.fit_transform(values)
        return normalized, scaler
    
    def prepare_sequences(self, data: np.ndarray, sequence_length: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare sequences for LSTM training
        
        Args:
            data: Normalized price data
            sequence_length: Number of time steps in each sequence
        
        Returns:
            Tuple of (X sequences, y targets)
        """
        X, y = [], []
        
        for i in range(sequence_length, len(data)):
            X.append(data[i - sequence_length:i, 0])
            y.append(data[i, 0])
        
        return np.array(X), np.array(y)
    
    def get_asset_info(self, symbol: str, is_crypto: bool = False) -> Dict:
        """Get basic asset information"""
        if is_crypto:
            return {
                "symbol": symbol,
                "type": "cryptocurrency",
                "exchange": "Binance",
                "currency": "USDT"
            }
        else:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                return {
                    "symbol": symbol,
                    "type": "stock",
                    "name": info.get('longName', symbol),
                    "sector": info.get('sector', 'Unknown'),
                    "currency": info.get('currency', 'USD'),
                    "market_cap": info.get('marketCap', 0)
                }
            except:
                return {"symbol": symbol, "type": "stock"}
    
    def clear_cache(self, symbol: str = None):
        """Clear cache for a specific symbol or all"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("DELETE FROM price_cache WHERE cache_key LIKE ?", (f"%{symbol}%",))
        else:
            cursor.execute("DELETE FROM price_cache")
            cursor.execute("DELETE FROM news_cache")
        
        conn.commit()
        conn.close()
        print(f"[Cache] Cleared cache for {symbol or 'all symbols'}")


# Singleton instance
data_manager = DataManager()
