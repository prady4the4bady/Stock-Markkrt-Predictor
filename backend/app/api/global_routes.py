"""
NexusTrader — Global Market Routes
=====================================
Endpoints that power the interactive 3D globe view.

All data sources: yfinance (free, no key) + web_searcher for news.

Endpoints:
  GET /api/global/overview          — all countries scored for globe colouring
  GET /api/global/markets/{code}    — detailed indices for one country
  GET /api/global/news/{code}       — live news headlines for a country
  GET /api/global/heatmap           — compact heat-map data (change_pct per country)
"""

import re
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
import yfinance as yf
import numpy as np

router = APIRouter(prefix="/api/global", tags=["Global Markets"])

# ─────────────────────────────────────────────────────────────────────────────
# Country → Market Index mapping
# All symbols are yfinance-compatible (free, no API key)
# ─────────────────────────────────────────────────────────────────────────────

COUNTRY_MARKETS: Dict[str, Dict] = {
    "US": {
        "name": "United States", "emoji": "🇺🇸",
        "currency": "USD", "lat": 38.0, "lng": -97.0,
        "indices": [
            ("S&P 500",  "^GSPC"),
            ("NASDAQ",   "^IXIC"),
            ("Dow Jones","^DJI"),
        ],
        "search_query": "US stock market Wall Street today",
    },
    "GB": {
        "name": "United Kingdom", "emoji": "🇬🇧",
        "currency": "GBP", "lat": 55.0, "lng": -3.5,
        "indices": [("FTSE 100", "^FTSE")],
        "search_query": "UK stock market FTSE London today",
    },
    "JP": {
        "name": "Japan", "emoji": "🇯🇵",
        "currency": "JPY", "lat": 36.0, "lng": 138.0,
        "indices": [("Nikkei 225", "^N225"), ("TOPIX", "^TOPX")],
        "search_query": "Japan stock market Nikkei Tokyo today",
    },
    "DE": {
        "name": "Germany", "emoji": "🇩🇪",
        "currency": "EUR", "lat": 51.0, "lng": 10.0,
        "indices": [("DAX", "^GDAXI"), ("MDAX", "^MDAXI")],
        "search_query": "Germany DAX Frankfurt stock market today",
    },
    "CN": {
        "name": "China", "emoji": "🇨🇳",
        "currency": "CNY", "lat": 35.0, "lng": 105.0,
        "indices": [("Shanghai Comp.", "000001.SS"), ("CSI 300", "000300.SS")],
        "search_query": "China stock market Shanghai SSE today",
    },
    "HK": {
        "name": "Hong Kong", "emoji": "🇭🇰",
        "currency": "HKD", "lat": 22.3, "lng": 114.2,
        "indices": [("Hang Seng", "^HSI"), ("HS Tech", "^HSTECH")],
        "search_query": "Hong Kong Hang Seng stock market today",
    },
    "IN": {
        "name": "India", "emoji": "🇮🇳",
        "currency": "INR", "lat": 20.0, "lng": 78.0,
        "indices": [("NIFTY 50", "^NSEI"), ("Sensex", "^BSESN")],
        "search_query": "India NIFTY Sensex BSE NSE stock market today",
    },
    "FR": {
        "name": "France", "emoji": "🇫🇷",
        "currency": "EUR", "lat": 46.0, "lng": 2.0,
        "indices": [("CAC 40", "^FCHI")],
        "search_query": "France CAC 40 Paris stock market today",
    },
    "CA": {
        "name": "Canada", "emoji": "🇨🇦",
        "currency": "CAD", "lat": 56.0, "lng": -106.0,
        "indices": [("TSX Composite", "^GSPTSE")],
        "search_query": "Canada TSX Toronto stock market today",
    },
    "AU": {
        "name": "Australia", "emoji": "🇦🇺",
        "currency": "AUD", "lat": -25.0, "lng": 133.0,
        "indices": [("ASX 200", "^AXJO"), ("All Ords", "^AORD")],
        "search_query": "Australia ASX 200 Sydney stock market today",
    },
    "BR": {
        "name": "Brazil", "emoji": "🇧🇷",
        "currency": "BRL", "lat": -10.0, "lng": -55.0,
        "indices": [("Bovespa", "^BVSP")],
        "search_query": "Brazil Bovespa B3 stock market today",
    },
    "KR": {
        "name": "South Korea", "emoji": "🇰🇷",
        "currency": "KRW", "lat": 36.0, "lng": 128.0,
        "indices": [("KOSPI", "^KS11"), ("KOSDAQ", "^KQ11")],
        "search_query": "Korea KOSPI Seoul stock market today",
    },
    "IT": {
        "name": "Italy", "emoji": "🇮🇹",
        "currency": "EUR", "lat": 42.0, "lng": 12.5,
        "indices": [("FTSE MIB", "FTSEMIB.MI")],
        "search_query": "Italy FTSE MIB Milan stock market today",
    },
    "ES": {
        "name": "Spain", "emoji": "🇪🇸",
        "currency": "EUR", "lat": 40.0, "lng": -4.0,
        "indices": [("IBEX 35", "^IBEX")],
        "search_query": "Spain IBEX 35 Madrid stock market today",
    },
    "CH": {
        "name": "Switzerland", "emoji": "🇨🇭",
        "currency": "CHF", "lat": 47.0, "lng": 8.5,
        "indices": [("SMI", "^SSMI")],
        "search_query": "Switzerland SMI Zurich stock market today",
    },
    "SG": {
        "name": "Singapore", "emoji": "🇸🇬",
        "currency": "SGD", "lat": 1.35, "lng": 103.8,
        "indices": [("STI", "^STI")],
        "search_query": "Singapore STI stock market today",
    },
    "TW": {
        "name": "Taiwan", "emoji": "🇹🇼",
        "currency": "TWD", "lat": 23.7, "lng": 121.0,
        "indices": [("Taiwan Weighted", "^TWII")],
        "search_query": "Taiwan TWSE stock market today",
    },
    "MX": {
        "name": "Mexico", "emoji": "🇲🇽",
        "currency": "MXN", "lat": 23.0, "lng": -102.0,
        "indices": [("IPC", "^MXX")],
        "search_query": "Mexico BMV IPC stock market today",
    },
    "ZA": {
        "name": "South Africa", "emoji": "🇿🇦",
        "currency": "ZAR", "lat": -29.0, "lng": 25.0,
        "indices": [("JSE All Share", "^J203.JO")],
        "search_query": "South Africa JSE stock market today",
    },
    "NL": {
        "name": "Netherlands", "emoji": "🇳🇱",
        "currency": "EUR", "lat": 52.3, "lng": 5.3,
        "indices": [("AEX", "AEX.AS")],
        "search_query": "Netherlands AEX Amsterdam stock market today",
    },
    "SE": {
        "name": "Sweden", "emoji": "🇸🇪",
        "currency": "SEK", "lat": 62.0, "lng": 15.0,
        "indices": [("OMX Stockholm", "^OMXS30")],
        "search_query": "Sweden OMX Stockholm stock market today",
    },
    "SA": {
        "name": "Saudi Arabia", "emoji": "🇸🇦",
        "currency": "SAR", "lat": 24.0, "lng": 45.0,
        "indices": [("Tadawul", "^TASI.SR")],
        "search_query": "Saudi Arabia Tadawul TASI stock market today",
    },
    "RU": {
        "name": "Russia", "emoji": "🇷🇺",
        "currency": "RUB", "lat": 60.0, "lng": 90.0,
        "indices": [("MOEX", "IMOEX.ME")],
        "search_query": "Russia MOEX Moscow stock market today",
    },
    "NG": {
        "name": "Nigeria", "emoji": "🇳🇬",
        "currency": "NGN", "lat": 9.0, "lng": 8.0,
        "indices": [("NGX All Share", "^NGSEINDX")],
        "search_query": "Nigeria NGX stock exchange Lagos today",
    },
    "AR": {
        "name": "Argentina", "emoji": "🇦🇷",
        "currency": "ARS", "lat": -38.0, "lng": -65.0,
        "indices": [("Merval", "^MERV")],
        "search_query": "Argentina Merval stock market Buenos Aires today",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# In-memory cache with TTL
# ─────────────────────────────────────────────────────────────────────────────

_overview_cache: Optional[Dict] = None
_overview_ts: float = 0.0
_country_cache: Dict[str, tuple] = {}  # code → (ts, data)
_cache_lock = threading.Lock()

OVERVIEW_TTL = 300   # 5 min
COUNTRY_TTL  = 180   # 3 min


def _fetch_index(symbol: str) -> Optional[Dict]:
    """Fetch latest price and % change for a yfinance index symbol."""
    try:
        ticker = yf.Ticker(symbol)
        fi = ticker.fast_info
        price = float(getattr(fi, "last_price", 0) or 0)
        prev  = float(getattr(fi, "previous_close", 0) or price or 1)
        if prev == 0:
            prev = price or 1
        change_pct = (price - prev) / abs(prev) * 100
        return {
            "price":      round(price, 2),
            "prev_close": round(prev, 2),
            "change":     round(price - prev, 2),
            "change_pct": round(change_pct, 3),
        }
    except Exception:
        return None


_CODE_RE = re.compile(r'^[A-Z]{2}$')

def _validate_code(code: str) -> str:
    """Validate and normalise a 2-letter ISO country code."""
    upper = code.strip().upper()
    if not _CODE_RE.match(upper):
        raise HTTPException(status_code=422, detail="Country code must be exactly 2 letters (e.g. 'US', 'GB')")
    if upper not in COUNTRY_MARKETS:
        raise HTTPException(status_code=404, detail=f"Country '{upper}' is not tracked")
    return upper


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/overview")
async def global_market_overview():
    """
    Returns all country market scores for globe polygon coloring.
    Each entry: {code, name, emoji, lat, lng, score, change_pct, status}
    Score: -100 (strong bear) to +100 (strong bull).
    Cached 5 minutes.
    """
    global _overview_cache, _overview_ts
    with _cache_lock:
        if _overview_cache and time.time() - _overview_ts < OVERVIEW_TTL:
            return _overview_cache

    results = []
    for code, info in COUNTRY_MARKETS.items():
        # Only primary index for overview (fast)
        primary_name, primary_sym = info["indices"][0]
        data = _fetch_index(primary_sym)
        if data:
            cp = data["change_pct"]
            score = float(np.clip(cp * 33, -100, 100))
            status = (
                "strong_bull" if score >= 33 else
                "bull"        if score >= 10 else
                "neutral"     if score >= -10 else
                "bear"        if score >= -33 else
                "strong_bear"
            )
        else:
            cp = 0.0
            score = 0.0
            status = "no_data"
        results.append({
            "code":       code,
            "name":       info["name"],
            "emoji":      info["emoji"],
            "lat":        info["lat"],
            "lng":        info["lng"],
            "score":      round(score, 1),
            "change_pct": round(cp, 3),
            "currency":   info["currency"],
            "status":     status,
            "primary_index": primary_name,
        })

    out = {
        "countries": results,
        "timestamp": datetime.now().isoformat(),
        "count": len(results),
    }
    with _cache_lock:
        _overview_cache = out
        _overview_ts = time.time()
    return out


@router.get("/markets/{country_code}")
async def country_markets(country_code: str):
    """
    Detailed market data for a single country.
    Returns all indices with price, change, change_pct, and a 7-day prediction.
    """
    code = _validate_code(country_code)

    # Check cache
    with _cache_lock:
        cached = _country_cache.get(code)
    if cached:
        ts, data = cached
        if time.time() - ts < COUNTRY_TTL:
            return data

    info = COUNTRY_MARKETS[code]
    indices_data = []
    total_change = []

    for idx_name, sym in info["indices"]:
        d = _fetch_index(sym)
        if d:
            total_change.append(d["change_pct"])
            # Quick 7-day prediction: linear extrapolation from recent trend
            try:
                hist = yf.Ticker(sym).history(period="1mo", interval="1d")
                if not hist.empty:
                    prices = hist["Close"].dropna().values
                    if len(prices) >= 5:
                        xs = np.arange(len(prices))
                        slope, intercept = np.polyfit(xs, prices, 1)
                        pred_7d = intercept + slope * (len(prices) + 6)
                        pred_change = (pred_7d - prices[-1]) / abs(prices[-1]) * 100
                        d["prediction_7d"] = round(float(pred_7d), 2)
                        d["prediction_change_pct"] = round(float(pred_change), 2)
                        d["trend"] = "up" if slope > 0 else "down"
            except Exception:
                pass
            indices_data.append({"name": idx_name, "symbol": sym, **d})

    avg_change = float(np.mean(total_change)) if total_change else 0.0
    score = float(np.clip(avg_change * 33, -100, 100))

    result = {
        "code":         code,
        "name":         info["name"],
        "emoji":        info["emoji"],
        "currency":     info["currency"],
        "lat":          info["lat"],
        "lng":          info["lng"],
        "indices":      indices_data,
        "avg_change_pct": round(avg_change, 3),
        "composite_score": round(score, 1),
        "market_status": _market_status(score),
        "timestamp":    datetime.now().isoformat(),
    }

    with _cache_lock:
        _country_cache[code] = (time.time(), result)
    return result


@router.get("/news/{country_code}")
async def country_news(
    country_code: str,
    max_results: int = Query(default=6, ge=1, le=12),
):
    """
    Live news headlines for a country's markets.
    Uses the multi-domain web searcher for aggregated results.
    """
    code = _validate_code(country_code)

    info = COUNTRY_MARKETS[code]
    query = info.get("search_query", f"{info['name']} stock market news")

    try:
        from ..agents.web_search import web_searcher
        results = web_searcher.search_question(query, max_sources=max_results)
        return {
            "code":    code,
            "name":    info["name"],
            "query":   query,
            "results": results,
            "count":   len(results) if isinstance(results, list) else 0,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        pass

    # Fallback: try yfinance news
    try:
        primary_sym = info["indices"][0][1]
        ticker = yf.Ticker(primary_sym)
        news = ticker.news or []
        headlines = [
            {
                "title":   n.get("title", ""),
                "source":  n.get("publisher", ""),
                "url":     n.get("link", ""),
                "time":    datetime.fromtimestamp(n.get("providerPublishTime", 0)).isoformat(),
                "summary": n.get("summary", ""),
            }
            for n in news[:max_results]
            if n.get("title")
        ]
        return {
            "code":      code,
            "name":      info["name"],
            "query":     query,
            "results":   headlines,
            "count":     len(headlines),
            "timestamp": datetime.now().isoformat(),
            "source":    "yfinance",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"News fetch failed: {e}")


@router.get("/heatmap")
async def global_heatmap():
    """
    Ultra-compact heat-map payload for globe polygon coloring.
    Returns {code: change_pct} for all countries.
    Cached 5 minutes.
    """
    overview = await global_market_overview()
    heatmap = {
        c["code"]: {
            "change_pct": c["change_pct"],
            "score":      c["score"],
            "status":     c["status"],
        }
        for c in overview["countries"]
    }
    return {"heatmap": heatmap, "timestamp": overview["timestamp"]}


@router.get("/countries")
async def list_countries():
    """Return the list of supported countries with metadata (no live prices)."""
    return {
        "countries": [
            {
                "code":     code,
                "name":     info["name"],
                "emoji":    info["emoji"],
                "currency": info["currency"],
                "lat":      info["lat"],
                "lng":      info["lng"],
                "primary_index": info["indices"][0][0],
            }
            for code, info in COUNTRY_MARKETS.items()
        ],
        "count": len(COUNTRY_MARKETS),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _market_status(score: float) -> str:
    if score >= 50:   return "Strong Bull"
    if score >= 20:   return "Bull"
    if score >= 5:    return "Mild Bull"
    if score >= -5:   return "Neutral"
    if score >= -20:  return "Mild Bear"
    if score >= -50:  return "Bear"
    return "Strong Bear"
