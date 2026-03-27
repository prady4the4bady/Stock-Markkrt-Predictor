"""
NexusTrader — NVIDIA Kimi K2.5 Analyst
========================================
Centralized NVIDIA NIM interface using moonshotai/kimi-k2.5 with chain-of-thought
thinking for high-quality financial analysis across the entire prediction pipeline.

The thinking mode (chat_template_kwargs={"thinking": True}) enables the model to
reason step-by-step internally before generating its final answer — analogous to
Claude's extended thinking or o1's reasoning tokens.

This module provides three capabilities:
  1. generate_prediction_brief() — trading narrative for a completed prediction
  2. kimi_meta_score()           — [-1,+1] meta-signal from all 17 oracle layers
  3. enhance_news_sentiment()    — deeper headline analysis beyond keyword matching

Performance contract:
  All public functions use a background-cache pattern. The first call starts a
  daemon thread and returns None immediately (no added latency). Every call within
  the TTL window returns the cached result instantly. This means prediction
  endpoints are NEVER blocked by the Kimi API round-trip (~5-8 s).

Setup:
  Add NVIDIA_API_KEY=nvapi-... to your backend/.env file.
  Get a free key at https://build.nvidia.com/
"""

import os
import re
import time
import threading
import requests
from typing import Optional, Dict, Any

# ─── NVIDIA NIM config ────────────────────────────────────────────────────────
NVIDIA_BASE  = "https://integrate.api.nvidia.com/v1"
KIMI_MODEL   = "moonshotai/kimi-k2.5"
VISION_MODEL = "meta/llama-3.2-90b-vision-instruct"  # used in polymarket_routes

# ─── In-memory caches ────────────────────────────────────────────────────────
_brief_cache:  Dict[str, tuple] = {}   # symbol → (ts, brief_str)
_meta_cache:   Dict[str, tuple] = {}   # symbol → (ts, score_float)
_news_cache:   Dict[str, tuple] = {}   # symbol → (ts, sentiment_str)
_lock = threading.Lock()

BRIEF_TTL = 600    # 10 min — re-generate brief when prediction changes
META_TTL  = 600    # 10 min — re-score kimi_meta every 10 min
NEWS_TTL  = 300    # 5 min  — news changes faster


def _api_key() -> Optional[str]:
    return os.getenv("NVIDIA_API_KEY", "").strip() or None


def _kimi_complete(
    messages: list,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    thinking: bool = True,
) -> Optional[str]:
    """
    Call Kimi K2.5 with optional chain-of-thought thinking.
    Returns the response text, or None on any failure.
    Never raises — designed to degrade gracefully.
    """
    key = _api_key()
    if not key:
        return None
    try:
        payload: Dict[str, Any] = {
            "model":       KIMI_MODEL,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "top_p":       1.0,
        }
        if thinking:
            payload["chat_template_kwargs"] = {"thinking": True}

        resp = requests.post(
            f"{NVIDIA_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type":  "application/json",
            },
            json=payload,
            timeout=60,
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            # Strip any exposed <think>…</think> blocks from the output
            content = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()
            return content
    except Exception as e:
        print(f"[Kimi] API call failed: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Prediction Brief
# ─────────────────────────────────────────────────────────────────────────────

def _build_brief_prompt(symbol: str, prediction: dict) -> str:
    price     = prediction.get("current_price", 0)
    conf      = prediction.get("confidence", 0)
    analysis  = prediction.get("analysis", {})
    trend     = analysis.get("trend", "unknown")
    high      = analysis.get("predicted_high", 0)
    low       = analysis.get("predicted_low", 0)
    vol       = analysis.get("volatility", "unknown")
    oracle    = prediction.get("oracle_signals") or analysis.get("oracle_signals") or {}
    direction = "UP" if (oracle.get("direction", 0) or 0) >= 0 else "DOWN"
    news      = prediction.get("news_sentiment") or {}
    headlines = "; ".join(
        h.get("title", "") for h in (news.get("headlines") or [])[:3]
        if h.get("title")
    )
    signals_str = ""
    if oracle.get("signals"):
        top_signals = sorted(
            oracle["signals"].items(), key=lambda x: -abs(x[1])
        )[:8]
        signals_str = "\n".join(f"  {k}: {v:+.3f}" for k, v in top_signals)

    return f"""You are a senior quantitative analyst. Generate a concise trading brief for {symbol}.

PREDICTION DATA:
  Current price:  ${price:,.2f}
  Direction call: {direction}  |  Trend: {trend}
  Predicted high: ${high:,.2f}  |  Predicted low: ${low:,.2f}
  Volatility:     {vol}
  Ensemble confidence: {conf:.1f}%

TOP SIGNAL SCORES (scale -1 to +1):
{signals_str if signals_str else "  (not available)"}

RECENT NEWS:
  {headlines if headlines else "No recent headlines available."}

Write a 4-sentence trading brief covering:
1. What the strongest confirming signals say and why they matter
2. Any notable risk or conflicting signal to watch
3. Key price levels (support/resistance from high-low range)
4. Final actionable stance: BUY / SELL / HOLD / WATCH with one clear reason

Be direct and specific. No disclaimers. No bullet points. Plain prose only."""


def _generate_brief_sync(symbol: str, prediction: dict) -> None:
    """Background worker: generate brief and populate cache."""
    text = _kimi_complete(
        messages=[
            {
                "role":    "system",
                "content": (
                    "You are a concise quantitative trading analyst. "
                    "Write in the style of a Goldman Sachs morning brief. "
                    "No fluff, no generic disclaimers. Pure insight."
                ),
            },
            {"role": "user", "content": _build_brief_prompt(symbol, prediction)},
        ],
        max_tokens=512,
        temperature=0.35,
        thinking=True,
    )
    if text:
        with _lock:
            _brief_cache[symbol] = (time.time(), text)
        print(f"[Kimi] Brief generated for {symbol} ({len(text)} chars)")


def get_cached_brief(symbol: str) -> Optional[str]:
    """Return a cached trading brief, or None if not yet available."""
    with _lock:
        cached = _brief_cache.get(symbol)
    if cached:
        ts, text = cached
        if time.time() - ts < BRIEF_TTL:
            return text
    return None


def start_brief_generation(symbol: str, prediction: dict) -> None:
    """
    Kick off non-blocking brief generation in the background.
    Returns immediately — the brief will be available in ~5-8 s.
    """
    if not _api_key():
        return
    # Avoid duplicate concurrent calls for the same symbol
    with _lock:
        cached = _brief_cache.get(symbol)
    if cached and time.time() - cached[0] < BRIEF_TTL:
        return  # Already fresh

    t = threading.Thread(
        target=_generate_brief_sync,
        args=(symbol, prediction),
        daemon=True,
        name=f"KimiBrief-{symbol}",
    )
    t.start()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Kimi Meta-Signal (for MarketOracle)
# ─────────────────────────────────────────────────────────────────────────────

def _score_from_kimi(symbol: str, signal_scores: Dict[str, float]) -> None:
    """Background worker: run Kimi meta-reasoning and cache the [-1,+1] score."""
    if not signal_scores:
        return

    scores_str = "\n".join(
        f"  {k:25s}: {v:+.4f}"
        for k, v in sorted(signal_scores.items(), key=lambda x: -abs(x[1]))
    )
    prompt = f"""You are analyzing {symbol} using 17 quantitative signal layers.
Each score is on a scale from -1.0 (strongly bearish) to +1.0 (strongly bullish):

{scores_str}

Based on your chain-of-thought reasoning about these signals:
- Which signals are most reliable and meaningful?
- Are there any contradictions that reduce confidence?
- What is the net directional bias when weighing signal quality and context?

Respond with ONLY a single number between -1.0 and +1.0 representing your
reasoned meta-assessment. Nothing else. No explanation. Just the number."""

    text = _kimi_complete(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=16,
        temperature=0.1,
        thinking=True,
    )
    if text:
        try:
            # Extract first float from response
            match = re.search(r"-?\d+\.?\d*", text.strip())
            if match:
                score = float(match.group())
                score = max(-1.0, min(1.0, score))
                with _lock:
                    _meta_cache[symbol] = (time.time(), score)
                print(f"[Kimi] Meta-score for {symbol}: {score:+.4f}")
        except Exception:
            pass


def get_kimi_meta_score(symbol: str, signal_scores: Dict[str, float]) -> float:
    """
    Return Kimi's meta-signal score for a symbol.
    - If cache is warm: returns the cached score immediately.
    - If cache is cold: starts background computation, returns 0.0 (neutral) now.
    The next prediction call (within ~10 s) will have the real Kimi score.
    """
    with _lock:
        cached = _meta_cache.get(symbol)
    if cached:
        ts, score = cached
        if time.time() - ts < META_TTL:
            return score

    # Start background Kimi reasoning
    if _api_key() and signal_scores:
        t = threading.Thread(
            target=_score_from_kimi,
            args=(symbol, dict(signal_scores)),
            daemon=True,
            name=f"KimiMeta-{symbol}",
        )
        t.start()

    return 0.0  # neutral placeholder until Kimi responds


# ─────────────────────────────────────────────────────────────────────────────
# 3. Enhanced News Sentiment
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_news_sync(symbol: str, headlines: list) -> None:
    """Background: use Kimi to score news sentiment beyond keyword matching."""
    if not headlines:
        return
    hl_str = "\n".join(f"  - {h}" for h in headlines[:10])
    prompt = f"""Rate the net market sentiment for {symbol} based on these news headlines:

{hl_str}

Consider: earnings impact, macro implications, sector rotation, short-term vs long-term effects.
Respond with ONLY a JSON object: {{"score": <-1.0 to +1.0>, "label": "<BULLISH|BEARISH|NEUTRAL>", "key_theme": "<10-word summary>"}}"""

    text = _kimi_complete(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0.2,
        thinking=False,  # Fast path — no thinking needed for simple scoring
    )
    if text:
        import json as _json
        try:
            m = re.search(r"\{[\s\S]*?\}", text)
            if m:
                data = _json.loads(m.group())
                with _lock:
                    _news_cache[symbol] = (time.time(), data)
                print(f"[Kimi] News sentiment for {symbol}: {data}")
        except Exception:
            pass


def get_kimi_news_sentiment(symbol: str, headlines: list) -> Optional[dict]:
    """
    Return Kimi-enhanced news sentiment.
    Background-cache pattern — returns None on first call, dict on subsequent calls.
    """
    with _lock:
        cached = _news_cache.get(symbol)
    if cached:
        ts, data = cached
        if time.time() - ts < NEWS_TTL:
            return data

    if _api_key() and headlines:
        t = threading.Thread(
            target=_analyze_news_sync,
            args=(symbol, headlines),
            daemon=True,
            name=f"KimiNews-{symbol}",
        )
        t.start()

    return None
