"""
NexusTrader — Barebone TA Analyzer
====================================
Pure technical-analysis engine: zero external API dependencies, zero ML.
Operates entirely on OHLCV price/volume data already fetched by yfinance.

Algorithm: 9-indicator composite
  1. RSI (14)              — momentum oscillator (oversold/overbought)
  2. MACD signal cross     — trend + momentum confirmation
  3. Bollinger Band %B     — price position within volatility channel
  4. EMA cross (20/50)     — short-vs-medium-term trend direction
  5. Volume surge          — 10-day avg ratio (institutional activity proxy)
  6. ATR regime            — volatility expansion/contraction
  7. Stochastic %K/%D      — overbought/oversold (secondary oscillator)
  8. Williams %R           — reversal timing
  9. OBV trend slope       — on-balance volume (buying vs selling pressure)

Each indicator returns a score in [-1, +1].
Composite = weighted average, then clamped to [-1, +1].

Used as Signal Layer 17 in the MarketOracle and as a standalone
sanity-check when all other data sources are unavailable.
"""

from typing import Optional, Dict
import numpy as np


def _rsi(closes: np.ndarray, period: int = 14) -> float:
    """RSI — 0-100. Returns normalised score: overbought < -0.5, oversold > +0.5."""
    if len(closes) < period + 1:
        return 0.0
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:]) or 1e-10
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # Map: RSI 30 → +1.0 (oversold = buy), RSI 70 → -1.0 (overbought = sell)
    if rsi <= 30:   return  min(1.0, (30 - rsi) / 15 + 0.5)
    if rsi >= 70:   return  max(-1.0, -(rsi - 70) / 15 - 0.5)
    return (50 - rsi) / 50 * 0.5   # mild signal between 30-70


def _macd_signal(closes: np.ndarray) -> float:
    """MACD 12/26/9. Returns +1 if MACD crossed above signal, -1 if below."""
    if len(closes) < 35:
        return 0.0
    def ema(arr, n):
        k = 2 / (n + 1)
        e = arr[0]
        for v in arr[1:]:
            e = v * k + e * (1 - k)
        return e

    # Compute EMA series
    k12 = 2 / 13
    k26 = 2 / 27
    k9  = 2 / 10

    ema12, ema26 = closes[0], closes[0]
    macd_line = []
    for price in closes:
        ema12 = price * k12 + ema12 * (1 - k12)
        ema26 = price * k26 + ema26 * (1 - k26)
        macd_line.append(ema12 - ema26)

    signal_line = []
    sig = macd_line[0]
    for m in macd_line:
        sig = m * k9 + sig * (1 - k9)
        signal_line.append(sig)

    hist_now  = macd_line[-1]  - signal_line[-1]
    hist_prev = macd_line[-2]  - signal_line[-2]

    if hist_now > 0 and hist_prev <= 0:   return  0.80   # bullish crossover
    if hist_now < 0 and hist_prev >= 0:   return -0.80   # bearish crossover
    if hist_now > 0:  return  min(0.50, hist_now / (abs(closes[-1]) * 0.005 + 1e-9))
    if hist_now < 0:  return  max(-0.50, hist_now / (abs(closes[-1]) * 0.005 + 1e-9))
    return 0.0


def _bollinger_pct_b(closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> float:
    """Bollinger %B: 0 = at lower band (buy), 1 = at upper band (sell)."""
    if len(closes) < period:
        return 0.0
    window = closes[-period:]
    mid  = np.mean(window)
    std  = np.std(window) or 1e-9
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    pct_b = (closes[-1] - lower) / (upper - lower + 1e-9)
    # Map: below 0.2 → bullish (+1), above 0.8 → bearish (-1)
    if pct_b < 0.2:   return  min(1.0, (0.2 - pct_b) * 5)
    if pct_b > 0.8:   return  max(-1.0, (0.8 - pct_b) * 5)
    return (0.5 - pct_b)  # mild neutral signal


def _ema_cross(closes: np.ndarray, fast: int = 20, slow: int = 50) -> float:
    """EMA fast/slow cross. +1 if fast > slow (uptrend), -1 if fast < slow (downtrend)."""
    if len(closes) < slow + 1:
        return 0.0

    def ema_series(arr, n):
        k = 2 / (n + 1)
        e = arr[0]
        series = [e]
        for v in arr[1:]:
            e = v * k + e * (1 - k)
            series.append(e)
        return np.array(series)

    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)

    gap = (fast_ema[-1] - slow_ema[-1]) / (slow_ema[-1] + 1e-9)
    # Normalize: 2% gap = ±0.5 score
    score = np.clip(gap * 25, -1.0, 1.0)
    return float(score)


def _volume_surge(volumes: np.ndarray, period: int = 10) -> float:
    """Volume relative to 10-day avg. Surge = institutional interest."""
    if len(volumes) < period + 1:
        return 0.0
    avg_vol = np.mean(volumes[-period - 1:-1]) or 1e-9
    ratio   = volumes[-1] / avg_vol
    if ratio > 2.5:   return  0.70    # strong surge
    if ratio > 1.5:   return  0.35
    if ratio > 1.0:   return  0.10
    if ratio < 0.5:   return -0.30    # abnormally low volume
    return 0.0


def _stochastic(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                k_period: int = 14, d_period: int = 3) -> float:
    """Stochastic %K/%D. Oversold (<20) = bullish, overbought (>80) = bearish."""
    if len(closes) < k_period + d_period:
        return 0.0
    k_values = []
    for i in range(d_period + 1):
        idx = -(d_period - i + 1)
        window_h = highs[idx - k_period + 1: idx + 1] if idx + 1 != 0 else highs[idx - k_period + 1:]
        window_l = lows[idx - k_period + 1: idx + 1]  if idx + 1 != 0 else lows[idx - k_period + 1:]
        h_max = np.max(window_h) if len(window_h) > 0 else closes[idx]
        l_min = np.min(window_l) if len(window_l) > 0 else closes[idx]
        denom = h_max - l_min or 1e-9
        k_values.append((closes[idx] - l_min) / denom * 100)
    k = k_values[-1]
    d = np.mean(k_values)
    if k < 20 and d < 20:   return  0.70   # oversold confirmation
    if k > 80 and d > 80:   return -0.70   # overbought confirmation
    if k < 20:              return  0.40
    if k > 80:              return -0.40
    return (50 - k) / 100


def _williams_r(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                period: int = 14) -> float:
    """Williams %R: -100 to 0. Near -100 = oversold, near 0 = overbought."""
    if len(closes) < period:
        return 0.0
    h_max = np.max(highs[-period:])
    l_min = np.min(lows[-period:])
    denom = h_max - l_min or 1e-9
    wr = (h_max - closes[-1]) / denom * -100
    if wr <= -80:   return  0.65   # oversold
    if wr >= -20:   return -0.65   # overbought
    return (-50 - wr) / 60


def _obv_trend(closes: np.ndarray, volumes: np.ndarray, period: int = 14) -> float:
    """On-Balance Volume slope. Rising OBV = buying pressure."""
    if len(closes) < period + 1 or len(volumes) < period + 1:
        return 0.0
    obv = 0.0
    obv_series = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
        obv_series.append(obv)
    obv_arr = np.array(obv_series[-period:])
    if len(obv_arr) < 2:
        return 0.0
    xs = np.arange(len(obv_arr))
    slope, _ = np.polyfit(xs, obv_arr, 1)
    # Normalize: positive slope = bullish
    vol_scale = np.mean(np.abs(volumes[-period:])) or 1e-9
    score = np.clip(slope / vol_scale, -1.0, 1.0)
    return float(score)


# ── Composite weights ────────────────────────────────────────────────────────
_INDICATOR_WEIGHTS = {
    "rsi":           0.18,
    "macd":          0.20,
    "bollinger":     0.12,
    "ema_cross":     0.18,
    "volume_surge":  0.10,
    "stochastic":    0.10,
    "williams_r":    0.06,
    "obv":           0.06,
}  # sum = 1.0


def analyze(
    closes:  np.ndarray,
    highs:   Optional[np.ndarray] = None,
    lows:    Optional[np.ndarray] = None,
    volumes: Optional[np.ndarray] = None,
) -> Dict:
    """
    Run all Barebone indicators and return composite score.

    Parameters
    ----------
    closes  : 1-D array of closing prices (oldest → newest)
    highs   : 1-D array of highs (optional — needed for Stochastic / Williams %R)
    lows    : 1-D array of lows  (optional)
    volumes : 1-D array of volumes (optional — needed for volume surge / OBV)

    Returns
    -------
    {
        "composite":   float [-1, +1],   # overall signal
        "indicators":  { name: score },  # individual scores
        "signal":      "BULL" | "BEAR" | "NEUTRAL",
        "strength":    "STRONG" | "MODERATE" | "WEAK",
    }
    """
    if len(closes) < 30:
        return {"composite": 0.0, "indicators": {}, "signal": "NEUTRAL", "strength": "WEAK"}

    # Fallback arrays if optional data not provided
    _highs   = highs   if highs   is not None else closes
    _lows    = lows    if lows    is not None else closes
    _volumes = volumes if volumes is not None else np.ones(len(closes))

    scores = {
        "rsi":          _rsi(closes),
        "macd":         _macd_signal(closes),
        "bollinger":    _bollinger_pct_b(closes),
        "ema_cross":    _ema_cross(closes),
        "volume_surge": _volume_surge(_volumes),
        "stochastic":   _stochastic(_highs, _lows, closes),
        "williams_r":   _williams_r(_highs, _lows, closes),
        "obv":          _obv_trend(closes, _volumes),
    }

    composite = sum(
        scores[ind] * _INDICATOR_WEIGHTS[ind]
        for ind in scores
        if ind in _INDICATOR_WEIGHTS
    )
    composite = float(np.clip(composite, -1.0, 1.0))

    signal = "BULL" if composite > 0.10 else ("BEAR" if composite < -0.10 else "NEUTRAL")
    abs_c  = abs(composite)
    strength = "STRONG" if abs_c > 0.55 else ("MODERATE" if abs_c > 0.25 else "WEAK")

    return {
        "composite":  round(composite, 4),
        "indicators": {k: round(v, 4) for k, v in scores.items()},
        "signal":     signal,
        "strength":   strength,
    }
