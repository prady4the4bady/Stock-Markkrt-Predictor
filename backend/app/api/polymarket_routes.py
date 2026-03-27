"""
NexusTrader — Polymarket + Polywhale Integration
==================================================
Endpoints for crowd-wisdom prediction market signals and AI-powered analysis.

Polymarket (FREE — no API key):
  GET  /api/polymarket/signals/{symbol}   — market-implied macro signals for a ticker
  GET  /api/polymarket/markets            — live open prediction markets (finance/econ)

Polywhale (screenshot analysis — requires NVIDIA_API_KEY):
  POST /api/polymarket/analyze-screenshot — upload a Polymarket screenshot,
                                            get structured position analysis via
                                            NVIDIA Llama-3.2-90B Vision (free)

AI Signal Synthesis (requires NVIDIA_API_KEY):
  POST /api/polymarket/ai-synthesize      — feed all MarketOracle signal scores to
                                            NVIDIA Llama-3.1-70B for a human-readable
                                            trading recommendation

NVIDIA NIM Free API (replaces Anthropic):
  1. Go to https://build.nvidia.com/
  2. Create account → "Get API Key" (top-right)
  3. Add NVIDIA_API_KEY=nvapi-... to your backend/.env file
  4. Free tier: generous monthly credits, no credit card required

Bloomberg (PAID — architecture stub):
  Full Bloomberg API integration requires a Bloomberg Terminal licence.
  Free alternative: RSS feed sentiment is already baked into the MarketOracle
  (bloomberg_rss signal layer).  When you have a Bloomberg API key, uncomment
  the BLOOMBERG_API_KEY section in config.py and this module will use it.

TradingView Data API (PAID — architecture stub):
  The free chart widget (TradingViewChart.jsx) works without any API key.
  Paid plan: https://www.tradingview.com/data-pulses/
"""

import os
import base64
import json
import re
import time
import threading
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
import requests
import numpy as np

router = APIRouter(prefix="/api/polymarket", tags=["Polymarket & Polywhale"])

# ─── NVIDIA NIM config ────────────────────────────────────────────────────────
NVIDIA_BASE_URL  = "https://integrate.api.nvidia.com/v1"
VISION_MODEL     = "meta/llama-3.2-90b-vision-instruct"
TEXT_MODEL       = "moonshotai/kimi-k2.5"   # upgraded: chain-of-thought thinking

# ─── In-memory caches ────────────────────────────────────────────────────────
_markets_cache: Optional[List[Dict]] = None
_markets_ts: float = 0.0
_signals_cache: Dict[str, tuple] = {}   # symbol → (ts, data)
_cache_lock = threading.Lock()

MARKETS_TTL = 120   # 2 min (Polymarket prices update frequently)
SIGNALS_TTL = 300   # 5 min

POLYMARKET_BASE = "https://gamma-api.polymarket.com"


# ─── NVIDIA NIM helper ────────────────────────────────────────────────────────

def _nvidia_api_key() -> str:
    """Return NVIDIA API key or raise a helpful 402 error."""
    key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=402,
            detail={
                "error":       "NVIDIA_API_KEY not configured",
                "feature":     "AI-powered analysis (Polywhale + Signal Synthesis)",
                "setup_steps": [
                    "1. Go to https://build.nvidia.com/",
                    "2. Create a free account",
                    "3. Click 'Get API Key' (top-right corner)",
                    "4. Add NVIDIA_API_KEY=nvapi-... to your backend/.env file",
                    "5. Redeploy — both AI endpoints will activate automatically",
                ],
                "note": (
                    "Free tier gives generous monthly credits. "
                    "All Polymarket signals work without any API key."
                ),
            }
        )
    return key


def _nvidia_chat(messages: list, model: str, api_key: str,
                 max_tokens: int = 2048, temperature: float = 0.3,
                 thinking: bool = False) -> str:
    """Call NVIDIA NIM's OpenAI-compatible chat endpoint."""
    payload: dict = {
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "top_p":       1.0,
    }
    if thinking:
        payload["chat_template_kwargs"] = {"thinking": True}

    resp = requests.post(
        f"{NVIDIA_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"NVIDIA API error {resp.status_code}: {resp.text[:300]}"
        )
    content = resp.json()["choices"][0]["message"]["content"]
    # Strip any exposed <think>…</think> blocks
    import re as _re
    content = _re.sub(r"<think>[\s\S]*?</think>", "", content, flags=_re.IGNORECASE).strip()
    return content


# ─── Polymarket helpers ───────────────────────────────────────────────────────

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
    seen, unique = set(), []
    for m in all_markets:
        mid = m.get("id") or m.get("conditionId", "")
        if mid not in seen:
            seen.add(mid)
            unique.append(m)

    with _cache_lock:
        _markets_cache = unique
        _markets_ts    = time.time()
    return unique


def _extract_probability(market: Dict) -> Optional[float]:
    """Extract YES probability (0–1) from a market object."""
    try:
        prices = market.get("outcomePrices") or []
        if prices:
            return float(prices[0])
        best_bid = market.get("bestBid")
        best_ask = market.get("bestAsk")
        if best_bid and best_ask:
            return (float(best_bid) + float(best_ask)) / 2
    except (TypeError, ValueError, IndexError):
        pass
    return None


def _question_signal(question: str, yes_prob: float, symbol: str) -> Optional[tuple]:
    """
    Map a Polymarket question + YES probability → (bull_bear, weight) signal.
    Returns ('bull', weight), ('bear', weight), or None.
    """
    q = question.lower()
    is_crypto = "/" in symbol or symbol in {
        "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"
    }

    # Fed / interest rates
    if any(kw in q for kw in ("rate cut", "cut rates", "reduce rates", "dovish", "pivot")):
        return ("bull", yes_prob)
    if any(kw in q for kw in ("rate hike", "raise rates", "increase rates", "hawkish")):
        return ("bear", yes_prob)

    # Recession / economy
    if "recession" in q and not any(kw in q for kw in ("avoid", "no recession", "soft landing")):
        return ("bear", yes_prob)
    if any(kw in q for kw in ("soft landing", "no recession", "avoid recession")):
        return ("bull", yes_prob)

    # Broad market direction
    if any(idx in q for idx in ("s&p 500", "s&p500", "nasdaq", "dow jones", "stock market")):
        if any(kw in q for kw in ("above", "higher", "reach", "exceed", "record", "rally")):
            return ("bull", yes_prob * 0.8)
        if any(kw in q for kw in ("below", "lower", "crash", "fall", "correction", "bear")):
            return ("bear", yes_prob * 0.8)

    # Crypto-specific
    if is_crypto:
        sym_lower = symbol.split("/")[0].lower()
        keywords  = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH",
                     "eth": "ETH", "crypto": "*", sym_lower: symbol}
        if any(kw in q for kw in keywords):
            if any(kw in q for kw in ("above", "higher", "reach", "hit", "exceed", "ath")):
                return ("bull", yes_prob * 0.6)
            if any(kw in q for kw in ("below", "lower", "crash", "fall", "dump")):
                return ("bear", yes_prob * 0.6)

    # Inflation
    if "inflation" in q:
        if any(kw in q for kw in ("above", "exceed", "rise", "higher")):
            return ("bear", yes_prob * 0.5)
        if any(kw in q for kw in ("below", "fall", "lower", "target")):
            return ("bull", yes_prob * 0.5)

    return None


def _compute_polymarket_signal(symbol: str, markets: List[Dict]) -> Dict:
    """Convert Polymarket market list into a net signal for the given symbol."""
    bull_signals, bear_signals, relevant_markets = [], [], []
    clean_sym = symbol.split("/")[0].upper()

    for market in markets:
        question = market.get("question", "")
        if not question:
            continue
        yes_prob = _extract_probability(market)
        if yes_prob is None:
            continue

        volume  = float(market.get("volume", 0) or 0)
        weight  = min(1.5, 0.5 + volume / 1_000_000)
        result  = _question_signal(question, yes_prob, clean_sym)
        if result is None:
            continue

        direction, prob = result
        weighted_prob   = prob * weight

        if direction == "bull":
            bull_signals.append((yes_prob, weighted_prob))
        else:
            bear_signals.append((yes_prob, weighted_prob))

        relevant_markets.append({
            "question":  question,
            "direction": direction,
            "yes_prob":  round(yes_prob, 3),
            "volume":    round(volume),
            "url":       market.get("url") or market.get("slug", ""),
        })

    def wavg(signals):
        if not signals:
            return 0.5
        total_w = sum(w for _, w in signals) or 1e-9
        return sum(p * w for p, w in signals) / total_w

    bull_avg   = wavg(bull_signals)
    bear_avg   = wavg(bear_signals)
    bull_score = (bull_avg - 0.5) * 2
    bear_score = (bear_avg - 0.5) * 2

    if bull_signals and bear_signals:
        composite = (bull_score - bear_score) / 2
    elif bull_signals:
        composite = bull_score
    elif bear_signals:
        composite = -bear_score
    else:
        composite = 0.0

    composite = float(np.clip(composite, -1.0, 1.0))
    signal_label = (
        "BULLISH" if composite > 0.15
        else "BEARISH" if composite < -0.15
        else "NEUTRAL"
    )

    return {
        "symbol":            clean_sym,
        "composite_signal":  round(composite, 4),
        "signal_label":      signal_label,
        "bull_market_count": len(bull_signals),
        "bear_market_count": len(bear_signals),
        "bull_avg_prob":     round(bull_avg, 3),
        "bear_avg_prob":     round(bear_avg, 3),
        "relevant_markets":  relevant_markets[:10],
        "total_scanned":     len(markets),
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/markets")
async def list_prediction_markets(limit: int = Query(default=50, ge=1, le=200)):
    """
    List open Polymarket prediction markets in the finance/economics/crypto categories.
    Includes YES probability, volume, and market URL.  FREE — no API key needed.
    """
    markets    = _fetch_markets(limit)
    simplified = []
    for m in markets[:limit]:
        yes_prob = _extract_probability(m)
        simplified.append({
            "question":  m.get("question", ""),
            "yes_prob":  round(yes_prob, 3) if yes_prob is not None else None,
            "volume":    round(float(m.get("volume",    0) or 0)),
            "liquidity": round(float(m.get("liquidity", 0) or 0)),
            "end_date":  m.get("endDate") or m.get("endDateIso", ""),
            "url":       m.get("url") or m.get("slug", ""),
            "tag":       m.get("tag") or (m.get("tags") or [{}])[0].get("slug", ""),
        })
    simplified.sort(key=lambda x: x["volume"], reverse=True)
    return {"markets": simplified, "count": len(simplified)}


@router.get("/signals/{symbol}")
async def polymarket_signals(symbol: str):
    """
    Compute a net bullish/bearish signal for a given stock/crypto ticker
    based on currently open Polymarket prediction market probabilities.
    FREE — no API key required.
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
    position analysis using NVIDIA Llama-3.2-90B Vision (free).

    Requires NVIDIA_API_KEY.  Get a free key at https://build.nvidia.com/
    If not configured, returns 402 with setup instructions.
    """
    api_key = _nvidia_api_key()

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, WEBP)")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")

    image_b64  = base64.standard_b64encode(image_bytes).decode()
    media_type = (content_type
                  if content_type in ("image/jpeg", "image/png", "image/gif", "image/webp")
                  else "image/jpeg")

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
   - Macro sentiment implied (BULLISH / BEARISH / NEUTRAL for stocks/crypto)
   - Key catalysts embedded in the positions
   - Recommended action (add, reduce, hold)

4. RISK FACTORS — What could move these markets against current pricing?

Format your response as structured JSON with keys:
positions, portfolio_summary, trading_signal, risk_factors.
If the screenshot doesn't show Polymarket content, say so clearly."""

    try:
        raw_text = _nvidia_chat(
            messages=[{
                "role":    "user",
                "content": [
                    {
                        "type":      "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
            model=VISION_MODEL,
            api_key=api_key,
            max_tokens=2048,
            temperature=0.2,
        )

        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if json_match:
            try:
                structured = json.loads(json_match.group())
            except Exception:
                structured = {"raw_analysis": raw_text}
        else:
            structured = {"raw_analysis": raw_text}

        return {
            "analysis": structured,
            "model":    VISION_MODEL,
            "provider": "NVIDIA NIM",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)[:200]}")


@router.post("/ai-synthesize")
async def ai_synthesize_signals(body: dict):
    """
    AI Signal Synthesis — feed all MarketOracle signal layer scores to
    NVIDIA Llama-3.1-70B and receive a concise, human-readable trading
    recommendation with reasoning.

    Request body:
      {
        "symbol":   "AAPL",
        "signals":  { "macro": 0.62, "barebone_ta": 0.78, ... },
        "confidence": 84.5,
        "prediction_direction": "UP",
        "asset_type": "stock"   // optional
      }

    Requires NVIDIA_API_KEY.  Get a free key at https://build.nvidia.com/
    """
    api_key = _nvidia_api_key()

    symbol    = body.get("symbol", "UNKNOWN").upper()
    signals   = body.get("signals", {})
    conf      = body.get("confidence", 0)
    direction = body.get("prediction_direction", "UNKNOWN")
    atype     = body.get("asset_type", "stock")

    if not signals:
        raise HTTPException(status_code=400, detail="'signals' dict is required")

    # Format signals table for the LLM
    signals_str = "\n".join(
        f"  {k:25s}: {v:+.4f}" for k, v in sorted(signals.items(), key=lambda x: -abs(x[1]))
    )

    prompt = f"""You are a professional quantitative analyst reviewing AI signal output for {symbol} ({atype}).

The NexusTrader ML ensemble has generated the following 17 signal-layer scores
(scale: -1.0 = strongly bearish, 0.0 = neutral, +1.0 = strongly bullish):

{signals_str}

Overall model confidence: {conf:.1f}%
Price direction prediction: {direction}

Provide a concise trading brief (4–6 sentences) covering:
1. The strongest confirming signals and what they mean
2. Any notable conflicting signals and why they could be ignored or watched
3. One specific risk to monitor
4. Final actionable stance (BUY / SELL / HOLD / WATCH) with a clear reason

Be direct, specific, and data-driven. Avoid generic statements.
Do NOT repeat all the numbers — synthesize them into insight.
Respond in plain prose, no bullet points, no headers."""

    try:
        recommendation = _nvidia_chat(
            messages=[
                {
                    "role":    "system",
                    "content": (
                        "You are a concise, data-driven quant analyst. "
                        "You give specific, actionable insights from signal data. "
                        "No fluff, no disclaimers, no 'not financial advice'."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            model=TEXT_MODEL,
            api_key=api_key,
            max_tokens=1024,
            temperature=0.35,
            thinking=True,   # Kimi K2.5 — reason before answering
        )

        return {
            "symbol":         symbol,
            "recommendation": recommendation.strip(),
            "model":          TEXT_MODEL,
            "provider":       "NVIDIA NIM",
            "signals_used":   len(signals),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)[:200]}")


# ─── Bloomberg Architecture Stub ─────────────────────────────────────────────
# Bloomberg Terminal API is institutional ($24,000+/year).
# The free alternative (Bloomberg RSS sentiment) is already live in MarketOracle.
#
# When you have Bloomberg API access, implement these using blpapi:
#   import blpapi
#   def get_bloomberg_historical(ticker, fields, start, end): ...
#
# Or use the xbbg Python wrapper:
#   from xbbg import blp
#   data = blp.bdh(ticker, "PX_LAST", start_date=start, end_date=end)
#
# API documentation: https://developer.bloomberg.com/portal/documentation
# ─────────────────────────────────────────────────────────────────────────────

# ─── TradingView Data API Architecture Stub ───────────────────────────────────
# TradingView REST API requires a paid "Data Pulses" subscription.
# The free chart widget (TradingViewChart.jsx) works without any API key.
#
# When you have a TradingView API key:
#   GET https://data.tradingview.com/v1/history?symbol={sym}&resolution=D&from=X&to=Y
# Map the response to a pandas DataFrame: open, high, low, close, volume
# ─────────────────────────────────────────────────────────────────────────────
