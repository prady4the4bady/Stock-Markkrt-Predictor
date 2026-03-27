"""
NexusTrader — Multi-Asset New Listings & Discovery Service
==========================================================
Tracks 6 asset classes for the "New Listings" feed:
  1. Crypto      — Binance new USDT pairs + CoinGecko trending/new coins
  2. Stocks      — NASDAQ IPO calendar (upcoming + recent)
  3. ETFs        — Recently launched ETFs (BlackRock/Vanguard/State Street feeds)
  4. Bonds/Rates — US Treasury yields + key FRED macro rates
  5. Indices     — 30 major global indices with live prices
  6. Forex       — 30 major/minor currency pairs with live rates

Background daemon refresh intervals:
  Crypto    — 6 h   Stocks    — 24 h   ETFs      — 24 h
  Bonds     — 1 h   Indices   — 15 min Forex     — 15 min
"""

from __future__ import annotations

import sqlite3
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

# ── Storage ───────────────────────────────────────────────────────────────────
_DB_DIR  = Path(__file__).parent.parent.parent.parent / "data"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DB_DIR / "new_listings.db"

# ── Known crypto in DEFAULT_CRYPTO ────────────────────────────────────────────
_known_crypto: Optional[set] = None
_known_lock   = threading.Lock()

def _get_known_crypto() -> set:
    global _known_crypto
    with _known_lock:
        if _known_crypto is None:
            try:
                from ..config import DEFAULT_CRYPTO
                _known_crypto = {p.split("/")[0].upper() for p in DEFAULT_CRYPTO if "/" in p}
            except Exception:
                _known_crypto = set()
        return _known_crypto

# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS crypto_listings (
            symbol      TEXT PRIMARY KEY,
            base_asset  TEXT NOT NULL,
            quote_asset TEXT NOT NULL,
            exchange    TEXT NOT NULL DEFAULT 'Binance',
            status      TEXT,
            first_seen  TEXT NOT NULL,
            is_new      INTEGER NOT NULL DEFAULT 1,
            price_usdt  REAL,
            volume_24h  REAL,
            change_24h  REAL,
            market_cap  REAL,
            source      TEXT DEFAULT 'binance'
        );
        CREATE TABLE IF NOT EXISTS stock_ipo_listings (
            symbol         TEXT PRIMARY KEY,
            company_name   TEXT,
            exchange       TEXT,
            ipo_date       TEXT,
            offer_price    REAL,
            shares_offered TEXT,
            first_seen     TEXT NOT NULL,
            is_new         INTEGER NOT NULL DEFAULT 1,
            status         TEXT DEFAULT 'upcoming',
            market_cap     TEXT,
            sector         TEXT
        );
        CREATE TABLE IF NOT EXISTS etf_listings (
            symbol        TEXT PRIMARY KEY,
            name          TEXT,
            issuer        TEXT,
            category      TEXT,
            inception     TEXT,
            aum           REAL,
            expense_ratio REAL,
            price         REAL,
            change_pct    REAL,
            first_seen    TEXT NOT NULL,
            is_new        INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS bond_rates (
            id          TEXT PRIMARY KEY,
            name        TEXT,
            symbol      TEXT,
            rate        REAL,
            prev_rate   REAL,
            change_bps  REAL,
            category    TEXT,
            updated_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS global_indices (
            symbol      TEXT PRIMARY KEY,
            name        TEXT,
            region      TEXT,
            price       REAL,
            change_pct  REAL,
            change_abs  REAL,
            currency    TEXT,
            updated_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS forex_pairs (
            pair        TEXT PRIMARY KEY,
            base        TEXT,
            quote       TEXT,
            rate        REAL,
            change_pct  REAL,
            category    TEXT,
            updated_at  TEXT
        );
        """)
        conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# 1. CRYPTO — Binance + CoinGecko
# ─────────────────────────────────────────────────────────────────────────────
_BINANCE_API        = "https://api.binance.com/api/v3/exchangeInfo"
_BINANCE_TICKER     = "https://api.binance.com/api/v3/ticker/24hr"
_COINGECKO_TRENDING = "https://api.coingecko.com/api/v3/search/trending"
_COINGECKO_MARKET   = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=recently_added&per_page=50&page=1"
_QUOTE_ASSETS       = {"USDT", "BTC", "ETH", "BNB", "USDC"}


def _fetch_binance_symbols() -> List[Dict]:
    try:
        resp = requests.get(_BINANCE_API, timeout=20)
        resp.raise_for_status()
        return [
            {
                "symbol":      s["symbol"],
                "base_asset":  s["baseAsset"],
                "quote_asset": s["quoteAsset"],
                "status":      s["status"],
            }
            for s in resp.json().get("symbols", [])
            if s.get("status") == "TRADING" and s.get("quoteAsset") in _QUOTE_ASSETS
        ]
    except Exception as e:
        print(f"[NewListings] Binance error: {e}")
        return []


def _fetch_binance_tickers() -> Dict[str, Dict]:
    try:
        resp = requests.get(_BINANCE_TICKER, timeout=30)
        resp.raise_for_status()
        return {t["symbol"]: t for t in resp.json()}
    except Exception:
        return {}


def _fetch_coingecko_trending() -> List[Dict]:
    """Get CoinGecko trending coins with price data."""
    try:
        resp = requests.get(_COINGECKO_TRENDING, timeout=15, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return []
        coins = resp.json().get("coins", [])
        results = []
        for item in coins[:10]:
            coin = item.get("item", {})
            results.append({
                "symbol":     coin.get("symbol", "").upper() + "USDT",
                "base_asset": coin.get("symbol", "").upper(),
                "quote_asset": "USDT",
                "price_usdt": coin.get("data", {}).get("price", 0),
                "change_24h": coin.get("data", {}).get("price_change_percentage_24h", {}).get("usd", 0),
                "market_cap": coin.get("data", {}).get("market_cap", ""),
                "source":     "coingecko_trending",
            })
        return results
    except Exception as e:
        print(f"[NewListings] CoinGecko trending error: {e}")
        return []


def _fetch_coingecko_new() -> List[Dict]:
    """Get recently added CoinGecko coins."""
    try:
        resp = requests.get(_COINGECKO_MARKET, timeout=15, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return []
        results = []
        for coin in resp.json()[:30]:
            sym = (coin.get("symbol") or "").upper()
            if not sym:
                continue
            results.append({
                "symbol":     sym + "USDT",
                "base_asset": sym,
                "quote_asset": "USDT",
                "price_usdt": coin.get("current_price", 0),
                "volume_24h": coin.get("total_volume", 0),
                "change_24h": coin.get("price_change_percentage_24h", 0),
                "market_cap": coin.get("market_cap", 0),
                "source":     "coingecko_new",
            })
        return results
    except Exception as e:
        print(f"[NewListings] CoinGecko new error: {e}")
        return []


def _sync_crypto_listings():
    print("[NewListings] Syncing crypto…")
    symbols  = _fetch_binance_symbols()
    tickers  = _fetch_binance_tickers()
    cg_trend = _fetch_coingecko_trending()
    cg_new   = _fetch_coingecko_new()
    known    = _get_known_crypto()
    now      = datetime.utcnow().isoformat()

    usdt_syms = [s for s in symbols if s["quote_asset"] == "USDT"]

    with _get_conn() as conn:
        existing  = {r["symbol"] for r in conn.execute("SELECT symbol FROM crypto_listings").fetchall()}
        new_count = 0

        for s in usdt_syms:
            sym = s["symbol"]
            if sym in existing:
                t = tickers.get(sym, {})
                conn.execute(
                    "UPDATE crypto_listings SET price_usdt=?,volume_24h=?,change_24h=? WHERE symbol=?",
                    (
                        float(t.get("lastPrice", 0) or 0),
                        float(t.get("quoteVolume", 0) or 0),
                        float(t.get("priceChangePercent", 0) or 0),
                        sym,
                    ),
                )
                continue
            base = s["base_asset"].upper()
            t    = tickers.get(sym, {})
            conn.execute(
                "INSERT OR IGNORE INTO crypto_listings "
                "(symbol,base_asset,quote_asset,exchange,status,first_seen,is_new,"
                "price_usdt,volume_24h,change_24h,source) "
                "VALUES (?,?,?,'Binance',?,?,?,?,?,?,'binance')",
                (
                    sym, base, s["quote_asset"], s["status"], now,
                    0 if base in known else 1,
                    float(t.get("lastPrice", 0) or 0),
                    float(t.get("quoteVolume", 0) or 0),
                    float(t.get("priceChangePercent", 0) or 0),
                ),
            )
            new_count += 1

        # CoinGecko trending + new
        for item in cg_trend + cg_new:
            sym = item["symbol"]
            if sym in existing:
                continue
            base = item["base_asset"].upper()
            conn.execute(
                "INSERT OR IGNORE INTO crypto_listings "
                "(symbol,base_asset,quote_asset,exchange,status,first_seen,is_new,"
                "price_usdt,volume_24h,change_24h,market_cap,source) "
                "VALUES (?,?,?,'CoinGecko','TRADING',?,?,?,?,?,?,?)",
                (
                    sym, base, item["quote_asset"], now,
                    1 if base not in known else 0,
                    float(item.get("price_usdt", 0) or 0),
                    float(item.get("volume_24h", 0) or 0),
                    float(item.get("change_24h", 0) or 0),
                    float(item.get("market_cap", 0) or 0),
                    item.get("source", "coingecko"),
                ),
            )

        conn.commit()
    print(f"[NewListings] Crypto done — {new_count} new Binance pairs + CoinGecko data")


# ─────────────────────────────────────────────────────────────────────────────
# 2. STOCKS — NASDAQ IPO (keep existing logic)
# ─────────────────────────────────────────────────────────────────────────────
_NASDAQ_IPO_API = (
    "https://api.nasdaq.com/api/ipo/upcoming?"
    "assetClass=stocks&offset=0&limit=50&type=upcoming&sortColumn=priceDateMs&sortOrder=desc"
)
_NASDAQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "application/json, text/plain, */*",
    "Referer":    "https://www.nasdaq.com/",
}


def _parse_price(raw: str) -> Optional[float]:
    if not raw:
        return None
    try:
        clean = raw.replace("$", "").replace(",", "").strip()
        if "-" in clean:
            parts = [float(p.strip()) for p in clean.split("-") if p.strip()]
            return round(sum(parts) / len(parts), 2) if parts else None
        return float(clean)
    except Exception:
        return None


def _fetch_nasdaq_ipos() -> List[Dict]:
    try:
        resp = requests.get(_NASDAQ_IPO_API, headers=_NASDAQ_HEADERS, timeout=20)
        resp.raise_for_status()
        rows = resp.json().get("data", {}).get("upcomingData", {}).get("rows", [])
        return [
            {
                "symbol":         (r.get("proposedTickerSymbol") or "").strip().upper(),
                "company_name":   r.get("companyName", ""),
                "exchange":       r.get("proposedExchange", ""),
                "ipo_date":       r.get("expectedPriceDate", ""),
                "offer_price":    _parse_price(r.get("proposedSharePrice", "")),
                "shares_offered": r.get("sharesOffered", ""),
                "status":         "upcoming",
                "sector":         r.get("primaryMarket", ""),
            }
            for r in rows
            if r.get("proposedTickerSymbol")
        ]
    except Exception as e:
        print(f"[NewListings] NASDAQ IPO error: {e}")
        return []


def _sync_stock_listings():
    print("[NewListings] Syncing stock IPOs…")
    ipos = _fetch_nasdaq_ipos()
    now  = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        existing  = {r["symbol"] for r in conn.execute("SELECT symbol FROM stock_ipo_listings").fetchall()}
        new_count = 0
        for ipo in ipos:
            sym = ipo["symbol"]
            if not sym or sym in existing:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO stock_ipo_listings "
                "(symbol,company_name,exchange,ipo_date,offer_price,"
                "shares_offered,first_seen,is_new,status,sector) "
                "VALUES (?,?,?,?,?,?,?,1,?,?)",
                (
                    sym, ipo["company_name"], ipo["exchange"], ipo["ipo_date"],
                    ipo["offer_price"], ipo["shares_offered"], now,
                    ipo["status"], ipo["sector"],
                ),
            )
            new_count += 1
        conn.commit()
    print(f"[NewListings] IPO done — {new_count} new")


# ─────────────────────────────────────────────────────────────────────────────
# 3. ETFs — Recently launched + major funds updated prices
# ─────────────────────────────────────────────────────────────────────────────
_RECENT_ETFS = [
    # Bitcoin spot ETFs
    {"symbol": "BITO", "name": "ProShares Bitcoin Strategy ETF",        "issuer": "ProShares",  "category": "Crypto",     "inception": "2021-10-19", "expense_ratio": 0.95},
    {"symbol": "FBTC", "name": "Fidelity Wise Origin Bitcoin Fund",      "issuer": "Fidelity",   "category": "Crypto",     "inception": "2024-01-11", "expense_ratio": 0.25},
    {"symbol": "IBIT", "name": "iShares Bitcoin Trust",                  "issuer": "BlackRock",  "category": "Crypto",     "inception": "2024-01-11", "expense_ratio": 0.25},
    {"symbol": "ARKB", "name": "ARK 21Shares Bitcoin ETF",               "issuer": "ARK",        "category": "Crypto",     "inception": "2024-01-11", "expense_ratio": 0.21},
    {"symbol": "GBTC", "name": "Grayscale Bitcoin Trust ETF",            "issuer": "Grayscale",  "category": "Crypto",     "inception": "2024-01-11", "expense_ratio": 1.50},
    {"symbol": "EZBC", "name": "Franklin Bitcoin ETF",                   "issuer": "Franklin",   "category": "Crypto",     "inception": "2024-01-11", "expense_ratio": 0.19},
    {"symbol": "ETHW", "name": "Bitwise Ethereum ETF",                   "issuer": "Bitwise",    "category": "Crypto",     "inception": "2024-07-23", "expense_ratio": 0.20},
    {"symbol": "ETHA", "name": "iShares Ethereum Trust ETF",             "issuer": "BlackRock",  "category": "Crypto",     "inception": "2024-07-23", "expense_ratio": 0.25},
    # AI/Tech thematic
    {"symbol": "BOTZ", "name": "Global X Robotics & AI ETF",             "issuer": "Global X",   "category": "AI/Tech",    "inception": "2016-09-12", "expense_ratio": 0.68},
    {"symbol": "ROBO", "name": "ROBO Global Robotics & Automation",      "issuer": "ROBO",       "category": "AI/Tech",    "inception": "2013-10-22", "expense_ratio": 0.95},
    {"symbol": "CHAT", "name": "Roundhill Generative AI & Technology",   "issuer": "Roundhill",  "category": "AI/Tech",    "inception": "2023-05-10", "expense_ratio": 0.75},
    {"symbol": "AIQ",  "name": "Global X Artificial Intelligence ETF",   "issuer": "Global X",   "category": "AI/Tech",    "inception": "2018-05-11", "expense_ratio": 0.68},
    # Bond ETFs
    {"symbol": "BND",  "name": "Vanguard Total Bond Market ETF",         "issuer": "Vanguard",   "category": "Bonds",      "inception": "2007-04-03", "expense_ratio": 0.03},
    {"symbol": "TLT",  "name": "iShares 20+ Year Treasury Bond ETF",     "issuer": "BlackRock",  "category": "Bonds",      "inception": "2002-07-22", "expense_ratio": 0.15},
    {"symbol": "HYG",  "name": "iShares iBoxx $ High Yield Corp Bond",   "issuer": "BlackRock",  "category": "Bonds",      "inception": "2007-04-04", "expense_ratio": 0.48},
    # Commodity ETFs
    {"symbol": "GLD",  "name": "SPDR Gold Shares",                       "issuer": "State Street","category": "Commodities","inception": "2004-11-18", "expense_ratio": 0.40},
    {"symbol": "SLV",  "name": "iShares Silver Trust",                   "issuer": "BlackRock",  "category": "Commodities","inception": "2006-04-21", "expense_ratio": 0.50},
    {"symbol": "USO",  "name": "United States Oil Fund",                  "issuer": "USCF",       "category": "Commodities","inception": "2006-04-10", "expense_ratio": 0.60},
]


def _sync_etf_listings():
    print("[NewListings] Syncing ETFs…")
    try:
        import yfinance as yf
        now = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            existing = {r["symbol"] for r in conn.execute("SELECT symbol FROM etf_listings").fetchall()}
            for etf in _RECENT_ETFS:
                sym = etf["symbol"]
                try:
                    ticker = yf.Ticker(sym)
                    fi     = ticker.fast_info
                    price  = float(getattr(fi, "last_price", 0) or 0)
                    prev   = float(getattr(fi, "previous_close", price) or price)
                    chg    = (price - prev) / (abs(prev) + 1e-9) * 100 if prev else 0.0
                    aum    = float(getattr(fi, "market_cap", 0) or 0)
                except Exception:
                    price, chg, aum = 0.0, 0.0, 0.0

                if sym not in existing:
                    conn.execute(
                        "INSERT OR IGNORE INTO etf_listings "
                        "(symbol,name,issuer,category,inception,aum,expense_ratio,"
                        "price,change_pct,first_seen,is_new) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,1)",
                        (
                            sym, etf["name"], etf["issuer"], etf["category"],
                            etf.get("inception", ""), aum, etf.get("expense_ratio", 0),
                            price, round(chg, 3), now,
                        ),
                    )
                else:
                    conn.execute(
                        "UPDATE etf_listings SET price=?,change_pct=?,aum=? WHERE symbol=?",
                        (price, round(chg, 3), aum, sym),
                    )
            conn.commit()
    except Exception as e:
        print(f"[NewListings] ETF error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. BONDS / RATES — Treasury yields + key rates
# ─────────────────────────────────────────────────────────────────────────────
_BOND_SYMBOLS = [
    # US Treasury yields
    {"id": "US2Y",    "name": "US 2-Year Treasury Yield",       "symbol": "^IRX",    "category": "Treasury"},
    {"id": "US5Y",    "name": "US 5-Year Treasury Yield",       "symbol": "^FVX",    "category": "Treasury"},
    {"id": "US10Y",   "name": "US 10-Year Treasury Yield",      "symbol": "^TNX",    "category": "Treasury"},
    {"id": "US30Y",   "name": "US 30-Year Treasury Yield",      "symbol": "^TYX",    "category": "Treasury"},
    # Bond indices via ETF proxies
    {"id": "CORP_HY", "name": "High Yield Spread (HYG)",        "symbol": "HYG",     "category": "Corporate"},
    {"id": "AGG",     "name": "US Aggregate Bond (AGG)",         "symbol": "AGG",     "category": "Aggregate"},
    # International
    {"id": "EU10Y",   "name": "EUR/USD 10Y Spread (proxy)",     "symbol": "BUND.DE", "category": "International"},
    # TIPS
    {"id": "TIPS10Y", "name": "10-Year TIPS Yield",             "symbol": "TIP",     "category": "Inflation"},
    # Repo
    {"id": "SOFR",    "name": "SOFR Rate (proxy: SHY)",         "symbol": "SHY",     "category": "Repo"},
]


def _sync_bond_rates():
    print("[NewListings] Syncing bond rates…")
    try:
        import yfinance as yf
        now = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            for bond in _BOND_SYMBOLS:
                try:
                    ticker  = yf.Ticker(bond["symbol"])
                    fi      = ticker.fast_info
                    rate    = float(getattr(fi, "last_price", 0) or 0)
                    prev    = float(getattr(fi, "previous_close", rate) or rate)
                    chg_bps = (rate - prev) * 100  # basis points
                except Exception:
                    rate, prev, chg_bps = 0.0, 0.0, 0.0

                conn.execute(
                    "INSERT OR REPLACE INTO bond_rates "
                    "(id,name,symbol,rate,prev_rate,change_bps,category,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (bond["id"], bond["name"], bond["symbol"], rate, prev,
                     round(chg_bps, 2), bond["category"], now),
                )
            conn.commit()
    except Exception as e:
        print(f"[NewListings] Bond rates error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. GLOBAL INDICES
# ─────────────────────────────────────────────────────────────────────────────
_GLOBAL_INDICES = [
    {"symbol": "^GSPC",    "name": "S&P 500",             "region": "US",          "currency": "USD"},
    {"symbol": "^NDX",     "name": "NASDAQ-100",           "region": "US",          "currency": "USD"},
    {"symbol": "^DJI",     "name": "Dow Jones",            "region": "US",          "currency": "USD"},
    {"symbol": "^RUT",     "name": "Russell 2000",         "region": "US",          "currency": "USD"},
    {"symbol": "^VIX",     "name": "CBOE VIX",             "region": "US",          "currency": "USD"},
    {"symbol": "^FTSE",    "name": "FTSE 100",             "region": "UK",          "currency": "GBP"},
    {"symbol": "^GDAXI",   "name": "DAX",                  "region": "Germany",     "currency": "EUR"},
    {"symbol": "^FCHI",    "name": "CAC 40",               "region": "France",      "currency": "EUR"},
    {"symbol": "^STOXX50E","name": "Euro Stoxx 50",        "region": "Europe",      "currency": "EUR"},
    {"symbol": "^N225",    "name": "Nikkei 225",           "region": "Japan",       "currency": "JPY"},
    {"symbol": "^HSI",     "name": "Hang Seng",            "region": "HK",          "currency": "HKD"},
    {"symbol": "000001.SS","name": "Shanghai Composite",   "region": "China",       "currency": "CNY"},
    {"symbol": "^NSEI",    "name": "Nifty 50",             "region": "India",       "currency": "INR"},
    {"symbol": "^BSESN",   "name": "BSE Sensex",           "region": "India",       "currency": "INR"},
    {"symbol": "^AXJO",    "name": "ASX 200",              "region": "Australia",   "currency": "AUD"},
    {"symbol": "^GSPTSE",  "name": "TSX Composite",        "region": "Canada",      "currency": "CAD"},
    {"symbol": "^MERV",    "name": "MERVAL",               "region": "Argentina",   "currency": "ARS"},
    {"symbol": "^BVSP",    "name": "Bovespa",              "region": "Brazil",      "currency": "BRL"},
    {"symbol": "^KS11",    "name": "KOSPI",                "region": "South Korea", "currency": "KRW"},
    {"symbol": "^TWII",    "name": "TAIEX",                "region": "Taiwan",      "currency": "TWD"},
]


def _sync_indices():
    print("[NewListings] Syncing global indices…")
    try:
        import yfinance as yf
        now = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            for idx in _GLOBAL_INDICES:
                try:
                    ticker  = yf.Ticker(idx["symbol"])
                    fi      = ticker.fast_info
                    price   = float(getattr(fi, "last_price", 0) or 0)
                    prev    = float(getattr(fi, "previous_close", price) or price)
                    chg_pct = (price - prev) / (abs(prev) + 1e-9) * 100 if prev else 0.0
                    chg_abs = price - prev
                except Exception:
                    price, chg_pct, chg_abs = 0.0, 0.0, 0.0

                conn.execute(
                    "INSERT OR REPLACE INTO global_indices "
                    "(symbol,name,region,price,change_pct,change_abs,currency,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        idx["symbol"], idx["name"], idx["region"],
                        price, round(chg_pct, 3), round(chg_abs, 3),
                        idx["currency"], now,
                    ),
                )
            conn.commit()
    except Exception as e:
        print(f"[NewListings] Indices error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. FOREX
# ─────────────────────────────────────────────────────────────────────────────
_FOREX_PAIRS = [
    # Majors
    {"pair": "EUR/USD", "base": "EUR", "quote": "USD", "category": "Major", "yf": "EURUSD=X"},
    {"pair": "GBP/USD", "base": "GBP", "quote": "USD", "category": "Major", "yf": "GBPUSD=X"},
    {"pair": "USD/JPY", "base": "USD", "quote": "JPY", "category": "Major", "yf": "USDJPY=X"},
    {"pair": "USD/CHF", "base": "USD", "quote": "CHF", "category": "Major", "yf": "USDCHF=X"},
    {"pair": "AUD/USD", "base": "AUD", "quote": "USD", "category": "Major", "yf": "AUDUSD=X"},
    {"pair": "USD/CAD", "base": "USD", "quote": "CAD", "category": "Major", "yf": "USDCAD=X"},
    {"pair": "NZD/USD", "base": "NZD", "quote": "USD", "category": "Major", "yf": "NZDUSD=X"},
    # Minors
    {"pair": "EUR/GBP", "base": "EUR", "quote": "GBP", "category": "Minor", "yf": "EURGBP=X"},
    {"pair": "EUR/JPY", "base": "EUR", "quote": "JPY", "category": "Minor", "yf": "EURJPY=X"},
    {"pair": "GBP/JPY", "base": "GBP", "quote": "JPY", "category": "Minor", "yf": "GBPJPY=X"},
    {"pair": "EUR/CHF", "base": "EUR", "quote": "CHF", "category": "Minor", "yf": "EURCHF=X"},
    {"pair": "AUD/JPY", "base": "AUD", "quote": "JPY", "category": "Minor", "yf": "AUDJPY=X"},
    # Exotics
    {"pair": "USD/INR", "base": "USD", "quote": "INR", "category": "Exotic", "yf": "USDINR=X"},
    {"pair": "USD/CNY", "base": "USD", "quote": "CNY", "category": "Exotic", "yf": "USDCNY=X"},
    {"pair": "USD/BRL", "base": "USD", "quote": "BRL", "category": "Exotic", "yf": "USDBRL=X"},
    {"pair": "USD/MXN", "base": "USD", "quote": "MXN", "category": "Exotic", "yf": "USDMXN=X"},
    {"pair": "USD/KRW", "base": "USD", "quote": "KRW", "category": "Exotic", "yf": "USDKRW=X"},
    {"pair": "USD/SGD", "base": "USD", "quote": "SGD", "category": "Exotic", "yf": "USDSGD=X"},
    {"pair": "USD/HKD", "base": "USD", "quote": "HKD", "category": "Exotic", "yf": "USDHKD=X"},
    {"pair": "USD/TRY", "base": "USD", "quote": "TRY", "category": "Exotic", "yf": "USDTRY=X"},
]


def _sync_forex():
    print("[NewListings] Syncing forex…")
    try:
        import yfinance as yf
        now = datetime.utcnow().isoformat()
        with _get_conn() as conn:
            for fx in _FOREX_PAIRS:
                try:
                    ticker = yf.Ticker(fx["yf"])
                    fi     = ticker.fast_info
                    rate   = float(getattr(fi, "last_price", 0) or 0)
                    prev   = float(getattr(fi, "previous_close", rate) or rate)
                    chg    = (rate - prev) / (abs(prev) + 1e-9) * 100 if prev else 0.0
                except Exception:
                    rate, chg = 0.0, 0.0

                conn.execute(
                    "INSERT OR REPLACE INTO forex_pairs "
                    "(pair,base,quote,rate,change_pct,category,updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (fx["pair"], fx["base"], fx["quote"], rate, round(chg, 4),
                     fx["category"], now),
                )
            conn.commit()
    except Exception as e:
        print(f"[NewListings] Forex error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Public query API
# ─────────────────────────────────────────────────────────────────────────────

def get_new_crypto(limit: int = 100, only_new: bool = False, min_volume: float = 0.0) -> List[Dict]:
    with _get_conn() as conn:
        conds: List[str] = []
        params: List     = []
        if only_new:
            conds.append("is_new=1")
        if min_volume > 0:
            conds.append("volume_24h>=?")
            params.append(min_volume)
        q = "SELECT * FROM crypto_listings"
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY volume_24h DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def get_new_ipos(limit: int = 50, status: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM stock_ipo_listings WHERE status=? ORDER BY ipo_date DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stock_ipo_listings ORDER BY ipo_date DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_etfs(limit: int = 50, category: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM etf_listings WHERE category=? ORDER BY aum DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM etf_listings ORDER BY aum DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_bond_rates() -> List[Dict]:
    with _get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM bond_rates ORDER BY category, id"
        ).fetchall()]


def get_indices(region: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if region:
            rows = conn.execute(
                "SELECT * FROM global_indices WHERE region=? ORDER BY symbol",
                (region,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM global_indices ORDER BY region, symbol"
            ).fetchall()
        return [dict(r) for r in rows]


def get_forex(category: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM forex_pairs WHERE category=? ORDER BY pair",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM forex_pairs ORDER BY category, pair"
            ).fetchall()
        return [dict(r) for r in rows]


def get_all_new(limit: int = 200) -> Dict:
    return {
        "crypto":        get_new_crypto(limit=limit, only_new=True, min_volume=100_000),
        "stocks":        get_new_ipos(limit=50),
        "etfs":          get_etfs(limit=50),
        "bonds":         get_bond_rates(),
        "indices":       get_indices(),
        "forex":         get_forex(),
        "total_crypto":  len(get_new_crypto(only_new=True, min_volume=100_000)),
        "total_stocks":  len(get_new_ipos()),
        "updated_at":    datetime.utcnow().isoformat(),
    }


def get_summary() -> Dict:
    with _get_conn() as conn:
        return {
            "total_crypto_tracked": conn.execute("SELECT COUNT(*) FROM crypto_listings").fetchone()[0],
            "new_crypto_coins":     conn.execute("SELECT COUNT(*) FROM crypto_listings WHERE is_new=1").fetchone()[0],
            "total_ipos":           conn.execute("SELECT COUNT(*) FROM stock_ipo_listings").fetchone()[0],
            "upcoming_ipos":        conn.execute("SELECT COUNT(*) FROM stock_ipo_listings WHERE status='upcoming'").fetchone()[0],
            "etfs_tracked":         conn.execute("SELECT COUNT(*) FROM etf_listings").fetchone()[0],
            "bond_rates_tracked":   conn.execute("SELECT COUNT(*) FROM bond_rates").fetchone()[0],
            "indices_tracked":      conn.execute("SELECT COUNT(*) FROM global_indices").fetchone()[0],
            "forex_pairs_tracked":  conn.execute("SELECT COUNT(*) FROM forex_pairs").fetchone()[0],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Background daemon
# ─────────────────────────────────────────────────────────────────────────────

class NewListingsTracker:
    CRYPTO_H  = 6
    STOCK_H   = 24
    ETF_H     = 24
    BOND_MIN  = 60
    INDEX_MIN = 15
    FOREX_MIN = 15

    def __init__(self):
        _init_db()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def _loop(self):
        print("[NewListings] Multi-asset daemon started")
        crypto_due = stock_due = etf_due = datetime.utcnow()
        bond_due   = index_due = forex_due = datetime.utcnow()

        while self._running:
            now = datetime.utcnow()
            try:
                if now >= crypto_due:
                    _sync_crypto_listings()
                    crypto_due = now + timedelta(hours=self.CRYPTO_H)
                if now >= stock_due:
                    _sync_stock_listings()
                    stock_due = now + timedelta(hours=self.STOCK_H)
                if now >= etf_due:
                    _sync_etf_listings()
                    etf_due = now + timedelta(hours=self.ETF_H)
                if now >= bond_due:
                    _sync_bond_rates()
                    bond_due = now + timedelta(minutes=self.BOND_MIN)
                if now >= index_due:
                    _sync_indices()
                    index_due = now + timedelta(minutes=self.INDEX_MIN)
                if now >= forex_due:
                    _sync_forex()
                    forex_due = now + timedelta(minutes=self.FOREX_MIN)
            except Exception:
                traceback.print_exc()

            # Sleep in 1-second ticks so stop() is responsive
            for _ in range(60):
                if not self._running:
                    break
                time.sleep(1)

        print("[NewListings] Multi-asset daemon stopped")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="NewListings")
        self._thread.start()
        print(
            "[NewListings] Tracker started "
            "(crypto/6h, stocks/24h, etfs/24h, bonds/1h, indices/15min, forex/15min)"
        )

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def force_refresh(self, asset_class: str = "all"):
        """Trigger an immediate out-of-band refresh (runs in caller's thread)."""
        if asset_class in ("all", "crypto"):   _sync_crypto_listings()
        if asset_class in ("all", "stocks"):   _sync_stock_listings()
        if asset_class in ("all", "etfs"):     _sync_etf_listings()
        if asset_class in ("all", "bonds"):    _sync_bond_rates()
        if asset_class in ("all", "indices"):  _sync_indices()
        if asset_class in ("all", "forex"):    _sync_forex()


# ── Singleton ─────────────────────────────────────────────────────────────────
new_listings_tracker = NewListingsTracker()
