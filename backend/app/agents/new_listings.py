"""
NexusTrader — New Listings Auto-Discovery Service
Automatically tracks new crypto listings on Binance and new stock IPOs.

Runs as a background daemon:
  - Crypto  : refreshes every 6 h   (Binance exchangeInfo)
  - Stocks  : refreshes every 24 h  (NASDAQ IPO API + Yahoo Finance)

Data is persisted in SQLite and served via REST so the frontend can show
a "New Listings" feed sorted by date, exchange, and asset class.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests  # type: ignore[import-untyped]

# ── Storage path ──────────────────────────────────────────────────────────────
_DB_DIR = Path(__file__).parent.parent.parent.parent / "data"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DB_DIR / "new_listings.db"

# ── Known crypto pairs already in DEFAULT_CRYPTO (loaded lazily) ──────────────
_known_crypto: Optional[set] = None
_known_lock = threading.Lock()


def _get_known_crypto() -> set:
    global _known_crypto
    with _known_lock:
        if _known_crypto is None:
            try:
                from ..config import DEFAULT_CRYPTO
                # Normalise to base symbol, e.g. "BTC/USDT" → "BTC"
                _known_crypto = {
                    pair.split("/")[0].upper()
                    for pair in DEFAULT_CRYPTO
                    if "/" in pair
                }
            except Exception:
                _known_crypto = set()
        return _known_crypto


# ── Database helpers ──────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crypto_listings (
                symbol       TEXT PRIMARY KEY,
                base_asset   TEXT NOT NULL,
                quote_asset  TEXT NOT NULL,
                exchange     TEXT NOT NULL DEFAULT 'Binance',
                status       TEXT,
                first_seen   TEXT NOT NULL,
                is_new       INTEGER NOT NULL DEFAULT 1,
                price_usdt   REAL,
                volume_24h   REAL,
                change_24h   REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_ipo_listings (
                symbol          TEXT PRIMARY KEY,
                company_name    TEXT,
                exchange        TEXT,
                ipo_date        TEXT,
                offer_price     REAL,
                shares_offered  TEXT,
                first_seen      TEXT NOT NULL,
                is_new          INTEGER NOT NULL DEFAULT 1,
                status          TEXT DEFAULT 'upcoming',
                market_cap      TEXT,
                sector          TEXT
            )
        """)
        conn.commit()


# ── Crypto: Binance exchangeInfo ──────────────────────────────────────────────

_BINANCE_API = "https://api.binance.com/api/v3/exchangeInfo"
_BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"

_QUOTE_ASSETS = {"USDT", "BTC", "ETH", "BNB", "BUSD", "USDC"}


def _fetch_binance_symbols() -> List[Dict]:
    """Return all TRADING symbols from Binance with their quote/base assets."""
    try:
        resp = requests.get(_BINANCE_API, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        symbols = []
        for s in data.get("symbols", []):
            if s.get("status") != "TRADING":
                continue
            if s.get("quoteAsset") not in _QUOTE_ASSETS:
                continue
            symbols.append({
                "symbol":      s["symbol"],
                "base_asset":  s["baseAsset"],
                "quote_asset": s["quoteAsset"],
                "status":      s["status"],
            })
        return symbols
    except Exception as e:
        print(f"[NewListings] Binance fetch error: {e}")
        return []


def _fetch_binance_tickers() -> Dict[str, Dict]:
    """Fetch 24h ticker data keyed by symbol."""
    try:
        resp = requests.get(_BINANCE_TICKER, timeout=30)
        resp.raise_for_status()
        return {t["symbol"]: t for t in resp.json()}
    except Exception:
        return {}


def _sync_crypto_listings():
    """Compare Binance symbols against DB; insert genuinely new ones."""
    print("[NewListings] Syncing crypto listings from Binance …")
    symbols = _fetch_binance_symbols()
    if not symbols:
        return

    tickers = _fetch_binance_tickers()
    known = _get_known_crypto()
    now = datetime.utcnow().isoformat()

    # Only surface USDT pairs for the "new listings" feed
    usdt_symbols = [s for s in symbols if s["quote_asset"] == "USDT"]

    with _get_conn() as conn:
        existing = {
            row["symbol"]
            for row in conn.execute("SELECT symbol FROM crypto_listings").fetchall()
        }

        new_count = 0
        for s in usdt_symbols:
            sym = s["symbol"]
            if sym in existing:
                continue  # already recorded

            base = s["base_asset"].upper()
            ticker = tickers.get(sym, {})
            price  = float(ticker.get("lastPrice", 0) or 0)
            vol    = float(ticker.get("quoteVolume", 0) or 0)
            chg    = float(ticker.get("priceChangePercent", 0) or 0)
            is_new = 0 if base in known else 1   # 1 = not in our existing universe

            conn.execute("""
                INSERT OR IGNORE INTO crypto_listings
                    (symbol, base_asset, quote_asset, exchange, status,
                     first_seen, is_new, price_usdt, volume_24h, change_24h)
                VALUES (?, ?, ?, 'Binance', ?, ?, ?, ?, ?, ?)
            """, (sym, base, s["quote_asset"], s["status"], now,
                  is_new, price, vol, chg))
            new_count += 1

        # Refresh price/volume for existing entries (rolling window)
        for sym, ticker in tickers.items():
            if sym not in existing:
                continue
            price = float(ticker.get("lastPrice", 0) or 0)
            vol   = float(ticker.get("quoteVolume", 0) or 0)
            chg   = float(ticker.get("priceChangePercent", 0) or 0)
            conn.execute("""
                UPDATE crypto_listings
                SET price_usdt=?, volume_24h=?, change_24h=?
                WHERE symbol=?
            """, (price, vol, chg, sym))

        conn.commit()
        print(f"[NewListings] Crypto sync done — {new_count} new pairs recorded "
              f"({len(usdt_symbols)} USDT pairs total)")


# ── Stocks: NASDAQ IPO Calendar ───────────────────────────────────────────────

_NASDAQ_IPO_API = (
    "https://api.nasdaq.com/api/ipo/upcoming?"
    "assetClass=stocks&offset=0&limit=50&type=upcoming&sortColumn=priceDateMs"
    "&sortOrder=desc"
)
_NASDAQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nasdaq.com/",
}

_YAHOO_IPO_URL = (
    "https://finance.yahoo.com/calendar/ipo"
)


def _fetch_nasdaq_ipos() -> List[Dict]:
    """Fetch upcoming + recent IPOs from NASDAQ free API."""
    try:
        resp = requests.get(_NASDAQ_IPO_API, headers=_NASDAQ_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        rows_data = (
            data.get("data", {})
                .get("upcomingData", {})
                .get("rows", [])
        )
        results = []
        for row in rows_data:
            results.append({
                "symbol":         (row.get("proposedTickerSymbol") or "").strip().upper(),
                "company_name":   row.get("companyName", ""),
                "exchange":       row.get("proposedExchange", ""),
                "ipo_date":       row.get("expectedPriceDate", ""),
                "offer_price":    _parse_price(row.get("proposedSharePrice", "")),
                "shares_offered": row.get("sharesOffered", ""),
                "status":         "upcoming",
                "sector":         row.get("primaryMarket", ""),
            })
        return [r for r in results if r["symbol"]]
    except Exception as e:
        print(f"[NewListings] NASDAQ IPO fetch error: {e}")
        return []


def _parse_price(raw: str) -> Optional[float]:
    """Extract a float from a string like '$18.00 - $20.00' or '$15.00'."""
    if not raw:
        return None
    try:
        clean = raw.replace("$", "").replace(",", "").strip()
        if "-" in clean:
            parts = clean.split("-")
            vals = [float(p.strip()) for p in parts if p.strip()]
            return round(sum(vals) / len(vals), 2) if vals else None
        return float(clean)
    except Exception:
        return None


def _fetch_recent_ipos_yfinance() -> List[Dict]:
    """
    Supplement with yfinance-scraped recent IPOs (last 90 days).
    Returns a minimal list — yfinance doesn't expose a structured IPO calendar,
    so we use a curated list of recent notable IPOs as a fallback seed.
    """
    # yfinance has no direct IPO calendar endpoint.
    # We derive "recent" by checking symbols listed in the last 90 days
    # from a community-maintained GitHub JSON (updated weekly).
    try:
        url = (
            "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/"
            "main/nyse/nyse_full_tickers.json"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return []
        tickers = resp.json()
        # This file has {symbol: name} — no IPO dates. Return empty; NASDAQ is primary.
        return []
    except Exception:
        return []


def _sync_stock_listings():
    """Fetch IPOs and insert new ones into DB."""
    print("[NewListings] Syncing stock IPO listings …")
    ipos = _fetch_nasdaq_ipos()
    ipos += _fetch_recent_ipos_yfinance()

    if not ipos:
        print("[NewListings] No IPO data fetched (APIs may be throttled)")
        return

    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        existing = {
            row["symbol"]
            for row in conn.execute("SELECT symbol FROM stock_ipo_listings").fetchall()
        }
        new_count = 0
        for ipo in ipos:
            sym = ipo["symbol"]
            if not sym or sym in existing:
                continue
            conn.execute("""
                INSERT OR IGNORE INTO stock_ipo_listings
                    (symbol, company_name, exchange, ipo_date, offer_price,
                     shares_offered, first_seen, is_new, status, sector)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                sym, ipo.get("company_name"), ipo.get("exchange"),
                ipo.get("ipo_date"), ipo.get("offer_price"),
                ipo.get("shares_offered"), now,
                ipo.get("status", "upcoming"), ipo.get("sector"),
            ))
            new_count += 1

        conn.commit()
        print(f"[NewListings] Stock IPO sync done — {new_count} new listings recorded")


# ── Public query API ──────────────────────────────────────────────────────────

def get_new_crypto(
    limit: int = 100,
    only_new: bool = False,
    min_volume: float = 0.0,
) -> List[Dict]:
    """
    Return crypto listings sorted by volume (descending).

    Parameters
    ----------
    limit       : max rows to return
    only_new    : if True, only return coins not in our DEFAULT_CRYPTO universe
    min_volume  : filter out coins with 24h volume below this threshold (USDT)
    """
    with _get_conn() as conn:
        query = "SELECT * FROM crypto_listings"
        conditions: List[str] = []
        params: List = []
        if only_new:
            conditions.append("is_new = 1")
        if min_volume > 0:
            conditions.append("volume_24h >= ?")
            params.append(min_volume)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY volume_24h DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_new_ipos(limit: int = 50, status: Optional[str] = None) -> List[Dict]:
    """
    Return stock IPO listings sorted by IPO date (newest first).

    Parameters
    ----------
    limit  : max rows
    status : filter by status — 'upcoming', 'priced', 'withdrawn', or None for all
    """
    with _get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM stock_ipo_listings WHERE status=? "
                "ORDER BY ipo_date DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stock_ipo_listings ORDER BY ipo_date DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_all_new(limit: int = 200) -> Dict:
    """Combined snapshot: newest crypto + stock IPOs."""
    crypto = get_new_crypto(limit=limit, only_new=True, min_volume=100_000)
    stocks = get_new_ipos(limit=50)
    return {
        "crypto": crypto,
        "stocks": stocks,
        "total_crypto": len(crypto),
        "total_stocks": len(stocks),
        "updated_at": datetime.utcnow().isoformat(),
    }


def get_summary() -> Dict:
    """Quick stats for the summary bar."""
    with _get_conn() as conn:
        total_crypto = conn.execute(
            "SELECT COUNT(*) FROM crypto_listings"
        ).fetchone()[0]
        new_crypto   = conn.execute(
            "SELECT COUNT(*) FROM crypto_listings WHERE is_new=1"
        ).fetchone()[0]
        total_ipos   = conn.execute(
            "SELECT COUNT(*) FROM stock_ipo_listings"
        ).fetchone()[0]
        upcoming_ipos = conn.execute(
            "SELECT COUNT(*) FROM stock_ipo_listings WHERE status='upcoming'"
        ).fetchone()[0]
        return {
            "total_crypto_tracked": total_crypto,
            "new_crypto_coins":     new_crypto,
            "total_ipos":           total_ipos,
            "upcoming_ipos":        upcoming_ipos,
        }


# ── Background daemon ─────────────────────────────────────────────────────────

class NewListingsTracker:
    """
    Singleton background daemon that keeps the listings DB current.

    Crypto is refreshed every `crypto_interval_h` hours.
    Stocks are refreshed every `stock_interval_h` hours.
    """

    CRYPTO_INTERVAL_H = 6
    STOCK_INTERVAL_H  = 24

    def __init__(self):
        _init_db()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def _loop(self):
        print("[NewListings] Daemon thread started")
        crypto_due = datetime.utcnow()
        stock_due  = datetime.utcnow()

        while self._running:
            now = datetime.utcnow()
            try:
                if now >= crypto_due:
                    _sync_crypto_listings()
                    crypto_due = now + timedelta(hours=self.CRYPTO_INTERVAL_H)

                if now >= stock_due:
                    _sync_stock_listings()
                    stock_due = now + timedelta(hours=self.STOCK_INTERVAL_H)
            except Exception:
                traceback.print_exc()

            # Sleep in 60-second ticks so stop() is responsive
            for _ in range(60):
                if not self._running:
                    break
                time.sleep(1)

        print("[NewListings] Daemon thread stopped")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="NewListings"
        )
        self._thread.start()
        print("[NewListings] Background tracker started "
              f"(crypto every {self.CRYPTO_INTERVAL_H}h, "
              f"stocks every {self.STOCK_INTERVAL_H}h)")

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def force_refresh(self, asset_class: str = "all"):
        """Trigger an immediate out-of-band refresh (runs in caller's thread)."""
        if asset_class in ("all", "crypto"):
            _sync_crypto_listings()
        if asset_class in ("all", "stocks"):
            _sync_stock_listings()


# ── Singleton ─────────────────────────────────────────────────────────────────
new_listings_tracker = NewListingsTracker()
