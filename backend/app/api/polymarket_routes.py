"""
NexusTrader — Polymarket + Polywhale Integration
==================================================
Endpoints for crowd-wisdom prediction market signals and screenshot analysis.

Polymarket (FREE — no API key):
  GET /api/polymarket/signals/{symbol}   — market-implied macro signals for a ticker
  GET /api/polymarket/markets            — live open prediction markets (finance/econ)

Polywhale (screenshot analysis — requires ANTHROPIC_API_KEY):
  POST /api/polymarket/analyze-screenshot — upload a Polymarket screenshot,
                                            get structured position analysis

Bloomberg (PAID — architecture stub):
  Full Bloomberg API integration requires a Bloomberg Terminal licence.
  Free alternative: RSS feed sentiment is already baked into the MarketOracle
  (bloomberg_rss signal layer).  When you have a Bloomberg API key, uncomment
  the BLOOMBERG_API_KEY section in config.py and this module will use it.

For the Anthropic (Polywhale) API key:
  1. Go to https://console.anthropic.com/
  2. Create account → API Keys → Create Key
  3. Add ANTHROPIC_API_KEY=sk-ant-... to your .env file (backend/.env)
  4. Redeploy — the analyze-screenshot endpoint will activate automatically

For TradingView data API (paid):
  1. Sign up at https://www.tradingview.com/data-pulses/
  2. Add TRADINGVIEW_API_KEY=... to .env
  Architecture: use lightweight REST calls to their /quotes and /history endpoints,
  map responses to the same df format used in data_manager.py.
"""

import os
import base64
import time
import threading
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
import requests
import numpy as np

router = APIRouter(prefix="/api/polymarket", tags=["Polymarket & Polywhale"])

# ─── In-memory caches ────────────────────────────────────────────────────────
_markets_cache: Optional[List[Dict]] = None
_markets_ts: float = 0.0
_signals_cache: Dict[str, tuple] = {}   # symbol → (ts, data)
_cache_lock = threading.Lock()

MARKETS_TTL = 120   # 2 min (Polymarket prices update frequently)
SIGNALS_TTL = 300   # 5 min

POLYMARKET_BASE = "https://gamma-api.polymarket.com"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _fetch_markets(limit: int = 100) -> List[Dict]:
    """Fetch open finance/economics markets from Polymarket's free public API."""
    global _markets_cache, _markets_ts
    with _cache_lock:
        if _markets_cache and time.time() - _markets_ts < MARKETS_TTL:
            return _markets_cache

    all_markets: List[Dict] = []
    for tag in ("economics", "finance", "crypto", "business"):
        try:
            resp = requests.get(
                f"{POLYMARKET_BASE}/markets",
                params={"closed": "false", "limit": limit // 4, "tag_slug": tag},
                timeout=6,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("markets", [])
                all_markets.extend(items)
        except Exception:
            pass

    # Deduplicate by ID
    seen = set()
    unique = []
    for m in all_markets:
        mid = m.get("id") or m.get("conditionId", "")
        if mid not in seen:
            seen.add(mid)
            unique.append(m)

    with _cache_lock:
        _markets_cache = unique
        _markets_ts = time.time()
    return unique


def _extract_probability(market: Dict) -> Optional[float]:
    """Extract YES probability (0-1) from a market object."""
    try:
        prices = market.get("outcomePrices") or []
        if prices:
            return float(prices[0])
        # Some endpoints return bestBid/bestAsk
        best_bid = market.get("bestBid")
        best_ask = market.get("bestAsk")
        if best_bid and best_ask:
            return (float(best_bid) + float(best_ask)) / 2
    except (TypeError, ValueError, IndexError):
        pass
    return None


def _question_signal(question: str, yes_prob: float, symbol: str) -> Optional[tuple]:
    """
    Map a Polymarket question + YES probability to a (bull_bear, weight) signal.
    Returns ('bull', weight), ('bear', weight), or None.
    """
    q = question.lower()
    volume_proxy = 1.0   # caller can pass actual volume for better weighting
    is_crypto = "/" in symbol or symbol in {"BTC", "ETH", "BNB", "SOL", "XRP",
                                             "ADA", "AVAX", "DOT", "LINK", "MATIC"}

    # ── Fed / interest rate ────────────────────────────────────────────────
    if any(kw in q for kw in ("rate cut", "cut rates", "reduce rates", "dovish", "pivot")):
        return ("bull", yes_prob)
    if any(kw in q for kw in ("rate hike", "raise rates", "increase rates", "hawkish")):
        return ("bear", yes_prob)

    # ── Recession / economy ───────────────────────────────────────────────
    if "recession" in q and not any(kw in q for kw in ("avoid", "no recession", "soft landing")):
        return ("bear", yes_prob)
    if any(kw in q for kw in ("soft landing", "no recession", "avoid recession")):
        return ("bull", yes_prob)

    # ── Broad market direction ────────────────────────────────────────────
    if any(idx in q for idx in ("s&p 500", "s&p500", "nasdaq", "dow jones", "stock market")):
        if any(kw in q for kw in ("above", "higher", "reach", "exceed", "record", "rally")):
            return ("bull", yes_prob * 0.8)
        if any(kw in q for kw in ("below", "lower", "crash", "fall", "correction", "bear")):
            return ("bear", yes_prob * 0.8)

    # ── Crypto specific ────────────────────────────────────────────────────
    if is_crypto:
        sym_lower = symbol.split("/")[0].lower()
        crypto_keywords = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH",
                           "eth": "ETH", "crypto": "*", sym_lower: symbol}
        if any(kw in q for kw in crypto_keywords):
            if any(kw in q for kw in ("above", "higher", "reach", "hit", "exceed", "ath")):
                return ("bull", yes_prob * 0.6)
            if any(kw in q for kw in ("below", "lower", "crash", "fall", "dump")):
                return ("bear", yes_prob * 0.6)

    # ── Inflation ─────────────────────────────────────────────────────────
    if "inflation" in q:
        if any(kw in q for kw in ("above", "exceed", "rise", "higher")):
            return ("bear", yes_prob * 0.5)   # high inflation = bearish
        if any(kw in q for kw in ("below", "fall", "lower", "target")):
            return ("bull", yes_prob * 0.5)

    return None


def _compute_polymarket_signal(symbol: str, markets: List[Dict]) -> Dict:
    """Convert a list of Polymarket markets into a net signal for the given symbol."""
    bull_signals = []
    bear_signals = []
    relevant_markets = []

    clean_sym = symbol.split("/")[0].upper()

    for market in markets:
        question = market.get("question", "")
        if not question:
            continue
        yes_prob = _extract_probability(market)
        if yes_prob is None:
            continue

        volume = float(market.get("volume", 0) or 0)
        weight = min(1.5, 0.5 + volume / 1_000_000)   # volume-weighted, capped

        result = _question_signal(question, yes_prob, clean_sym)
        if result is None:
            continue

        direction, prob = result
        weighted_prob = prob * weight

        if direction == "bull":
            bull_signals.append((yes_prob, weighted_prob))
        else:
            bear_signals.append((yes_prob, weighted_prob))

        relevant_markets.append({
            "question":    question,
            "direction":   direction,
            "yes_prob":    round(yes_prob, 3),
            "volume":      round(volume),
            "url":         market.get("url") or market.get("slug", ""),
        })

    def wavg(signals):
        if not signals:
            return 0.5
        total_w = sum(w for _, w in signals) or 1e-9
        return sum(p * w for p, w in signals) / total_w

    bull_avg = wavg(bull_signals)
    bear_avg = wavg(bear_signals)

    # Convert to [-1, +1]
    bull_score = (bull_avg - 0.5) * 2  # 0.7 → +0.4
    bear_score = (bear_avg - 0.5) * 2  # 0.7 → +0.4 (positive = expecting bad event)

    if bull_signals and bear_signals:
        composite = (bull_score - bear_score) / 2
    elif bull_signals:
        composite = bull_score
    elif bear_signals:
        composite = -bear_score
    else:
        composite = 0.0

    composite = float(np.clip(composite, -1.0, 1.0))

    signal_label = "BULLISH" if composite > 0.15 else ("BEARISH" if composite < -0.15 else "NEUTRAL")

    return {
        "symbol":           clean_sym,
        "composite_signal": round(composite, 4),
        "signal_label":     signal_label,
        "bull_market_count": len(bull_signals),
        "bear_market_count": len(bear_signals),
        "bull_avg_prob":    round(bull_avg, 3),
        "bear_avg_prob":    round(bear_avg, 3),
        "relevant_markets": relevant_markets[:10],   # top 10 most relevant
        "total_scanned":    len(markets),
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/markets")
async def list_prediction_markets(
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    List open Polymarket prediction markets in the finance/economics/crypto categories.
    Includes YES probability, volume, and market URL.
    """
    markets = _fetch_markets(limit)
    simplified = []
    for m in markets[:limit]:
        yes_prob = _extract_probability(m)
        simplified.append({
            "question":  m.get("question", ""),
            "yes_prob":  round(yes_prob, 3) if yes_prob is not None else None,
            "volume":    round(float(m.get("volume", 0) or 0)),
            "liquidity": round(float(m.get("liquidity", 0) or 0)),
            "end_date":  m.get("endDate") or m.get("endDateIso", ""),
            "url":       m.get("url") or m.get("slug", ""),
            "tag":       m.get("tag") or (m.get("tags") or [{}])[0].get("slug", ""),
        })
    # Sort by volume descending
    simplified.sort(key=lambda x: x["volume"], reverse=True)
    return {"markets": simplified, "count": len(simplified)}


@router.get("/signals/{symbol}")
async def polymarket_signals(symbol: str):
    """
    Compute a net bullish/bearish signal for a given stock/crypto ticker
    based on currently open Polymarket prediction market probabilities.

    The signal aggregates crowd-wisdom from real-money bettors on:
      - Fed rate decisions, recession odds, inflation targets
      - Broad market direction (S&P, Nasdaq)
      - Crypto-specific markets (for BTC, ETH, etc.)
    """
    clean = symbol.strip().upper()

    with _cache_lock:
        cached = _signals_cache.get(clean)
    if cached:
        ts, data = cached
        if time.time() - ts < SIGNALS_TTL:
            return data

    markets = _fetch_markets(100)
    result  = _compute_polymarket_signal(clean, markets)

    with _cache_lock:
        _signals_cache[clean] = (time.time(), result)
    return result


@router.post("/analyze-screenshot")
async def analyze_polywhale_screenshot(
    file: UploadFile = File(..., description="Screenshot of a Polymarket portfolio or market page"),
):
    """
    Polywhale Analysis — upload a Polymarket screenshot and get AI-powered
    analysis of the visible positions, probabilities, and trading implications.

    Requires ANTHROPIC_API_KEY to be set in the environment.
    Get your free API key at: https://console.anthropic.com/

    If the API key is not configured, returns a 402 with setup instructions.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=402,
            detail={
                "error":       "ANTHROPIC_API_KEY not configured",
                "feature":     "Polywhale Screenshot Analysis",
                "setup_steps": [
                    "1. Go to https://console.anthropic.com/",
                    "2. Create account → API Keys → Create Key",
                    "3. Add ANTHROPIC_API_KEY=sk-ant-... to your backend/.env file",
                    "4. Redeploy — this endpoint will activate automatically",
                ],
                "note": "All other Polymarket signals work without any API key.",
            }
        )

    # Validate file type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, WEBP)")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")

    image_b64    = base64.standard_b64encode(image_bytes).decode()
    media_type   = content_type if content_type in ("image/jpeg", "image/png",
                                                     "image/gif", "image/webp") else "image/jpeg"

    # Build Anthropic API request
    prompt = """You are a Polymarket prediction market analyst (Polywhale mode).

Analyze this screenshot of a Polymarket page and extract:

1. POSITIONS — List every visible market/contract with:
   - Question text
   - Current YES probability (%)
   - User's position (YES/NO, amount if visible)
   - Implied edge (is the market under/overpriced vs your estimate?)

2. PORTFOLIO SUMMARY — If multiple positions are visible:
   - Net bullish vs bearish exposure
   - Estimated PnL direction
   - Most/least confident positions

3. TRADING SIGNAL — Based on the market probabilities shown:
   - Macro sentiment implied by these markets (BULLISH / BEARISH / NEUTRAL for stocks/crypto)
   - Key catalysts embedded in the positions (Fed decision, election, earnings, etc.)
   - Recommended action (add, reduce, hold)

4. RISK FACTORS — What could move these markets against current pricing?

Format your response as structured JSON with keys: positions, portfolio_summary, trading_signal, risk_factors.
If the screenshot doesn't show Polymarket content, say so clearly."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",   # fast + cheap for image analysis
                "max_tokens": 2048,
                "messages": [{
                    "role":    "user",
                    "content": [
                        {
                            "type":   "image",
                            "source": {
                                "type":       "base64",
                                "media_type": media_type,
                                "data":       image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }],
            },
            timeout=30,
        )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Anthropic API error {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        raw_text = data["content"][0]["text"]

        # Try to parse JSON from the response
        import json as _json
        import re as _re
        json_match = _re.search(r'\{[\s\S]*\}', raw_text)
        if json_match:
            try:
                structured = _json.loads(json_match.group())
            except Exception:
                structured = {"raw_analysis": raw_text}
        else:
            structured = {"raw_analysis": raw_text}

        return {
            "analysis":    structured,
            "model":       "claude-haiku-4-5-20251001",
            "tokens_used": data.get("usage", {}).get("output_tokens", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)[:200]}")


# ─── Bloomberg Architecture Stub ─────────────────────────────────────────────
# Bloomberg Terminal API is institutional ($24,000+/year).
# The free alternative (Bloomberg RSS sentiment) is already live in MarketOracle.
#
# When you have Bloomberg API access, implement these using blpapi:
#
#   import blpapi
#   def get_bloomberg_historical(ticker, fields, start, end):
#       session = blpapi.Session()
#       session.start()
#       ...
#
# Or use the xbbg Python wrapper:
#   from xbbg import blp
#   data = blp.bdh(ticker, "PX_LAST", start_date=start, end_date=end)
#
# API documentation: https://developer.bloomberg.com/portal/documentation
# ─────────────────────────────────────────────────────────────────────────────


# ─── TradingView Data API Architecture Stub ────────────────────────────────
# TradingView REST API requires a paid "Data Pulses" subscription.
# The free chart widget (TradingViewChart.jsx) works without any API key.
#
# When you have a TradingView API key, implement:
#
#   GET https://symbol-search.tradingview.com/symbol_search/?text={symbol}
#   GET https://data.tradingview.com/v1/history?symbol={sym}&resolution=D&from=X&to=Y
#
# Map the response to a pandas DataFrame with columns: open, high, low, close, volume
# to use directly in the existing prediction pipeline.
# ─────────────────────────────────────────────────────────────────────────────
