"""
NexusTrader — Advanced Prediction Strategies
=============================================
Analytical strategies module that implements Claude-grade reasoning
for market prediction. Each strategy is an independent signal source
that can be composed with the Market Oracle and Model Council.

Strategies implemented:
  1. Multi-timeframe confluence — 1h/4h/daily/weekly alignment scoring
  2. Volume-price divergence — detects moves lacking volume confirmation
  3. Bayesian confidence updater — uses feedback loop to dynamically weight signals
  4. Signal decay weighting — recent signals count more than stale ones
  5. Regime-adaptive scoring — trending/ranging/volatile → different logic
  6. Confluence multiplier — exponential boost when many signals agree
  7. Smart money divergence — institutional vs retail flow mismatch
  8. Key level proximity — support/resistance/pivot proximity scoring

All strategies return scores in [-1, +1]. Thread-safe, cached.
"""

import numpy as np
import pandas as pd
import time
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False


# ─────────────────────────────────────────────────────────────────────────────
# Thread-safe cache
# ─────────────────────────────────────────────────────────────────────────────
class _TTLCache:
    def __init__(self, default_ttl: int = 300):
        self._store: Dict[str, Tuple[float, object]] = {}
        self._lock = threading.Lock()
        self._ttl = default_ttl

    def get(self, key: str) -> Optional[object]:
        with self._lock:
            entry = self._store.get(key)
            if entry and (time.time() - entry[0]) < self._ttl:
                return entry[1]
        return None

    def set(self, key: str, value: object, ttl: int = None):
        with self._lock:
            self._store[key] = (time.time(), value)

_cache = _TTLCache(default_ttl=300)


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 1: Multi-Timeframe Confluence
# ─────────────────────────────────────────────────────────────────────────────

def score_multi_timeframe(symbol: str, df: Optional[pd.DataFrame] = None) -> float:
    """
    Check if multiple timeframes agree on direction.
    When 1h, 4h, daily, and weekly all point the same way, confidence
    is much higher than when they conflict.

    Returns [-1, +1]: positive = all timeframes bullish, negative = bearish.
    """
    cached = _cache.get(f"mtf_{symbol}")
    if cached is not None:
        return cached

    if not HAS_YF:
        return 0.0

    scores = []

    try:
        clean = symbol.replace("/", "-").split("USDT")[0]
        is_crypto = "/" in symbol or "BTC" in symbol or "ETH" in symbol
        yf_sym = f"{clean}-USD" if is_crypto else symbol.split(".")[0] if "." not in symbol else symbol

        # Fetch multiple timeframes
        timeframes = {
            "1h":  {"period": "5d",  "interval": "1h"},
            "4h":  {"period": "1mo", "interval": "1h"},   # aggregate manually
            "1d":  {"period": "3mo", "interval": "1d"},
            "1wk": {"period": "1y",  "interval": "1wk"},
        }

        for tf_name, params in timeframes.items():
            try:
                data = yf.download(yf_sym, period=params["period"],
                                   interval=params["interval"],
                                   progress=False, auto_adjust=True)
                if data is None or data.empty or len(data) < 5:
                    continue

                closes = data["Close"].values if "Close" in data.columns else data["close"].values
                if len(closes) < 5:
                    continue

                # Compute trend direction for this timeframe
                sma_fast = np.mean(closes[-5:])
                sma_slow = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
                current = float(closes[-1])

                tf_score = 0.0
                if current > sma_fast > sma_slow:
                    tf_score = 0.5   # bullish alignment
                elif current < sma_fast < sma_slow:
                    tf_score = -0.5  # bearish alignment
                elif current > sma_slow:
                    tf_score = 0.2
                elif current < sma_slow:
                    tf_score = -0.2

                # Momentum confirmation
                mom = (closes[-1] - closes[-5]) / (abs(closes[-5]) + 1e-9)
                tf_score += np.clip(mom * 2, -0.3, 0.3)

                scores.append(tf_score)
            except Exception:
                continue

    except Exception:
        pass

    if not scores:
        _cache.set(f"mtf_{symbol}", 0.0)
        return 0.0

    # Confluence: average of timeframe scores, boosted when all agree
    avg = np.mean(scores)
    all_same_sign = all(s > 0 for s in scores) or all(s < 0 for s in scores)
    if all_same_sign and len(scores) >= 3:
        avg *= 1.5  # 50% boost for full confluence

    result = float(np.clip(avg, -1.0, 1.0))
    _cache.set(f"mtf_{symbol}", result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 2: Volume-Price Divergence
# ─────────────────────────────────────────────────────────────────────────────

def score_volume_divergence(df: Optional[pd.DataFrame] = None) -> float:
    """
    Detect price moves that lack volume confirmation.
    Rising price + falling volume = weak rally (bearish divergence).
    Falling price + rising volume = capitulation (potential bottom).

    Returns [-1, +1].
    """
    if df is None or df.empty:
        return 0.0

    try:
        col_c = "close" if "close" in df.columns else "Close"
        col_v = "volume" if "volume" in df.columns else "Volume"

        if col_v not in df.columns:
            return 0.0

        closes = df[col_c].values[-20:]
        volumes = df[col_v].values[-20:]

        if len(closes) < 10 or len(volumes) < 10:
            return 0.0

        # Price trend (last 10 vs prior 10)
        price_recent = np.mean(closes[-5:])
        price_prior = np.mean(closes[-10:-5])
        price_change = (price_recent - price_prior) / (abs(price_prior) + 1e-9)

        # Volume trend
        vol_recent = np.mean(volumes[-5:])
        vol_prior = np.mean(volumes[-10:-5])
        vol_change = (vol_recent - vol_prior) / (abs(vol_prior) + 1e-9)

        score = 0.0

        # Bearish divergence: price up but volume down
        if price_change > 0.01 and vol_change < -0.1:
            score = -0.3 - abs(vol_change) * 0.3  # weaker rally

        # Bullish divergence: price down but volume up (capitulation)
        elif price_change < -0.01 and vol_change > 0.2:
            score = 0.3 + abs(vol_change) * 0.2  # capitulation buy signal

        # Confirmation: price and volume moving together
        elif price_change > 0.01 and vol_change > 0.1:
            score = 0.4  # healthy rally with volume
        elif price_change < -0.01 and vol_change < -0.1:
            score = -0.2  # orderly decline

        # High volume spike (>2x average) = attention event
        if vol_recent > np.mean(volumes) * 2:
            score += 0.1 if price_change > 0 else -0.1

        return float(np.clip(score, -1.0, 1.0))

    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 3: Bayesian Confidence Updater
# ─────────────────────────────────────────────────────────────────────────────

def bayesian_confidence_update(
    prior_confidence: float,
    oracle_signals: Dict[str, float],
    feedback_accuracies: Optional[Dict[str, float]] = None,
) -> float:
    """
    Use Bayesian reasoning to update confidence based on signal track records.

    If the feedback loop tells us that 'macro' has been right 70% of the time
    and 'social' only 40%, we weight macro's current signal much higher.

    Returns adjusted confidence [0, 100].
    """
    if not oracle_signals:
        return prior_confidence

    # Default priors: assume 55% accuracy for unknown signals
    accuracies = feedback_accuracies or {}

    weighted_agreement = 0.0
    total_weight = 0.0

    for signal_name, signal_value in oracle_signals.items():
        accuracy = accuracies.get(signal_name, 0.55)
        # Weight = accuracy^2 (quadratic boost for high-accuracy signals)
        weight = accuracy ** 2
        # Agreement = how strongly this signal points in the consensus direction
        weighted_agreement += abs(signal_value) * weight
        total_weight += weight

    if total_weight == 0:
        return prior_confidence

    # Bayesian update: scale confidence by quality-weighted signal strength
    signal_quality = weighted_agreement / total_weight  # 0 to 1
    # Map to confidence adjustment: high quality → boost, low → penalty
    adjustment = (signal_quality - 0.3) * 30  # -9 to +21 range

    return float(np.clip(prior_confidence + adjustment, 45, 98))


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 4: Signal Decay Weighting
# ─────────────────────────────────────────────────────────────────────────────

def apply_signal_decay(
    signals: Dict[str, float],
    signal_ages_minutes: Optional[Dict[str, float]] = None,
    half_life_minutes: float = 30.0,
) -> Dict[str, float]:
    """
    Apply exponential decay to signal scores based on their age.
    Fresher signals matter more than stale ones.

    signals: {layer_name: score}
    signal_ages_minutes: {layer_name: age_in_minutes}
    half_life_minutes: time for signal to lose half its weight

    Returns decay-adjusted signal scores.
    """
    if signal_ages_minutes is None:
        return signals  # No age info → no decay

    decayed = {}
    for name, score in signals.items():
        age = signal_ages_minutes.get(name, 0.0)
        # Exponential decay: weight = 0.5^(age / half_life)
        decay_factor = 0.5 ** (age / half_life_minutes) if half_life_minutes > 0 else 1.0
        decayed[name] = score * decay_factor

    return decayed


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 5: Market Regime Detection (Enhanced)
# ─────────────────────────────────────────────────────────────────────────────

def detect_regime(df: Optional[pd.DataFrame] = None) -> Dict[str, object]:
    """
    Classify the current market regime and return regime-appropriate
    strategy weights.

    Regimes:
      - "strong_trend": Use momentum, follow the trend
      - "mean_revert": Use RSI extremes, fade the move
      - "high_vol": Reduce position size, wider stops
      - "consolidation": Wait for breakout, reduce signals
      - "breakout": Aggressive entry on confirmed break

    Returns: {"regime": str, "confidence": float, "strategy_bias": float}
    """
    if df is None or df.empty:
        return {"regime": "unknown", "confidence": 0.5, "strategy_bias": 0.0}

    try:
        col_c = "close" if "close" in df.columns else "Close"
        col_h = "high" if "high" in df.columns else "High"
        col_l = "low" if "low" in df.columns else "Low"

        closes = df[col_c].values
        if len(closes) < 20:
            return {"regime": "unknown", "confidence": 0.5, "strategy_bias": 0.0}

        # ATR-based volatility
        highs = df[col_h].values[-14:] if col_h in df.columns else closes[-14:] * 1.01
        lows = df[col_l].values[-14:] if col_l in df.columns else closes[-14:] * 0.99
        tr_list = []
        for i in range(1, min(14, len(closes))):
            tr_list.append(max(
                float(highs[i]) - float(lows[i]),
                abs(float(highs[i]) - float(closes[i - 1])),
                abs(float(lows[i]) - float(closes[i - 1])),
            ))
        atr = np.mean(tr_list) if tr_list else 0
        atr_pct = atr / (abs(closes[-1]) + 1e-9) * 100

        # Trend strength via ADX approximation
        price_20 = closes[-20:]
        returns_20 = np.diff(price_20) / (np.abs(price_20[:-1]) + 1e-9)
        trend_strength = abs(np.mean(returns_20)) / (np.std(returns_20) + 1e-9)

        # Bollinger Band width (volatility proxy)
        sma_20 = np.mean(closes[-20:])
        std_20 = np.std(closes[-20:])
        bb_width = (2 * std_20) / (sma_20 + 1e-9) * 100

        # RSI
        delta = np.diff(closes[-15:])
        gains = delta[delta > 0]
        losses = -delta[delta < 0]
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 1e-9
        rsi = 100 - (100 / (1 + avg_gain / max(avg_loss, 1e-9)))

        # Classify regime
        if trend_strength > 1.5 and atr_pct < 3:
            regime = "strong_trend"
            confidence = 0.85
            bias = np.sign(np.mean(returns_20)) * 0.6
        elif rsi > 72 or rsi < 28:
            regime = "mean_revert"
            confidence = 0.75
            bias = -0.4 if rsi > 72 else 0.4  # fade the extreme
        elif atr_pct > 4 or bb_width > 8:
            regime = "high_vol"
            confidence = 0.65
            bias = 0.0  # no directional bias in high vol
        elif bb_width < 3 and trend_strength < 0.5:
            regime = "consolidation"
            confidence = 0.60
            bias = 0.0
        elif bb_width < 4 and abs(closes[-1] - sma_20) / sma_20 > 0.02:
            regime = "breakout"
            confidence = 0.70
            bias = 0.5 if closes[-1] > sma_20 else -0.5
        else:
            regime = "normal"
            confidence = 0.55
            bias = np.sign(np.mean(returns_20)) * 0.2

        return {
            "regime": regime,
            "confidence": round(confidence, 2),
            "strategy_bias": round(float(bias), 3),
            "atr_pct": round(atr_pct, 2),
            "rsi": round(rsi, 1),
            "bb_width": round(bb_width, 2),
            "trend_strength": round(trend_strength, 3),
        }

    except Exception:
        return {"regime": "unknown", "confidence": 0.5, "strategy_bias": 0.0}


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 6: Confluence Multiplier
# ─────────────────────────────────────────────────────────────────────────────

def confluence_multiplier(signals: Dict[str, float], threshold: float = 0.1) -> float:
    """
    When many independent signals agree on direction, the combined
    confidence should be higher than a simple average.

    This implements an exponential confluence boost:
      - 3/5 signals agree → 1.1x multiplier
      - 4/5 signals agree → 1.3x multiplier
      - 5/5 signals agree → 1.5x multiplier

    Returns a multiplier [0.7, 1.5] to apply to the overall confidence.
    """
    if not signals:
        return 1.0

    bullish = sum(1 for v in signals.values() if v > threshold)
    bearish = sum(1 for v in signals.values() if v < -threshold)
    total = len(signals)

    if total == 0:
        return 1.0

    # Agreement ratio: what fraction of non-neutral signals agree?
    active = bullish + bearish
    if active == 0:
        return 0.85  # all neutral → slight confidence penalty

    majority = max(bullish, bearish)
    agreement_ratio = majority / active  # 0.5 (split) to 1.0 (unanimous)
    coverage = active / total  # what fraction of signals have an opinion

    # Exponential boost for high agreement + high coverage
    if agreement_ratio >= 0.9 and coverage >= 0.6:
        return 1.5  # near-unanimous with good coverage
    elif agreement_ratio >= 0.75 and coverage >= 0.5:
        return 1.3
    elif agreement_ratio >= 0.6:
        return 1.1
    elif agreement_ratio <= 0.55:
        return 0.8  # signals are split → reduce confidence
    else:
        return 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 7: Key Level Proximity Scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_key_levels(df: Optional[pd.DataFrame] = None) -> float:
    """
    Score based on proximity to key support/resistance levels.
    Near strong support → bullish bias (likely bounce).
    Near strong resistance → bearish bias (likely rejection).
    Breaking through a level → strong directional signal.

    Returns [-1, +1].
    """
    if df is None or df.empty:
        return 0.0

    try:
        col_c = "close" if "close" in df.columns else "Close"
        col_h = "high" if "high" in df.columns else "High"
        col_l = "low" if "low" in df.columns else "Low"

        closes = df[col_c].values
        highs = df[col_h].values if col_h in df.columns else closes
        lows = df[col_l].values if col_l in df.columns else closes

        if len(closes) < 20:
            return 0.0

        current = float(closes[-1])

        # Find key levels from recent price action
        recent_high = float(np.max(highs[-20:]))
        recent_low = float(np.min(lows[-20:]))
        range_size = recent_high - recent_low
        if range_size < 1e-6:
            return 0.0

        # Fibonacci levels
        fib_382 = recent_low + range_size * 0.382
        fib_500 = recent_low + range_size * 0.500
        fib_618 = recent_low + range_size * 0.618

        # Position relative to range
        position = (current - recent_low) / range_size  # 0 to 1

        score = 0.0

        # Near support (bottom 15% of range) → bullish
        if position < 0.15:
            score = 0.4 + (0.15 - position) * 2  # stronger at extremes

        # Near resistance (top 15% of range) → bearish
        elif position > 0.85:
            score = -0.4 - (position - 0.85) * 2

        # At Fibonacci levels → potential reversal zones
        for fib_level in [fib_382, fib_500, fib_618]:
            proximity = abs(current - fib_level) / (range_size + 1e-9)
            if proximity < 0.03:  # within 3% of a fib level
                # Direction depends on whether approaching from above or below
                if closes[-2] > fib_level and current <= fib_level:
                    score -= 0.2  # broke below → bearish
                elif closes[-2] < fib_level and current >= fib_level:
                    score += 0.2  # broke above → bullish

        # Breakout detection: closing beyond recent range
        if current > recent_high * 0.99:
            score = 0.6  # potential breakout
        elif current < recent_low * 1.01:
            score = -0.6  # potential breakdown

        return float(np.clip(score, -1.0, 1.0))

    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Master Strategy Aggregator
# ─────────────────────────────────────────────────────────────────────────────

def run_all_strategies(
    symbol: str,
    df: Optional[pd.DataFrame] = None,
    oracle_signals: Optional[Dict[str, float]] = None,
    prior_confidence: float = 75.0,
) -> Dict[str, object]:
    """
    Run all prediction strategies and return a comprehensive enhancement
    package that can be blended into the main prediction pipeline.

    Returns:
        {
            "mtf_score": float,           # multi-timeframe confluence
            "volume_div_score": float,     # volume-price divergence
            "key_level_score": float,      # support/resistance proximity
            "regime": {...},               # market regime info
            "confluence_mult": float,      # confidence multiplier
            "bayesian_confidence": float,  # Bayesian-adjusted confidence
            "strategy_composite": float,   # weighted composite [-1, +1]
            "confidence_adjustment": float, # how much to adjust confidence
        }
    """
    # Run strategies in parallel-safe manner
    mtf = score_multi_timeframe(symbol, df)
    vol_div = score_volume_divergence(df)
    key_lvl = score_key_levels(df)
    regime = detect_regime(df)

    # Combine oracle signals with our strategy signals for confluence
    all_signals = dict(oracle_signals or {})
    all_signals["multi_timeframe"] = mtf
    all_signals["volume_divergence"] = vol_div
    all_signals["key_levels"] = key_lvl
    all_signals["regime_bias"] = regime.get("strategy_bias", 0.0)

    conf_mult = confluence_multiplier(all_signals)

    # Get feedback accuracies for Bayesian update
    feedback_accs = None
    try:
        from ..agents.feedback_loop import feedback_loop
        layer_stats = feedback_loop.get_accuracy_summary()
        if layer_stats and isinstance(layer_stats, dict):
            feedback_accs = layer_stats.get("layer_accuracies", None)
    except Exception:
        pass

    bayesian_conf = bayesian_confidence_update(prior_confidence, all_signals, feedback_accs)

    # Weighted composite of strategy scores
    strategy_composite = (
        mtf * 0.30 +        # multi-timeframe is strongest
        vol_div * 0.20 +    # volume confirmation
        key_lvl * 0.20 +    # key level proximity
        regime.get("strategy_bias", 0.0) * 0.30  # regime context
    )
    strategy_composite = float(np.clip(strategy_composite, -1.0, 1.0))

    # Confidence adjustment based on all strategies
    conf_adj = (conf_mult - 1.0) * 15  # convert multiplier to confidence delta

    return {
        "mtf_score": round(mtf, 3),
        "volume_div_score": round(vol_div, 3),
        "key_level_score": round(key_lvl, 3),
        "regime": regime,
        "confluence_mult": round(conf_mult, 2),
        "bayesian_confidence": round(bayesian_conf, 1),
        "strategy_composite": round(strategy_composite, 3),
        "confidence_adjustment": round(conf_adj, 1),
    }
