"""
NexusTrader — Model Council
============================
Meta-ensemble that queries 12 NVIDIA NIM models in parallel, collects
directional votes (UP / DOWN / HOLD), and produces a weighted consensus score.

All models are called via the NVIDIA NIM chat-completions endpoint using the
plain requests library. Requires NVIDIA_API_KEY env var.
"""

import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Council model roster
# ─────────────────────────────────────────────────────────────────────────────
COUNCIL_MODELS: List[Dict] = [
    # Tier 1 — Reasoning/Thinking (highest weight)
    {
        "id": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "short_name": "Nemotron-Ultra",
        "weight": 0.14,
        "thinking": True,
        "thinking_kwargs": {"thinking": True},
        "reasoning_budget": None,
        "temperature": 0.4,
        "max_tokens": 256,
    },
    {
        "id": "moonshotai/kimi-k2.5",
        "short_name": "Kimi K2.5",
        "weight": 0.13,
        "thinking": True,
        "thinking_kwargs": {"thinking": True},
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 256,
    },
    {
        "id": "deepseek-ai/deepseek-r1",
        "short_name": "DeepSeek-R1",
        "weight": 0.12,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 256,
    },
    {
        "id": "qwen/qwq-32b",
        "short_name": "QwQ-32B",
        "weight": 0.11,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 256,
    },
    # Tier 2 — Large models
    {
        "id": "nvidia/nemotron-3-super-120b-a12b",
        "short_name": "Nemotron-120B",
        "weight": 0.10,
        "thinking": True,
        "thinking_kwargs": {"enable_thinking": True},
        "reasoning_budget": 4096,
        "temperature": 0.6,
        "max_tokens": 256,
    },
    {
        "id": "microsoft/phi-4-reasoning-plus",
        "short_name": "Phi-4-Reasoning",
        "weight": 0.09,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 256,
    },
    {
        "id": "meta/llama-4-maverick-17b-128e-instruct",
        "short_name": "Llama4-Maverick",
        "weight": 0.09,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 256,
    },
    {
        "id": "minimaxai/minimax-m2.5",
        "short_name": "MiniMax M2.5",
        "weight": 0.08,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 256,
    },
    # Tier 3 — Specialist models
    {
        "id": "z-ai/glm5",
        "short_name": "GLM5",
        "weight": 0.06,
        "thinking": True,
        "thinking_kwargs": {"enable_thinking": True, "clear_thinking": True},
        "reasoning_budget": None,
        "temperature": 0.5,
        "max_tokens": 256,
    },
    {
        "id": "baidu/ernie-4.5-300b-a47b",
        "short_name": "ERNIE-4.5",
        "weight": 0.03,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 128,
    },
    {
        "id": "google/gemma-3-27b-it",
        "short_name": "Gemma-3-27B",
        "weight": 0.03,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.3,
        "max_tokens": 128,
    },
    {
        "id": "meta/llama-3.3-70b-instruct",
        "short_name": "Llama 70B",
        "weight": 0.02,
        "thinking": False,
        "thinking_kwargs": None,
        "reasoning_budget": None,
        "temperature": 0.2,
        "max_tokens": 128,
    },
]

_NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# ─────────────────────────────────────────────────────────────────────────────
# Module-level state
# ─────────────────────────────────────────────────────────────────────────────
_council_cache: Dict[str, Dict] = {}   # symbol → result dict
_council_ts: Dict[str, float] = {}     # symbol → epoch timestamp
_council_lock = threading.Lock()
_COUNCIL_TTL = 900  # 15 minutes


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _call_model(model_cfg: Dict, messages: List[Dict], api_key: str) -> Optional[str]:
    """
    POST to NVIDIA NIM chat-completions endpoint for one model.
    Returns the assistant text content (with <think>...</think> stripped) or None.
    """
    import requests as _requests

    payload: Dict = {
        "model": model_cfg["id"],
        "messages": messages,
        "temperature": model_cfg["temperature"],
        "max_tokens": model_cfg["max_tokens"],
        "stream": False,
    }

    # Thinking models — add chat_template_kwargs and optional reasoning_budget
    if model_cfg.get("thinking") and model_cfg.get("thinking_kwargs"):
        payload["chat_template_kwargs"] = model_cfg["thinking_kwargs"]
        if model_cfg.get("reasoning_budget"):
            payload["reasoning_budget"] = model_cfg["reasoning_budget"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        resp = _requests.post(_NVIDIA_API_URL, json=payload, headers=headers, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Strip <think>...</think> blocks (reasoning traces)
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        return content.strip() or None
    except Exception as e:
        print(f"[Council/{model_cfg['short_name']}] call failed: {e}")
        return None


def _parse_vote(content: str) -> Optional[Tuple[str, float]]:
    """
    Parse model response in format:
        DIRECTION: UP
        CONFIDENCE: 78
    Returns (direction, confidence_0_to_1) or None on parse failure.
    """
    if not content:
        return None
    try:
        direction = None
        confidence = 0.5

        for line in content.upper().splitlines():
            line = line.strip()
            if line.startswith("DIRECTION:"):
                raw_dir = line.split(":", 1)[1].strip()
                if "UP" in raw_dir or "BULL" in raw_dir or "BUY" in raw_dir:
                    direction = "UP"
                elif "DOWN" in raw_dir or "BEAR" in raw_dir or "SELL" in raw_dir:
                    direction = "DOWN"
                elif "HOLD" in raw_dir or "NEUTRAL" in raw_dir or "SIDE" in raw_dir:
                    direction = "HOLD"
            elif line.startswith("CONFIDENCE:"):
                raw_conf = re.sub(r"[^0-9.]", "", line.split(":", 1)[1].strip())
                if raw_conf:
                    val = float(raw_conf)
                    # Accept both 0-1 and 0-100 scales
                    confidence = val / 100.0 if val > 1.0 else val
                    confidence = max(0.0, min(1.0, confidence))

        if direction is None:
            # Fallback: scan for UP/DOWN/HOLD anywhere in the first 200 chars
            snippet = content[:200].upper()
            if re.search(r"\bUP\b|\bBULLISH\b|\bBUY\b", snippet):
                direction = "UP"
            elif re.search(r"\bDOWN\b|\bBEARISH\b|\bSELL\b", snippet):
                direction = "DOWN"
            elif re.search(r"\bHOLD\b|\bNEUTRAL\b|\bSIDEWAYS\b", snippet):
                direction = "HOLD"

        if direction is None:
            return None

        return (direction, confidence)
    except Exception:
        return None


# ── Diverse trader personas (MiroFish swarm intelligence concept) ─────────
# Each council model gets a different persona, leading to genuinely diverse
# opinions instead of 12 models all answering the same generic prompt.
_TRADER_PERSONAS: List[str] = [
    # Tier 1 — heavyweight reasoning models get hardest personas
    "You are a macro-quant portfolio manager. Focus on macro signals (VIX, yields, DXY, oil), cross-asset correlations, and regime detection.",
    "You are a momentum day-trader. Focus on short-term price action, RSI, MACD momentum, and volume surges. Ignore long-term fundamentals.",
    "You are a risk-averse value investor. Focus on fundamentals (P/E, revenue growth, margins), analyst consensus, and downside protection.",
    "You are a contrarian hedge fund manager. Look for crowded trades, extreme sentiment, mean-reversion setups, and positions that the majority is wrong about.",
    # Tier 2 — large models
    "You are a systematic trend-follower. Focus on SMA crossovers, trend strength, breakout patterns, and ignore noise. Only trade confirmed trends.",
    "You are an options market-maker. Focus on implied volatility, put/call ratios, gamma exposure, and options flow for directional clues.",
    "You are a global macro strategist. Focus on cross-asset signals, sector rotation, fear & greed index, and geopolitical risk factors.",
    "You are a quantitative statistician. Focus purely on statistical patterns: z-scores, mean reversion probability, and Bayesian confidence intervals.",
    # Tier 3 — specialist models
    "You are a sentiment analyst. Focus on social buzz, Google Trends, news sentiment, and crowd psychology indicators.",
    "You are a technical chartist. Focus on chart patterns (head & shoulders, wedges, channels), support/resistance levels, and price action.",
    "You are an earnings specialist. Focus on earnings catalysts, revision trends, whisper numbers, and sector seasonality.",
    "You are a crypto/altcoin trader. Focus on on-chain metrics, exchange flows, funding rates, and crypto-specific momentum.",
]


def _build_prompt(symbol: str, signal_scores: Dict[str, float],
                  current_price: float, confidence: float,
                  ml_direction: str,
                  persona_index: int = 0) -> List[Dict]:
    """
    Build a compact system+user prompt (target <300 tokens).
    Each model gets a unique trader persona for diverse opinions.
    """
    # Summarise signal scores compactly
    sig_lines = []
    for k, v in list(signal_scores.items())[:12]:  # cap at 12 signals
        sig_lines.append(f"  {k}: {v:+.2f}")
    sig_summary = "\n".join(sig_lines) if sig_lines else "  (none available)"

    persona = _TRADER_PERSONAS[persona_index % len(_TRADER_PERSONAS)]

    system_msg = (
        f"{persona} "
        "Respond ONLY in this exact format (no extra text):\n"
        "DIRECTION: UP\n"
        "CONFIDENCE: 75\n"
        "REASON: one sentence max"
    )

    user_msg = (
        f"Symbol: {symbol}\n"
        f"Price: {current_price:.4g}\n"
        f"ML model direction: {ml_direction} ({confidence:.0f}% confidence)\n"
        f"Signal scores (-1=bearish, +1=bullish):\n{sig_summary}\n\n"
        "Give your DIRECTION (UP/DOWN/HOLD), CONFIDENCE (0-100), and REASON."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def _run_council_sync(symbol: str, signal_scores: Dict[str, float],
                      current_price: float, confidence: float,
                      ml_direction: str) -> None:
    """
    Query all 12 council models in parallel with diverse trader personas,
    aggregate weighted votes, store in cache.
    Called in a daemon thread — never blocks the request path.
    """
    api_key = os.getenv("NVIDIA_API_KEY", "")
    if not api_key:
        print("[Council] NVIDIA_API_KEY not set — skipping council run")
        return

    # ── Query all models in parallel (each with a unique trader persona) ─────
    raw_votes: List[Dict] = []
    with ThreadPoolExecutor(max_workers=12, thread_name_prefix="council") as pool:
        future_to_model = {}
        for idx, m in enumerate(COUNCIL_MODELS):
            messages = _build_prompt(symbol, signal_scores, current_price,
                                     confidence, ml_direction, persona_index=idx)
            future_to_model[pool.submit(_call_model, m, messages, api_key)] = m
        for future in as_completed(future_to_model, timeout=45):
            model_cfg = future_to_model[future]
            try:
                content = future.result(timeout=30)
                parsed = _parse_vote(content)
                if parsed:
                    direction, conf = parsed
                    raw_votes.append({
                        "model": model_cfg["short_name"],
                        "direction": direction,
                        "confidence": conf,
                        "weight": model_cfg["weight"],
                    })
            except (FuturesTimeoutError, Exception) as e:
                print(f"[Council/{model_cfg['short_name']}] vote failed: {e}")

    if not raw_votes:
        return

    # ── Aggregate weighted votes ───────────────────────────────────────────────
    composite = 0.0
    vote_counts: Dict[str, int] = {"UP": 0, "DOWN": 0, "HOLD": 0}

    for vote in raw_votes:
        d = vote["direction"]
        w = vote["weight"]
        c = vote["confidence"]
        score = w * c
        if d == "UP":
            composite += score
            vote_counts["UP"] += 1
        elif d == "DOWN":
            composite -= score
            vote_counts["DOWN"] += 1
        else:
            vote_counts["HOLD"] += 1

    # Normalise composite to [-1, +1]
    composite = max(-1.0, min(1.0, composite))

    total_votes = sum(vote_counts.values())
    max_votes = max(vote_counts.values()) if total_votes > 0 else 0
    agreement = (max_votes / total_votes * 100) if total_votes > 0 else 0.0

    if composite > 0.15:
        verdict = "BULLISH"
    elif composite < -0.15:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    result = {
        "composite": round(composite, 4),
        "verdict": verdict,
        "agreement": round(agreement, 1),
        "votes": [
            {
                "model": v["model"],
                "direction": v["direction"],
                "confidence": round(v["confidence"], 3),
            }
            for v in raw_votes
        ],
        "model_count": len(raw_votes),
    }

    with _council_lock:
        _council_cache[symbol] = result
        _council_ts[symbol] = time.time()

    print(f"[Council] {symbol} → {verdict} composite={composite:+.3f} "
          f"agreement={agreement:.0f}% ({len(raw_votes)}/12 models)")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_council_score(symbol: str, signal_scores: Dict[str, float],
                      current_price: float = 0, confidence: float = 0,
                      ml_direction: str = "UP") -> float:
    """
    Return the cached council composite score for *symbol* as a float in [-1, +1].

    On cache miss (or TTL expiry) returns 0.0 immediately and spawns a daemon
    thread to populate the cache for the next call.
    """
    with _council_lock:
        ts = _council_ts.get(symbol, 0)
        cached = _council_cache.get(symbol)

    if cached is not None and (time.time() - ts) < _COUNCIL_TTL:
        return cached["composite"]

    # Cache miss — warm in background
    t = threading.Thread(
        target=_run_council_sync,
        args=(symbol, signal_scores, current_price, confidence, ml_direction),
        daemon=True,
        name=f"council-{symbol}",
    )
    t.start()
    return 0.0


def get_council_score_blocking(symbol: str, signal_scores: Dict[str, float],
                               current_price: float = 0, confidence: float = 0,
                               ml_direction: str = "UP",
                               timeout: float = 10.0) -> float:
    """
    Like get_council_score but WAITS up to `timeout` seconds for the result
    instead of returning 0.0 immediately. Used by quick_predict so the first
    prediction for a symbol includes real council consensus.

    Falls back to 0.0 if NVIDIA_API_KEY is missing or timeout expires.
    """
    api_key = os.getenv("NVIDIA_API_KEY", "")
    if not api_key:
        return 0.0

    # Check cache first
    with _council_lock:
        ts = _council_ts.get(symbol, 0)
        cached = _council_cache.get(symbol)
    if cached is not None and (time.time() - ts) < _COUNCIL_TTL:
        return cached["composite"]

    # Run council in a thread and wait
    done_event = threading.Event()

    def _run_and_signal():
        _run_council_sync(symbol, signal_scores, current_price, confidence, ml_direction)
        done_event.set()

    t = threading.Thread(target=_run_and_signal, daemon=True, name=f"council-block-{symbol}")
    t.start()
    done_event.wait(timeout=timeout)

    # Read result from cache
    with _council_lock:
        cached = _council_cache.get(symbol)
    if cached is not None:
        return cached["composite"]
    return 0.0


def get_council_verdict(symbol: str) -> Optional[Dict]:
    """
    Return the full cached council verdict dict for *symbol*, or None if not
    yet available or expired.
    """
    with _council_lock:
        ts = _council_ts.get(symbol, 0)
        cached = _council_cache.get(symbol)

    if cached is not None and (time.time() - ts) < _COUNCIL_TTL:
        return cached
    return None
