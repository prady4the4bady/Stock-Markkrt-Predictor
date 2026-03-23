"""
NexusTrader - Risk Metrics Engine
Computes professional trading risk metrics for every prediction:
- Kelly Criterion (optimal position sizing)
- Sharpe & Sortino ratios (risk-adjusted return quality)
- Maximum Drawdown & Calmar Ratio
- Value at Risk (parametric + historical)
- Breakout / Key-level detection
- Short-squeeze potential
- Volume-price divergence signal
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


# ── Core Risk Calculations ─────────────────────────────────────────────────────

def calculate_sharpe_sortino(returns: np.ndarray, risk_free_rate: float = 0.05) -> Dict:
    """
    Annualised Sharpe and Sortino ratios from daily returns.
    risk_free_rate: annual rate (default 5% = current US T-bill proxy)
    """
    if len(returns) < 10:
        return {"sharpe": 0.0, "sortino": 0.0, "annual_return": 0.0, "annual_vol": 0.0}

    daily_rf = risk_free_rate / 252
    excess   = returns - daily_rf

    annual_return = float(np.mean(returns) * 252)
    annual_vol    = float(np.std(returns) * np.sqrt(252))
    sharpe        = float((annual_return - risk_free_rate) / (annual_vol + 1e-9))

    # Sortino: only downside deviation
    downside = returns[returns < daily_rf]
    downside_std = float(np.std(downside) * np.sqrt(252)) if len(downside) > 0 else annual_vol
    sortino = float((annual_return - risk_free_rate) / (downside_std + 1e-9))

    return {
        "sharpe":        round(sharpe,        3),
        "sortino":       round(sortino,       3),
        "annual_return": round(annual_return * 100, 2),  # in %
        "annual_vol":    round(annual_vol    * 100, 2),  # in %
    }


def calculate_max_drawdown(prices: np.ndarray) -> Dict:
    """Maximum peak-to-trough drawdown + Calmar ratio."""
    if len(prices) < 2:
        return {"max_drawdown": 0.0, "calmar_ratio": 0.0, "recovery_days": 0}

    peak = np.maximum.accumulate(prices)
    drawdown = (prices - peak) / (peak + 1e-9)
    max_dd = float(np.min(drawdown))

    # Estimate recovery: days since last all-time high
    at_peak = (prices == peak)
    last_peak_idx = len(prices) - 1
    for i in range(len(prices) - 1, -1, -1):
        if at_peak[i]:
            last_peak_idx = i
            break
    recovery_days = len(prices) - 1 - last_peak_idx

    # Calmar: annual return / |max drawdown|
    annual_ret = float(((prices[-1] / prices[0]) ** (252 / max(len(prices), 1))) - 1)
    calmar     = float(annual_ret / (abs(max_dd) + 1e-9))

    return {
        "max_drawdown":   round(max_dd * 100, 2),   # in %
        "calmar_ratio":   round(calmar, 3),
        "recovery_days":  int(recovery_days),
        "current_drawdown": round(float(drawdown[-1]) * 100, 2),
    }


def calculate_var(returns: np.ndarray, confidence: float = 0.95) -> Dict:
    """
    Value at Risk at given confidence level.
    Both parametric (Gaussian) and historical simulation.
    """
    if len(returns) < 10:
        return {"var_parametric": 0.0, "var_historical": 0.0, "cvar": 0.0}

    z = 1.645 if confidence == 0.95 else 2.326  # 95% or 99%
    mu  = float(np.mean(returns))
    sig = float(np.std(returns))

    var_param = float(-(mu - z * sig))                          # 1-day parametric VaR
    var_hist  = float(-np.percentile(returns, (1 - confidence) * 100))  # historical
    cvar      = float(-np.mean(returns[returns < -var_hist]))   # Expected Shortfall

    return {
        "var_parametric": round(var_param * 100, 3),   # % of position
        "var_historical": round(var_hist  * 100, 3),
        "cvar":           round(cvar      * 100, 3),
        "confidence":     int(confidence  * 100),
    }


def calculate_kelly_criterion(rise_probability: float, predicted_return_pct: float,
                               current_volatility_pct: float) -> Dict:
    """
    Kelly Criterion for optimal position sizing.

    f* = (b×p - q) / b   where:
      b = expected win / expected loss ratio
      p = probability of a winning trade
      q = 1 - p

    Returns full Kelly and a half-Kelly (more practical, less risk of ruin).
    """
    p = max(0.01, min(0.99, rise_probability / 100))
    q = 1.0 - p

    # Estimate win/loss magnitude from predicted return and volatility
    expected_win  = max(0.001, abs(predicted_return_pct) / 100)
    expected_loss = max(0.001, current_volatility_pct / 100 * 1.5)  # 1.5σ stop-loss proxy

    b = expected_win / expected_loss  # odds

    full_kelly = (b * p - q) / b
    half_kelly = full_kelly / 2

    # Cap at 25% of portfolio (prudent risk management)
    full_kelly_pct = round(max(0.0, min(25.0, full_kelly * 100)), 1)
    half_kelly_pct = round(max(0.0, min(12.5, half_kelly * 100)), 1)

    # Risk rating
    if half_kelly_pct > 8:
        risk_rating = "High Conviction"
    elif half_kelly_pct > 4:
        risk_rating = "Moderate"
    elif half_kelly_pct > 1:
        risk_rating = "Low"
    else:
        risk_rating = "Avoid"

    return {
        "full_kelly_pct":  full_kelly_pct,
        "half_kelly_pct":  half_kelly_pct,
        "edge":            round((b * p - q) * 100, 2),  # Expected edge per unit
        "win_loss_ratio":  round(b, 3),
        "risk_rating":     risk_rating,
        "suggested_size":  half_kelly_pct,  # Practical recommendation
    }


# ── Technical Pattern Detection ───────────────────────────────────────────────

def detect_breakout(df: pd.DataFrame) -> Dict:
    """
    Detect if price is breaking out of a key level:
    - 52-week high/low
    - 20-day / 50-day channel
    - Bollinger Band squeeze breakout
    """
    close  = df['close'].astype(float)
    high   = df['high'].astype(float)  if 'high'   in df.columns else close
    volume = df['volume'].astype(float) if 'volume' in df.columns else pd.Series(
        np.ones(len(df)), index=df.index)

    cur = float(close.iloc[-1])

    # 52-week levels
    w52_high = float(high.tail(252).max())
    w52_low  = float(close.tail(252).min())

    # 20-day channel
    ch20_high = float(high.tail(20).max())
    ch20_low  = float(close.tail(20).min())

    # Bollinger Band squeeze
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_width      = (2 * std20 / (sma20 + 1e-9)).iloc[-1]
    bb_width_sma  = (2 * std20 / (sma20 + 1e-9)).rolling(50).mean().iloc[-1]
    squeeze_active = bool(bb_width < bb_width_sma * 0.85)

    # Volume confirmation (breakout on high volume is stronger)
    vol_20_avg  = float(volume.tail(20).mean())
    vol_today   = float(volume.iloc[-1])
    vol_confirm = vol_today > vol_20_avg * 1.3

    # Breakout classifications
    near_52w_high = cur >= w52_high * 0.98
    near_52w_low  = cur <= w52_low  * 1.02
    ch20_breakout_up   = cur > ch20_high * 0.999
    ch20_breakout_down = cur < ch20_low  * 1.001

    breakout_type = "none"
    breakout_strength = 0
    if near_52w_high and vol_confirm:
        breakout_type = "52w_high_breakout"
        breakout_strength = 95
    elif near_52w_low and vol_confirm:
        breakout_type = "52w_low_breakdown"
        breakout_strength = 90
    elif ch20_breakout_up and vol_confirm:
        breakout_type = "channel_breakout_up"
        breakout_strength = 75
    elif ch20_breakout_down and vol_confirm:
        breakout_type = "channel_breakdown"
        breakout_strength = 70
    elif squeeze_active:
        breakout_type = "squeeze_pending"
        breakout_strength = 60

    return {
        "breakout_type":     breakout_type,
        "breakout_strength": breakout_strength,
        "near_52w_high":     near_52w_high,
        "near_52w_low":      near_52w_low,
        "w52_high":          round(w52_high, 2),
        "w52_low":           round(w52_low,  2),
        "bb_squeeze":        squeeze_active,
        "volume_confirm":    vol_confirm,
        "pct_from_52w_high": round((cur - w52_high) / w52_high * 100, 2),
        "pct_from_52w_low":  round((cur - w52_low)  / w52_low  * 100, 2),
    }


def detect_volume_price_divergence(df: pd.DataFrame) -> Dict:
    """
    Volume-price divergence: price rising on falling volume (bearish) or
    price falling on rising volume (potential capitulation / reversal).
    """
    close  = df['close'].astype(float).tail(20)
    volume = df['volume'].astype(float).tail(20) if 'volume' in df.columns else close * 0 + 1

    price_trend  = np.polyfit(np.arange(len(close)),  close.values,  1)[0]
    volume_trend = np.polyfit(np.arange(len(volume)), volume.values, 1)[0]

    price_up   = price_trend  > 0
    volume_up  = volume_trend > 0

    if price_up and not volume_up:
        divergence = "bearish"        # Rally losing volume support
        signal = -1
    elif not price_up and volume_up:
        divergence = "capitulation"   # Selling accelerating — possible reversal
        signal = 1
    elif price_up and volume_up:
        divergence = "confirmed_bull"
        signal = 2
    else:
        divergence = "confirmed_bear"
        signal = -2

    return {
        "divergence_type":   divergence,
        "signal":            signal,
        "price_trend_slope": round(float(price_trend),  4),
        "vol_trend_slope":   round(float(volume_trend), 0),
    }


def detect_short_squeeze_potential(df: pd.DataFrame) -> Dict:
    """
    Proxy short-squeeze score from price/volume behaviour (no paid data needed).
    High scores = elevated short-covering risk if price rallies.
    """
    close  = df['close'].astype(float)
    volume = df['volume'].astype(float) if 'volume' in df.columns else pd.Series(
        np.ones(len(df)), index=df.index)

    # 1. Price momentum (3-day vs 20-day)
    mom_3  = (close.iloc[-1] - close.iloc[-4])  / (close.iloc[-4]  + 1e-9) if len(close) > 4 else 0
    mom_20 = (close.iloc[-1] - close.iloc[-21]) / (close.iloc[-21] + 1e-9) if len(close) > 21 else 0

    # 2. Volume spike (today vs 20-day avg)
    vol_spike = float(volume.iloc[-1]) / (float(volume.tail(20).mean()) + 1e-9)

    # 3. RSI divergence from extreme oversold
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rsi   = 100 - 100 / (1 + gain / (loss + 1e-9))
    rsi_val = float(rsi.iloc[-1]) if not rsi.iloc[-1] != rsi.iloc[-1] else 50.0

    # Squeeze score: high when oversold RSI + high volume spike + price bouncing
    score = 0.0
    if rsi_val < 35:
        score += (35 - rsi_val) / 35 * 40    # up to 40 pts
    if vol_spike > 2:
        score += min(30, (vol_spike - 1) * 15)  # up to 30 pts
    if mom_3 > 0 and mom_20 < 0:
        score += 20                              # reversal signature
    if mom_3 > 0.02:
        score += 10                              # strong short-term move

    score = min(100, score)

    return {
        "squeeze_score":  round(score, 1),
        "risk_level":     "Very High" if score > 75 else "High" if score > 50 else "Moderate" if score > 25 else "Low",
        "rsi":            round(rsi_val, 1),
        "volume_spike":   round(vol_spike, 2),
        "momentum_3d":    round(mom_3 * 100, 2),
    }


# ── Main Entry Point ──────────────────────────────────────────────────────────

def compute_full_risk_metrics(df: pd.DataFrame, predictions: List[float],
                               rise_probability: float) -> Dict:
    """
    One-call interface for all risk metrics. Called from routes.py.
    Returns a structured dict that gets appended to the prediction response.
    """
    close  = df['close'].astype(float).values
    returns = np.diff(close) / (close[:-1] + 1e-9)

    current_price    = float(close[-1])
    predicted_final  = float(predictions[-1]) if predictions else current_price
    predicted_return = (predicted_final - current_price) / (current_price + 1e-9) * 100
    volatility_pct   = float(np.std(returns[-20:]) * 100) if len(returns) >= 20 else 2.0

    sr   = calculate_sharpe_sortino(returns)
    mdd  = calculate_max_drawdown(close)
    var  = calculate_var(returns)
    kelly = calculate_kelly_criterion(rise_probability, predicted_return, volatility_pct)
    bo   = detect_breakout(df)
    vpd  = detect_volume_price_divergence(df)
    ssp  = detect_short_squeeze_potential(df)

    return {
        "sharpe_sortino":       sr,
        "drawdown":             mdd,
        "value_at_risk":        var,
        "kelly_criterion":      kelly,
        "breakout":             bo,
        "volume_price_div":     vpd,
        "short_squeeze":        ssp,
        "volatility_20d_pct":   round(volatility_pct, 3),
        "predicted_return_pct": round(predicted_return, 2),
    }
