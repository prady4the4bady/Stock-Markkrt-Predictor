"""
Market Oracle - API Routes
REST API endpoints for predictions and data with real-time WebSocket support
"""
import sqlite3
import threading as _threading
from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, Depends
from typing import Any, Optional, List, Dict, Set
from pydantic import BaseModel
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import traceback
import re
import sys
import math
import numpy as np
import pandas as pd
import asyncio
import json

from ..data_manager import data_manager
from ..models.ensemble import EnsemblePredictor
from ..models.backtester import ModelBacktester
from ..models.chatbot import stock_chatbot
from ..models.enhanced_models import get_enhanced_prediction
from ..models.market_oracle import market_oracle
from ..models.prediction_tracker import prediction_tracker
from ..config import DEFAULT_STOCKS, DEFAULT_CRYPTO, NSE_INDIA_STOCKS, BSE_INDIA_STOCKS
from sqlalchemy.orm import Session
from ..models.user import User
from ..database import get_db, engine

router = APIRouter(prefix="/api", tags=["predictions"])

# Cache for trained models (in production, use Redis or similar)
# Extended cache duration for reduced latency
model_cache: Dict[str, Any] = {}
model_cache_timestamps: Dict[str, datetime] = {}
_model_cache_lock = _threading.Lock()
MODEL_CACHE_HOURS = 6  # Cache models for 6 hours

# ── AI Scanner: 6-hour background scheduler ───────────────────────────────────
# Curated scan list: top liquid assets across crypto, US stocks, Indian stocks
_SCAN_SYMBOLS = [
    # Crypto (top 5 by market cap)
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    # US Mega-caps
    "AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "NFLX", "AMD", "INTC",
    # Indian large-caps
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    # High-momentum / fintech
    "UBER", "PYPL", "SQ", "SHOP", "PLTR",
]
_SCAN_INTERVAL_HOURS = 6

_scan_cache: Dict[str, Any] = {
    "opportunities": [],
    "all_results": [],
    "last_run": None,
    "next_run": None,
    "status": "pending",   # pending | running | complete | failed
    "scan_count": 0,
}
_scan_cache_lock = _threading.Lock()


def _do_market_scan() -> None:
    """Run quick_predict on all scan symbols, update _scan_cache."""
    import time as _time
    global _scan_cache
    with _scan_cache_lock:
        _scan_cache["status"] = "running"

    opportunities: List[dict] = []
    all_results: List[dict] = []

    for symbol in _SCAN_SYMBOLS:
        try:
            is_crypto = "USDT" in symbol
            df = (data_manager.fetch_crypto_data(symbol)
                  if is_crypto else data_manager.fetch_stock_data(symbol))
            if df is None or df.empty:
                continue

            result = quick_predict(df, hours=24, is_crypto=is_crypto, symbol=symbol)

            price = result["current_price"]
            preds = result.get("predictions", [])
            pct_change = round(((preds[-1] - price) / price * 100), 2) if preds else 0.0

            signals_conflict = result["analysis"].get("signals_conflict", False)
            oracle_direction = result["analysis"].get("oracle_direction", 0)
            combined_signal  = result["analysis"].get("combined_signal", 0.0)
            entry = {
                "symbol": symbol,
                "confidence": result["confidence"],
                "predicted_change": pct_change,
                "price": price,
                "recommendation": result["analysis"]["recommendation"],
                "trend": result["analysis"].get("trend", "Neutral"),
                "rsi": result["analysis"].get("rsi", 50),
                "is_crypto": is_crypto,
                "signals_conflict": signals_conflict,
                "oracle_direction": oracle_direction,
                "combined_signal": combined_signal,
            }
            all_results.append(entry)
            # Only flag as opportunity when:
            #  - recommendation is BUY (combined signal >= 0.15)
            #  - confidence >= 75 (honest threshold, not inflated)
            #  - signals are NOT conflicting (oracle and technical agree)
            #  - oracle itself is not bearish
            is_clean_buy = (
                entry["recommendation"] == "BUY"
                and entry["confidence"] >= 75
                and not signals_conflict
                and oracle_direction >= 0
            )
            if is_clean_buy:
                opportunities.append(entry)
        except Exception:
            continue

    # Sort by confidence descending
    opportunities.sort(key=lambda x: x["confidence"], reverse=True)
    all_results.sort(key=lambda x: x["confidence"], reverse=True)

    now = datetime.now()
    with _scan_cache_lock:
        _scan_cache.update({
            "opportunities": opportunities,
            "all_results": all_results,
            "last_run": now.isoformat(),
            "next_run": (now + timedelta(hours=_SCAN_INTERVAL_HOURS)).isoformat(),
            "status": "complete",
            "scan_count": len(_SCAN_SYMBOLS),
        })


def _scanner_loop() -> None:
    """Daemon thread: wait for cold-start to finish, then scan every 6 hours."""
    import time as _time
    _time.sleep(90)  # Let server fully boot before first heavy scan
    while True:
        try:
            _do_market_scan()
        except Exception as e:
            print(f"[Scanner] Scan failed: {e}")
            with _scan_cache_lock:
                _scan_cache["status"] = "failed"
        _time.sleep(_SCAN_INTERVAL_HOURS * 3600)


# Start the background scanner thread when this module is first imported
_scanner_thread = _threading.Thread(target=_scanner_loop, daemon=True, name="ai-market-scanner")
_scanner_thread.start()

# ── Exchange Market Hub: per-exchange background scanner ─────────────────────
# Curated top-liquidity symbols per exchange. Results cache for 6 h.

_EXCHANGE_REGISTRY: Dict[str, Dict] = {
    "nse": {
        "id": "nse", "name": "NSE India", "full_name": "National Stock Exchange of India",
        "flag": "🇮🇳", "currency": "INR", "is_crypto": False,
        "symbols": [s for s in NSE_INDIA_STOCKS[:35] if "&" not in s],
    },
    "bse": {
        "id": "bse", "name": "BSE India", "full_name": "Bombay Stock Exchange",
        "flag": "🇮🇳", "currency": "INR", "is_crypto": False,
        "symbols": BSE_INDIA_STOCKS[:25],
    },
    "nasdaq": {
        "id": "nasdaq", "name": "NASDAQ", "full_name": "NASDAQ Stock Market",
        "flag": "🇺🇸", "currency": "USD", "is_crypto": False,
        "symbols": [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD",
            "INTC", "NFLX", "PYPL", "SHOP", "PLTR", "QCOM", "ADBE", "CSCO",
            "TXN", "AVGO", "MU", "PANW", "CRWD", "SNOW", "DDOG", "ZM",
        ],
    },
    "nyse": {
        "id": "nyse", "name": "NYSE", "full_name": "New York Stock Exchange",
        "flag": "🇺🇸", "currency": "USD", "is_crypto": False,
        "symbols": [
            "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "JNJ", "PFE", "UNH",
            "XOM", "CVX", "BA", "CAT", "GE", "MMM", "HD", "WMT", "KO", "PEP",
            "DIS", "NKE", "MCD", "T", "VZ", "IBM", "ORCL", "BRK-B",
        ],
    },
    "crypto": {
        "id": "crypto", "name": "Crypto", "full_name": "Global Crypto Markets",
        "flag": "₿", "currency": "USDT", "is_crypto": True,
        "symbols": [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
            "MATIC/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "BCH/USDT",
        ],
    },
}

_exchange_caches: Dict[str, Dict] = {
    ex_id: {
        "results": [], "buy_signals": [], "last_run": None,
        "next_run": None, "status": "pending", "scan_count": 0,
    }
    for ex_id in _EXCHANGE_REGISTRY
}
_exchange_caches_lock = _threading.Lock()


def _do_exchange_scan(exchange_id: str) -> None:
    """Scan curated symbols for one exchange and update its cache."""
    import time as _time
    ex = _EXCHANGE_REGISTRY.get(exchange_id)
    if not ex:
        return

    with _exchange_caches_lock:
        _exchange_caches[exchange_id]["status"] = "running"

    results: List[dict] = []
    is_crypto = ex.get("is_crypto", False)

    for symbol in ex["symbols"]:
        try:
            df = (data_manager.fetch_crypto_data(symbol)
                  if is_crypto else data_manager.fetch_stock_data(symbol))
            if df is None or df.empty:
                continue

            result = quick_predict(df, hours=24, is_crypto=is_crypto, symbol=symbol)
            price  = result["current_price"]
            preds  = result.get("predictions", [])
            pct    = round(((preds[-1] - price) / price * 100), 2) if preds else 0.0

            results.append({
                "symbol":           symbol,
                "confidence":       result["confidence"],
                "predicted_change": pct,
                "price":            price,
                "recommendation":   result["analysis"]["recommendation"],
                "trend":            result["analysis"].get("trend", "Neutral"),
                "rsi":              result["analysis"].get("rsi", 50),
                "is_crypto":        is_crypto,
                "exchange":         exchange_id,
                "signals_conflict": result["analysis"].get("signals_conflict", False),
                "oracle_direction": result["analysis"].get("oracle_direction", 0),
                "combined_signal":  result["analysis"].get("combined_signal", 0.0),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["confidence"], reverse=True)
    # Clean BUY signals: recommendation BUY + confidence >= 75 + no conflict + oracle not bearish
    buy_signals = [
        r for r in results
        if r["recommendation"] == "BUY"
        and r["confidence"] >= 75
        and not r.get("signals_conflict", False)
        and r.get("oracle_direction", 0) >= 0
    ]

    now = datetime.now()
    with _exchange_caches_lock:
        _exchange_caches[exchange_id].update({
            "results":     results,
            "buy_signals": buy_signals,
            "last_run":    now.isoformat(),
            "next_run":    (now + timedelta(hours=_SCAN_INTERVAL_HOURS)).isoformat(),
            "status":      "complete",
            "scan_count":  len(results),
        })


def _exchange_scan_loop() -> None:
    """Daemon: wait for cold-start to finish, then scan every exchange every 6 hours."""
    import time as _time
    _time.sleep(120)  # Offset from main scanner so they don't overlap
    while True:
        for ex_id in _EXCHANGE_REGISTRY:
            try:
                _do_exchange_scan(ex_id)
            except Exception as e:
                print(f"[ExchangeScanner] {ex_id} failed: {e}")
                with _exchange_caches_lock:
                    _exchange_caches[ex_id]["status"] = "failed"
        _time.sleep(_SCAN_INTERVAL_HOURS * 3600)


_exchange_scanner_thread = _threading.Thread(
    target=_exchange_scan_loop, daemon=True, name="exchange-market-scanner"
)
_exchange_scanner_thread.start()
# ─────────────────────────────────────────────────────────────────────────────

# Prediction cache for fast responses
prediction_cache: Dict[str, dict] = {}
prediction_cache_timestamps: Dict[str, datetime] = {}
_prediction_cache_lock = _threading.Lock()
PREDICTION_CACHE_SECONDS = 30  # Cache predictions for 30 seconds

# Real-time price cache for ultra-fast polling
realtime_cache: Dict[str, dict] = {}
cache_timestamps: Dict[str, datetime] = {}
_realtime_cache_lock = _threading.Lock()
CACHE_TTL_MS = 500  # Cache valid for 500ms

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
        self.active_connections[symbol].add(websocket)
    
    def disconnect(self, websocket: WebSocket, symbol: str):
        if symbol in self.active_connections:
            self.active_connections[symbol].discard(websocket)
    
    async def broadcast(self, symbol: str, data: dict):
        if symbol in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[symbol]:
                try:
                    await connection.send_json(data)
                except:
                    dead_connections.add(connection)
            # Clean up dead connections
            self.active_connections[symbol] -= dead_connections

manager = ConnectionManager()


def clean_for_json(obj):
    """Recursively clean NaN and Infinity values from objects for JSON serialization"""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return clean_for_json(obj.tolist())
    return obj


class PredictionRequest(BaseModel):
    symbol: str
    days: int = 7
    is_crypto: bool = False


class PredictionResponse(BaseModel):
    symbol: str
    current_price: float
    predictions: List[float]
    dates: List[str]
    confidence: float
    individual_predictions: dict
    analysis: dict
    timestamp: str


def _compute_trade_plan(
    recommendation: str,
    combined_signal: float,
    current_price: float,
    recent_high: float,
    recent_low: float,
    atr: float,
    rsi: float,
) -> Dict:
    """
    Professional trader-style trade plan with ATR-based stops and targets.

    Stop loss  = entry ± (ATR_mult × ATR)    — keeps loss proportional to volatility
    Target     = entry ± (3 × ATR_mult × ATR) — 3:1 reward-to-risk baseline
    Risk/Reward is adjusted upward for stronger signals.
    """
    sig_abs = abs(combined_signal)

    # Multiplier scales with signal strength:
    #   weak (<0.20)  → 1.5×   moderate (0.20-0.50) → 2.0×   strong (>0.50) → 2.5×
    if sig_abs > 0.50:
        stop_mult, tgt_mult = 2.0, 5.0   # strong:   2:1 stop, 5:1 target → 2.5 R:R
    elif sig_abs > 0.25:
        stop_mult, tgt_mult = 2.0, 4.0   # moderate: 2:1 stop, 4:1 target → 2.0 R:R
    else:
        stop_mult, tgt_mult = 1.5, 3.0   # weak:     1.5:1 stop, 3:1 target → 2.0 R:R

    if recommendation == "BUY":
        stop   = round(current_price - stop_mult * atr, 4)
        target = round(current_price + tgt_mult  * atr, 4)
        # Never place stop above entry or target below entry
        stop   = min(stop,   current_price * 0.995)
        target = max(target, current_price * 1.005)
    elif recommendation == "SELL":
        stop   = round(current_price + stop_mult * atr, 4)
        target = round(current_price - tgt_mult  * atr, 4)
        stop   = max(stop,   current_price * 1.005)
        target = min(target, current_price * 0.995)
    else:   # HOLD — no directional trade
        return {
            "entry": round(current_price, 4),
            "stop_loss":  None,
            "target":     None,
            "risk_reward": 0.0,
            "risk_pct":    0.0,
            "reward_pct":  0.0,
            "position_strength": "No Trade",
            "atr": round(atr, 4),
        }

    risk   = abs(current_price - stop)
    reward = abs(target - current_price)
    rr     = round(reward / risk, 2) if risk > 0 else 0.0

    risk_pct   = round(risk   / current_price * 100, 2)
    reward_pct = round(reward / current_price * 100, 2)

    # Position strength label
    if sig_abs > 0.50 and rr >= 2.0:
        strength = "Strong"
    elif sig_abs > 0.25 and rr >= 1.5:
        strength = "Moderate"
    elif sig_abs > 0.10 and rr >= 1.0:
        strength = "Weak"
    else:
        strength = "No Trade"

    return {
        "entry":             round(current_price, 4),
        "stop_loss":         round(stop,   4),
        "target":            round(target, 4),
        "risk_reward":       rr,
        "risk_pct":          risk_pct,
        "reward_pct":        reward_pct,
        "position_strength": strength,
        "atr":               round(atr, 4),
    }


def _generate_thesis(
    symbol: str,
    recommendation: str,
    combined_signal: float,
    signals_conflict: bool,
    rsi: float,
    momentum_5: float,
    current_price: float,
    sma_20: float,
    regime: str,
    bull_signals: List[str],
    bear_signals: List[str],
    chart_patterns: List[str],
    trade_plan: Dict,
    confidence: float,
) -> str:
    """
    Generate a 3–4 sentence professional trader analysis.
    Reads like a concise analyst note, not a signal dump.
    """
    ticker = symbol.split("/")[0].split("=")[0].upper() if symbol else "Asset"
    sig    = combined_signal
    sig_abs = abs(sig)

    # ── Sentence 1: Overall setup ────────────────────────────────────────────
    direction_word = "bullish" if sig > 0.08 else "bearish" if sig < -0.08 else "neutral"
    strength_word  = "strong" if sig_abs > 0.5 else "moderate" if sig_abs > 0.25 else "mild"

    if signals_conflict:
        s1 = (f"{ticker} is sending conflicting signals — technical indicators point "
              f"{'bullish' if trade_plan.get('entry') and sig > 0 else 'bearish'} "
              f"while the fundamental oracle disagrees. Reduced confidence; wait for confirmation.")
    else:
        s1 = f"{ticker} shows a {strength_word} {direction_word} setup in the {regime.lower()} regime."

    # ── Sentence 2: Primary oracle driver ───────────────────────────────────
    primary_signals = bull_signals if recommendation == "BUY" else bear_signals
    if primary_signals:
        drivers = " and ".join(primary_signals[:2])
        s2 = (f"Key drivers: {drivers} signal {'upside' if recommendation == 'BUY' else 'downside'} pressure.")
    else:
        s2 = ""

    # ── Sentence 3: Technical + RSI context ─────────────────────────────────
    ma_pos = "above" if current_price > sma_20 else "below"
    if rsi > 72:
        rsi_note = f"RSI at {rsi:.0f} — overbought territory, reversal risk elevated."
    elif rsi < 28:
        rsi_note = f"RSI at {rsi:.0f} — oversold, watch for a relief bounce."
    elif rsi > 60 and sig > 0:
        rsi_note = f"RSI at {rsi:.0f} with positive momentum — still room to run."
    elif rsi < 40 and sig < 0:
        rsi_note = f"RSI at {rsi:.0f} with declining momentum — downside pressure intact."
    else:
        rsi_note = f"RSI at {rsi:.0f} — neutral."

    chart_note = f" {chart_patterns[0]}." if chart_patterns else ""
    s3 = f"Price is {ma_pos} the 20-day MA. {rsi_note}{chart_note}"

    # ── Sentence 4: Trade plan ───────────────────────────────────────────────
    entry  = trade_plan.get("entry")
    stop   = trade_plan.get("stop_loss")
    target = trade_plan.get("target")
    rr     = trade_plan.get("risk_reward", 0)
    strength = trade_plan.get("position_strength", "")

    if recommendation != "HOLD" and stop and target and rr >= 1.0:
        reward_pct = trade_plan.get("reward_pct", 0)
        risk_pct   = trade_plan.get("risk_pct",   0)
        s4 = (f"Trade plan ({strength}): Entry ${entry:,.2f} → Target ${target:,.2f} "
              f"(+{reward_pct:.1f}%) | Stop ${stop:,.2f} (-{risk_pct:.1f}%) | "
              f"R:R {rr:.1f}:1 | Confidence {confidence:.0f}%.")
    elif recommendation == "HOLD":
        s4 = "No directional edge — stay flat or reduce size until clearer signal emerges."
    else:
        s4 = f"Signal present but R:R is unfavourable — wait for a better entry."

    return " ".join(filter(None, [s1, s2, s3, s4]))


def quick_predict(df: pd.DataFrame, hours: int, is_crypto: bool = False,
                  symbol: str = "") -> Dict:
    """
    Prediction engine combining technical analysis with Market Oracle 12-layer
    signal fusion. Oracle direction is the PRIMARY signal for recommendation and
    price trajectory. Technical indicators are secondary confirmation only.

    Signal priority:
      1. Market Oracle (12 layers: macro, fundamentals, options, smart money,
         earnings, sector, Fear/Greed, social, Google Trends, seasonal,
         cross-asset) — 60% weight
      2. Technical indicators (SMA crossovers, MACD, RSI, momentum) — 40% weight

    Confidence is HONEST: conflicting signals drop confidence to 45-72%.
    """
    # ── Raw price data ────────────────────────────────────────────────────────
    closes = df['close'].values if 'close' in df.columns else df['Close'].values
    highs  = df['high'].values  if 'high'  in df.columns else df['High'].values
    lows   = df['low'].values   if 'low'   in df.columns else df['Low'].values
    current_price = float(closes[-1])

    # ── Technical indicators ──────────────────────────────────────────────────
    sma_5  = np.mean(closes[-5:])  if len(closes) >= 5  else current_price
    sma_10 = np.mean(closes[-10:]) if len(closes) >= 10 else current_price
    sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else current_price
    sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else current_price

    ema_12 = pd.Series(closes).ewm(span=12, adjust=False).mean().iloc[-1] if len(closes) >= 12 else current_price
    ema_26 = pd.Series(closes).ewm(span=26, adjust=False).mean().iloc[-1] if len(closes) >= 26 else current_price
    macd   = ema_12 - ema_26

    # RSI (14-period)
    delta    = np.diff(closes[-15:]) if len(closes) >= 15 else np.array([0])
    gains    = delta[delta > 0]
    losses   = -delta[delta < 0]
    avg_gain = np.mean(gains)  if len(gains)  > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 1
    rsi = 100 - (100 / (1 + avg_gain / max(avg_loss, 0.001)))

    # Volatility (daily %, then scale to hourly)
    volatility       = np.std(closes[-20:]) / np.mean(closes[-20:]) * 100 if len(closes) >= 20 else 1
    hourly_volatility = volatility / 24 / 100

    # Momentum
    momentum_5  = (current_price - closes[-6])  / closes[-6]  * 100 if len(closes) > 5  and closes[-6]  != 0 else 0
    momentum_10 = (current_price - closes[-11]) / closes[-11] * 100 if len(closes) > 10 and closes[-11] != 0 else 0

    # Support / resistance
    recent_high   = np.max(highs[-20:]) if len(highs) >= 20 else current_price * 1.05
    recent_low    = np.min(lows[-20:])  if len(lows)  >= 20 else current_price * 0.95
    price_position = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5

    # ── ATR (Average True Range, 14-period) ───────────────────────────────────
    # Used for professional stop-loss and target placement
    if len(closes) >= 15 and len(highs) >= 15 and len(lows) >= 15:
        _tr_list = []
        for _i in range(1, min(15, len(closes))):
            _tr_list.append(max(
                float(highs[-_i])  - float(lows[-_i]),
                abs(float(highs[-_i])  - float(closes[-_i - 1])),
                abs(float(lows[-_i])   - float(closes[-_i - 1])),
            ))
        atr = float(np.mean(_tr_list)) if _tr_list else current_price * 0.02
    else:
        atr = current_price * 0.02   # fallback: 2% of price

    # ── Pivot point (standard Floor Trader formula, last session) ─────────────
    _ph, _pl, _pc = float(highs[-1]), float(lows[-1]), float(closes[-1])
    pivot  = (_ph + _pl + _pc) / 3
    pivot_r1 = 2 * pivot - _pl
    pivot_s1 = 2 * pivot - _ph
    pivot_r2 = pivot + (_ph - _pl)
    pivot_s2 = pivot - (_ph - _pl)

    # Technical trend score (-4 … +4)
    trend_score = 0
    if current_price > sma_5 > sma_10: trend_score += 2
    elif current_price < sma_5 < sma_10: trend_score -= 2
    if current_price > sma_20: trend_score += 1
    else: trend_score -= 1
    if macd > 0: trend_score += 1
    else: trend_score -= 1

    # Additional bearish confirmation signals
    # Descending SMA stack (bearish alignment): sma_5 < sma_10 < sma_20
    if sma_5 < sma_10 < sma_20 and current_price < sma_20:
        trend_score -= 1  # extra penalty for full bearish alignment
    # RSI overbought while bearish momentum (reversal risk)
    if rsi > 70 and momentum_5 < 0:
        trend_score -= 1
    # RSI oversold while bullish momentum
    if rsi < 30 and momentum_5 > 0:
        trend_score += 1

    tech_direction = 1 if trend_score > 0 else (-1 if trend_score < 0 else 0)
    trend_strength = min(abs(trend_score) * 0.5, 3)

    # Normalize technical score to [-1, +1]
    tech_normalized = max(-1.0, min(1.0, trend_score / 5.0))

    # ── Market Oracle: 12-layer signal fusion (runs FIRST to inform predictions) ──
    oracle_data: Dict[str, Any] = {}
    oracle_direction  = 0
    oracle_weighted   = 0.0
    oracle_confidence = 85.0   # fallback if oracle fails

    if symbol:
        try:
            _, oracle_data = market_oracle.boost_confidence(85.0, symbol, df)
            oracle_direction  = oracle_data.get("direction", 0)
            oracle_weighted   = float(oracle_data.get("weighted_score", 0.0))
            oracle_confidence = float(oracle_data.get("confidence", 85.0))

            # ── Apply per-layer calibration multipliers (self-learning) ──────
            # Each oracle layer's signal is scaled by its historical accuracy.
            # Layers that have been right > 60% of the time get amplified;
            # layers below 50% accuracy get dampened.
            _raw_signals = oracle_data.get("signals", {})
            _calib_mults = prediction_tracker.get_layer_calibration()
            if _calib_mults and _raw_signals:
                _cal_sum = 0.0; _cal_w = 0.0
                _ORACLE_W = {
                    "macro": 0.13, "market_breadth": 0.11, "fundamentals": 0.11,
                    "options": 0.09, "smart_money": 0.08, "earnings": 0.07,
                    "sector": 0.07, "fear_greed": 0.06, "social": 0.06,
                    "google_trends": 0.03, "seasonal": 0.02, "cross_asset": 0.02,
                    "chart_patterns": 0.09, "news_sentiment": 0.06,
                }
                for _lyr, _score in _raw_signals.items():
                    _w    = _ORACLE_W.get(_lyr, 0.05)
                    _mult = _calib_mults.get(_lyr, 1.0)
                    _cal_sum += float(_score) * _w * _mult
                    _cal_w   += _w * _mult
                if _cal_w > 0:
                    oracle_weighted = max(-1.0, min(1.0, _cal_sum / _cal_w))
        except Exception as _oracle_err:
            print(f"[Oracle] Skipped for quick_predict: {_oracle_err}")

    # ── Combined directional signal: 40% tech + 60% oracle (pre-council) ─────
    # Council is blended later when available (see below).
    combined_signal = tech_normalized * 0.40 + oracle_weighted * 0.60
    combined_signal = max(-1.0, min(1.0, combined_signal))

    combined_direction = (1  if combined_signal >  0.08
                          else -1 if combined_signal < -0.08
                          else  0)

    # ── Council integration (blocking wait up to 8s for AI consensus) ────────
    council_score = 0.0
    try:
        from ..models.council import get_council_score_blocking
        if symbol:
            council_score = get_council_score_blocking(
                symbol, oracle_data.get("signals", {}),
                current_price, oracle_confidence,
                "UP" if combined_direction >= 0 else "DOWN",
                timeout=8,
            )
    except Exception:
        pass

    # Blend: 30% technical + 45% oracle + 25% council
    if council_score != 0.0:
        combined_signal = tech_normalized * 0.30 + oracle_weighted * 0.45 + council_score * 0.25
        combined_signal = max(-1.0, min(1.0, combined_signal))
        combined_direction = (1 if combined_signal > 0.08
                              else -1 if combined_signal < -0.08
                              else 0)

    # ── Model-based price trajectory (NOT random walk) ───────────────────────
    # Uses linear regression on recent closes + ATR bands + signal-driven drift.
    # No np.random — all prices are deterministic from real data.
    predictions      = []
    prediction_dates = []

    # Fit linear regression on last 20 candles for trend slope
    _n_fit = min(20, len(closes))
    _x = np.arange(_n_fit)
    _y = closes[-_n_fit:]
    _slope, _intercept = np.polyfit(_x, _y, 1) if _n_fit >= 3 else (0.0, current_price)

    # Hourly slope derived from daily regression slope
    # _slope is price-change-per-candle (daily), so hourly = _slope / market_hours
    _market_hours = 6.5 if not is_crypto else 24.0
    hourly_regression_drift = _slope / _market_hours

    # Signal-driven drift adjustment: combined_signal scales the regression drift
    combined_strength = abs(combined_signal)
    signal_drift = combined_direction * combined_strength * atr / (24 * 2)  # ATR-scaled

    # Final hourly drift = regression extrapolation + signal-based adjustment
    hourly_drift = hourly_regression_drift * 0.4 + signal_drift * 0.6

    # Mean-reversion damping at support/resistance extremes
    if price_position > 0.85:
        hourly_drift -= atr * 0.01
    elif price_position < 0.15:
        hourly_drift += atr * 0.01

    # EMA smoothing: apply drift with exponential decay toward target
    base_price = current_price
    ema_alpha = 2.0 / (hours + 1) if hours > 1 else 0.5

    for h in range(1, hours + 1):
        # Target from regression line
        regression_target = _intercept + _slope * (_n_fit - 1 + h / _market_hours)
        # Blend current trajectory with regression target (prevents divergence)
        target = regression_target * 0.3 + (base_price + hourly_drift) * 0.7
        base_price = base_price + ema_alpha * (target - base_price)
        # Clamp to ATR-based bounds (no wild swings beyond 2× ATR per day)
        max_move = atr * 2.0 * (h / _market_hours)
        base_price = max(current_price - max_move, min(current_price + max_move, base_price))
        predictions.append(float(round(base_price, 2)))
        prediction_dates.append((datetime.now() + timedelta(hours=h)).strftime('%Y-%m-%d %H:%M'))

    # ── Honest confidence based on signal agreement ───────────────────────────
    signals_conflict = (oracle_direction != 0 and tech_direction != 0
                        and oracle_direction != tech_direction)

    if signals_conflict:
        # Oracle and technical disagree → confidence must reflect uncertainty
        conflict_severity  = abs(oracle_weighted)       # 0-1 (stronger oracle = bigger penalty)
        confidence_penalty = 20.0 + conflict_severity * 15.0   # 20-35% penalty
        final_confidence   = max(45.0, oracle_confidence - confidence_penalty)
    elif oracle_direction == 0 and tech_direction == 0:
        # Both neutral — moderately uncertain
        final_confidence = max(58.0, oracle_confidence - 12.0)
    elif oracle_direction == 0 or tech_direction == 0:
        # One neutral — slight uncertainty
        final_confidence = max(65.0, oracle_confidence - 6.0)
    else:
        # Full agreement between oracle + technical → confidence valid
        final_confidence = max(75.0, min(97.0, oracle_confidence))

    # ── Final recommendation from combined signal ─────────────────────────────
    # Thresholds: need combined_signal ≥ 0.15 to say BUY (prevents false signals)
    if combined_signal >= 0.15:
        final_recommendation = "BUY"
    elif combined_signal <= -0.15:
        final_recommendation = "SELL"
    else:
        final_recommendation = "HOLD"

    # ── Rise / fall probabilities based on combined signal ────────────────────
    # combined_signal in [-1, 1] → probability in [10%, 90%]
    rise_prob = round(50.0 + combined_signal * 40.0, 1)
    rise_prob = max(10.0, min(90.0, rise_prob))
    fall_prob = round(100.0 - rise_prob, 1)

    # ── Trend label uses combined direction ───────────────────────────────────
    if combined_signal >= 0.50:    trend_label = "Strong Bullish 🚀"
    elif combined_signal >= 0.15:  trend_label = "Bullish 📈"
    elif combined_signal <= -0.50: trend_label = "Strong Bearish 💥"
    elif combined_signal <= -0.15: trend_label = "Bearish 📉"
    else:                          trend_label = "Neutral ➡️"

    # ── Honest note / warning ─────────────────────────────────────────────────
    if signals_conflict:
        note = ("⚠️ Technical and fundamental signals conflict. "
                "Technical says " + ("bullish" if tech_direction > 0 else "bearish") +
                " but oracle says " + ("bullish" if oracle_direction > 0 else "bearish") +
                ". Exercise caution — confidence is reduced.")
    elif oracle_direction == -1 and combined_signal <= 0:
        note = "📉 Multiple layers bearish (macro/options/fundamentals). Risk is elevated."
    elif oracle_direction == 1 and combined_signal > 0.15:
        note = "✅ Oracle and technical both bullish. Trade on your own risk."
    else:
        note = "Signals mixed or neutral. Trade on your own risk."

    # ── Market regime ────────────────────────────────────────────────────────
    if rsi > 72 and momentum_5 < 0:
        market_regime = "Overbought — Reversal Risk"
    elif rsi < 28 and momentum_5 > 0:
        market_regime = "Oversold — Potential Bounce"
    elif abs(combined_signal) > 0.50:
        market_regime = "Strong Trend"
    elif abs(combined_signal) > 0.25:
        market_regime = "Trending"
    elif volatility > 3.0:
        market_regime = "High Volatility"
    else:
        market_regime = "Consolidation"

    # ── Professional trade plan (ATR-based stops & targets) ───────────────────
    trade_plan = _compute_trade_plan(
        recommendation=final_recommendation,
        combined_signal=combined_signal,
        current_price=current_price,
        recent_high=recent_high,
        recent_low=recent_low,
        atr=atr,
        rsi=rsi,
    )

    # ── News verdict: does the news support or contradict the prediction? ─────
    news_verdict: Dict[str, Any] = {}
    try:
        from ..models.news_sentiment import news_sentiment_analyzer
        if symbol:
            pred_dir = (1  if combined_signal >  0.08
                        else -1 if combined_signal < -0.08
                        else  0)
            news_verdict = news_sentiment_analyzer.get_prediction_alignment(symbol, pred_dir)
    except Exception:
        pass

    # ── Chart pattern human summary ────────────────────────────────────────────
    chart_pattern_summary: List[str] = []
    try:
        from ..models.chart_patterns import chart_pattern_recognizer
        _, chart_pats = chart_pattern_recognizer.score(df)
        chart_pattern_summary = chart_pattern_recognizer.get_human_summary(chart_pats)
    except Exception:
        pass

    # ── Key oracle signals: top-4 bullish + bearish by absolute score ─────────
    _SIG_LABELS: Dict[str, str] = {
        "macro": "Macro Environment", "market_breadth": "Market Breadth",
        "fundamentals": "Fundamentals",  "options": "Options Flow",
        "smart_money": "Smart Money",    "earnings": "Earnings Catalyst",
        "sector": "Sector Momentum",     "fear_greed": "Fear & Greed",
        "social": "Social Buzz",          "google_trends": "Google Trends",
        "seasonal": "Seasonal Pattern",   "cross_asset": "Cross-Asset",
        "chart_patterns": "Chart Patterns", "news_sentiment": "News Sentiment",
    }
    key_signals: Dict[str, List[str]] = {"bullish": [], "bearish": []}
    oracle_signals_dict = oracle_data.get("signals", {})
    if oracle_signals_dict:
        sorted_sigs = sorted(oracle_signals_dict.items(), key=lambda x: abs(x[1]), reverse=True)
        for _name, _val in sorted_sigs:
            _label = _SIG_LABELS.get(_name, _name)
            if _val > 0.05 and len(key_signals["bullish"]) < 4:
                key_signals["bullish"].append(_label)
            elif _val < -0.05 and len(key_signals["bearish"]) < 4:
                key_signals["bearish"].append(_label)

    # ── Professional trade thesis ─────────────────────────────────────────────
    trade_thesis = _generate_thesis(
        symbol=symbol,
        recommendation=final_recommendation,
        combined_signal=combined_signal,
        signals_conflict=signals_conflict,
        rsi=rsi,
        momentum_5=momentum_5,
        current_price=current_price,
        sma_20=sma_20,
        regime=market_regime,
        bull_signals=key_signals["bullish"],
        bear_signals=key_signals["bearish"],
        chart_patterns=chart_pattern_summary,
        trade_plan=trade_plan,
        confidence=final_confidence,
    )

    # ── Record prediction for outcome verification ────────────────────────────
    # Only record when symbol is known (not bulk scanner calls from background)
    if symbol:
        try:
            prediction_tracker.record(
                symbol         = symbol,
                price          = current_price,
                recommendation = final_recommendation,
                confidence     = final_confidence,
                combined_signal= combined_signal,
                oracle_direction=oracle_direction,
                tech_direction = tech_direction,
                oracle_signals = oracle_data.get("signals", {}),
                hours          = hours,
                entry          = trade_plan["entry"],
                stop           = trade_plan.get("stop_loss") or 0.0,
                target         = trade_plan.get("target")   or 0.0,
                risk_reward    = trade_plan.get("risk_reward") or 0.0,
            )
        except Exception as _rec_err:
            print(f"[Tracker] record skipped: {_rec_err}")

    return {
        "current_price": current_price,
        "predictions":   predictions,
        "dates":         prediction_dates,
        "confidence":    round(final_confidence, 1),
        "individual_predictions": {
            "momentum": predictions,
            "trend":    predictions,
        },
        "analysis": {
            "trend":            trend_label,
            "momentum":         round(momentum_5, 2),
            "volatility":       round(volatility, 2),
            "rsi":              round(rsi, 1),
            "macd":             round(macd, 4),
            "recommendation":   final_recommendation,
            "rise_probability": rise_prob,
            "fall_probability": fall_prob,
            "likely_direction": "up" if combined_signal > 0.08 else "down" if combined_signal < -0.08 else "neutral",
            "prediction_type":  "quick_hourly",
            "note":             note,
            "signals_conflict": signals_conflict,
            "oracle_signals":   oracle_data.get("signals", {}),
            "oracle_direction": oracle_direction,
            "oracle_weighted":  round(oracle_weighted, 3),
            "tech_direction":   tech_direction,
            "combined_signal":  round(combined_signal, 3),
            # ── Verdict enrichment for VerdictPanel ──────────────────────────
            "news_verdict":       news_verdict,
            "chart_patterns":     chart_pattern_summary,
            "key_signals":        key_signals,
            # ── Professional trade plan ───────────────────────────────────────
            "trade_plan":         trade_plan,
            "trade_thesis":       trade_thesis,
            "market_regime":      market_regime,
            # ── Key levels ────────────────────────────────────────────────────
            "key_levels": {
                "pivot":      round(pivot, 4),
                "resistance1": round(pivot_r1, 4),
                "resistance2": round(pivot_r2, 4),
                "support1":    round(pivot_s1, 4),
                "support2":    round(pivot_s2, 4),
                "atr":         round(atr, 4),
            },
        },
        "technical_analysis": {
            "sma_5":          round(sma_5, 2),
            "sma_20":         round(sma_20, 2),
            "rsi":            round(rsi, 1),
            "support":        round(recent_low, 2),
            "resistance":     round(recent_high, 2),
            "price_position": round(price_position * 100, 1),
        },
        "technical_indicators": {
            "momentum":       round(momentum_5, 2),
            "volatility":     round(volatility, 2),
            "trend_strength": round(trend_strength * 33, 1),
            "rsi":            round(rsi, 1),
        },
    }


@router.get("/predict-outcomes/{symbol}")
async def get_predict_outcomes(symbol: str, limit: int = Query(20, ge=1, le=100)):
    """
    Recent verified prediction outcomes for a symbol.
    Shows whether BUY/SELL/HOLD calls were correct and if targets were hit.
    """
    outcomes = prediction_tracker.get_recent_outcomes(symbol=symbol, limit=limit)
    return {"symbol": symbol.upper(), "outcomes": outcomes, "count": len(outcomes)}


@router.get("/accuracy-stats")
async def get_accuracy_stats(symbol: str = Query(None), days: int = Query(30, ge=1, le=365)):
    """
    System-wide (or per-symbol) prediction accuracy statistics.
    Includes direction accuracy, target hit rate, avg R:R, and confidence calibration factor.
    """
    stats       = prediction_tracker.get_accuracy_stats(symbol=symbol, days=days)
    layer_acc   = prediction_tracker.get_layer_accuracy(days=days)
    calib_mults = prediction_tracker.get_layer_calibration(days=days)
    pending     = prediction_tracker.get_pending_count()
    return {
        "overall":       stats,
        "layer_accuracy": layer_acc,
        "calibration":   calib_mults,
        "pending_verification": pending,
    }


@router.get("/health")
async def health_check():
    """API health check endpoint"""
    now = datetime.now()
    return {
        "status": "healthy",
        "service": "NexusTrader API",
        "version": "2.0.0",
        "timestamp": now.isoformat(),
        "server_date": now.strftime('%Y-%m-%d'),
        "server_time": now.strftime('%H:%M:%S'),
        "timezone": "UTC" if datetime.utcnow().hour == now.hour else "Local"
    }


@router.get("/time")
async def get_server_time():
    """Get current server time for synchronization"""
    now = datetime.now()
    return {
        "timestamp": now.isoformat(),
        "date": now.strftime('%Y-%m-%d'),
        "time": now.strftime('%H:%M:%S'),
        "day_of_week": now.strftime('%A'),
        "unix_timestamp": int(now.timestamp())
    }


@router.get('/metrics')
async def metrics():
    """Return simple in-memory metrics for monitoring (non-critical)."""
    from ..monitoring import get_metrics
    ## merge data_manager metrics if available
    try:
        dm = data_manager
        m = get_metrics()
        m.update(dm.metrics)
        return m
    except Exception:
        return get_metrics()


@router.get("/backtest/{symbol:path}")
async def backtest_model(
    symbol: str,
    days: int = Query(default=7, ge=1, le=14),
    test_periods: int = Query(default=5, ge=1, le=10),
    is_crypto: bool = Query(default=False)
):
    """
    Run backtesting to get REAL accuracy metrics for a symbol.
    
    This compares model predictions against actual historical prices
    to calculate genuine accuracy percentages.
    
    - **symbol**: Ticker symbol (e.g., AAPL, BTC/USDT)
    - **days**: Forecast horizon per test (1-14)
    - **test_periods**: Number of test periods to run (1-10)
    - **is_crypto**: Set to true for cryptocurrency
    """
    try:
        symbol = symbol.upper()
        if is_crypto and '/' not in symbol:
            symbol = f"{symbol}/USDT"
        
        print(f"🔬 Running backtest for {symbol}...")
        
        # Fetch historical data
        if is_crypto:
            df = data_manager.fetch_crypto_data(symbol)
        else:
            df = data_manager.fetch_stock_data(symbol)
        
        if df.empty or len(df) < 100:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient data for backtesting {symbol}. Need at least 100 data points."
            )
        
        # Create and train ensemble with exchange-specific parameters
        ensemble = EnsemblePredictor(symbol=symbol)
        ensemble.train(df, verbose=False)
        
        # Run backtest
        backtester = ModelBacktester()
        results = backtester.backtest_ensemble(df, ensemble, test_periods, days)
        
        return {
            "symbol": symbol,
            "backtest_config": {
                "forecast_days": days,
                "test_periods": test_periods,
                "data_points": len(df)
            },
            "results": results,
            "interpretation": _interpret_backtest(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Backtest error for {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _interpret_backtest(results: dict) -> dict:
    """Generate human-readable interpretation of backtest results"""
    ensemble_acc = results.get("ensemble", {}).get("overall_accuracy", 50)
    
    if ensemble_acc >= 70:
        rating = "Excellent"
        description = "Model shows strong predictive power for this asset"
    elif ensemble_acc >= 60:
        rating = "Good"
        description = "Model performs above average for this asset"
    elif ensemble_acc >= 50:
        rating = "Moderate"
        description = "Model shows average predictive ability"
    else:
        rating = "Poor"
        description = "Model struggles with this asset - high volatility or unpredictable patterns"
    
    # Find best performing model
    best_model = None
    best_acc = 0
    for model in ["lstm", "xgboost", "prophet"]:
        if results.get(model) and results[model].get("combined_accuracy", 0) > best_acc:
            best_acc = results[model]["combined_accuracy"]
            best_model = model.upper()
    
    return {
        "rating": rating,
        "description": description,
        "overall_accuracy": ensemble_acc,
        "best_model": best_model,
        "best_model_accuracy": best_acc,
        "reliability_note": "Accuracy is calculated by comparing predictions to actual historical prices. "
                          "Past performance does not guarantee future results."
    }


@router.get("/assets")
async def get_available_assets():
    """Get list of available assets to predict"""
    from ..config import (
        DEFAULT_STOCKS, DEFAULT_CRYPTO, DEFAULT_FOREX, DEFAULT_INDICES, DEFAULT_COMMODITIES,
        DEFAULT_INDIAN_STOCKS, DEFAULT_INDIAN_INDICES,
        NYSE_STOCKS, NASDAQ_STOCKS, SHANGHAI_STOCKS, SHENZHEN_STOCKS,
        TOKYO_STOCKS, HONGKONG_STOCKS, LONDON_STOCKS, EURONEXT_STOCKS,
        TORONTO_STOCKS, NSE_INDIA_STOCKS, BSE_INDIA_STOCKS,
        TADAWUL_STOCKS, ADX_STOCKS, DFM_STOCKS, QSE_STOCKS, KUWAIT_STOCKS,
        KRX_STOCKS, TWSE_STOCKS, SGX_STOCKS, ASX_STOCKS, NZX_STOCKS,
        IDX_STOCKS, SET_STOCKS, KLSE_STOCKS, BMV_STOCKS, B3_STOCKS,
        JSE_STOCKS, XETRA_STOCKS, SIX_STOCKS, TASE_STOCKS, EGX_STOCKS,
        # European exchanges
        VIENNA_STOCKS, MADRID_STOCKS, DUBLIN_STOCKS, LISBON_STOCKS,
        COPENHAGEN_STOCKS, HELSINKI_STOCKS, STOCKHOLM_STOCKS, OSLO_STOCKS, ICELAND_STOCKS,
        TALLINN_STOCKS, RIGA_STOCKS, VILNIUS_STOCKS,
        PRAGUE_STOCKS, WARSAW_STOCKS, BUDAPEST_STOCKS, BUCHAREST_STOCKS,
        ATHENS_STOCKS, ISTANBUL_STOCKS,
        # Latin America
        BUENOS_AIRES_STOCKS, SANTIAGO_STOCKS, COLOMBIA_STOCKS,
        # Southeast Asia
        VIETNAM_STOCKS, PHILIPPINES_STOCKS,
    )
    return {
        # Main categories
        "stocks": DEFAULT_STOCKS,
        "indian_stocks": DEFAULT_INDIAN_STOCKS,
        "crypto": DEFAULT_CRYPTO,
        "forex": DEFAULT_FOREX,
        "indices": DEFAULT_INDICES,
        "indian_indices": DEFAULT_INDIAN_INDICES,
        "commodities": DEFAULT_COMMODITIES,
        # Individual exchanges
        "exchanges": {
            "nyse": {
                "name": "New York Stock Exchange",
                "country": "United States",
                "currency": "USD",
                "market_cap": "$44.7 trillion",
                "stocks": NYSE_STOCKS
            },
            "nasdaq": {
                "name": "NASDAQ",
                "country": "United States", 
                "currency": "USD",
                "market_cap": "$42.2 trillion",
                "stocks": NASDAQ_STOCKS
            },
            "sse": {
                "name": "Shanghai Stock Exchange",
                "country": "China",
                "currency": "CNY",
                "market_cap": "$8.92 trillion",
                "stocks": SHANGHAI_STOCKS
            },
            "szse": {
                "name": "Shenzhen Stock Exchange",
                "country": "China",
                "currency": "CNY",
                "market_cap": "$5.11 trillion",
                "stocks": SHENZHEN_STOCKS
            },
            "tse": {
                "name": "Tokyo Stock Exchange",
                "country": "Japan",
                "currency": "JPY",
                "market_cap": "$7.59 trillion",
                "stocks": TOKYO_STOCKS
            },
            "hkex": {
                "name": "Hong Kong Stock Exchange",
                "country": "Hong Kong",
                "currency": "HKD",
                "market_cap": "$6.17 trillion",
                "stocks": HONGKONG_STOCKS
            },
            "lse": {
                "name": "London Stock Exchange",
                "country": "United Kingdom",
                "currency": "GBP",
                "market_cap": "$3.14 trillion",
                "stocks": LONDON_STOCKS
            },
            "euronext": {
                "name": "Euronext",
                "country": "Europe (NL, FR, BE, IT)",
                "currency": "EUR",
                "market_cap": "$7+ trillion",
                "stocks": EURONEXT_STOCKS
            },
            "tsx": {
                "name": "Toronto Stock Exchange",
                "country": "Canada",
                "currency": "CAD",
                "market_cap": "$4 trillion",
                "stocks": TORONTO_STOCKS
            },
            "nse": {
                "name": "National Stock Exchange",
                "country": "India",
                "currency": "INR",
                "market_cap": "$5.32 trillion",
                "stocks": NSE_INDIA_STOCKS
            },
            "bse": {
                "name": "Bombay Stock Exchange",
                "country": "India",
                "currency": "INR",
                "market_cap": "$5.25 trillion",
                "stocks": BSE_INDIA_STOCKS
            },
            "tadawul": {
                "name": "Saudi Stock Exchange (Tadawul)",
                "country": "Saudi Arabia",
                "currency": "SAR",
                "market_cap": "$2.9 trillion",
                "stocks": TADAWUL_STOCKS
            },
            "adx": {
                "name": "Abu Dhabi Securities Exchange",
                "country": "United Arab Emirates",
                "currency": "AED",
                "market_cap": "$0.7 trillion",
                "stocks": ADX_STOCKS
            },
            "dfm": {
                "name": "Dubai Financial Market",
                "country": "United Arab Emirates",
                "currency": "AED",
                "market_cap": "$0.1 trillion",
                "stocks": DFM_STOCKS
            },
            "qse": {
                "name": "Qatar Stock Exchange",
                "country": "Qatar",
                "currency": "QAR",
                "market_cap": "$0.15 trillion",
                "stocks": QSE_STOCKS
            },
            "boursa_kuwait": {
                "name": "Boursa Kuwait",
                "country": "Kuwait",
                "currency": "KWD",
                "market_cap": "$0.13 trillion",
                "stocks": KUWAIT_STOCKS
            },
            "krx": {
                "name": "Korea Exchange",
                "country": "South Korea",
                "currency": "KRW",
                "market_cap": "$2.2 trillion",
                "stocks": KRX_STOCKS
            },
            "twse": {
                "name": "Taiwan Stock Exchange",
                "country": "Taiwan",
                "currency": "TWD",
                "market_cap": "$2 trillion",
                "stocks": TWSE_STOCKS
            },
            "sgx": {
                "name": "Singapore Exchange",
                "country": "Singapore",
                "currency": "SGD",
                "market_cap": "$0.7 trillion",
                "stocks": SGX_STOCKS
            },
            "asx": {
                "name": "Australian Securities Exchange",
                "country": "Australia",
                "currency": "AUD",
                "market_cap": "$2.5 trillion",
                "stocks": ASX_STOCKS
            },
            "nzx": {
                "name": "New Zealand Exchange",
                "country": "New Zealand",
                "currency": "NZD",
                "market_cap": "$0.1 trillion",
                "stocks": NZX_STOCKS
            },
            "idx": {
                "name": "Indonesia Stock Exchange",
                "country": "Indonesia",
                "currency": "IDR",
                "market_cap": "$0.7 trillion",
                "stocks": IDX_STOCKS
            },
            "set": {
                "name": "Stock Exchange of Thailand",
                "country": "Thailand",
                "currency": "THB",
                "market_cap": "$0.6 trillion",
                "stocks": SET_STOCKS
            },
            "klse": {
                "name": "Bursa Malaysia",
                "country": "Malaysia",
                "currency": "MYR",
                "market_cap": "$0.4 trillion",
                "stocks": KLSE_STOCKS
            },
            "bmv": {
                "name": "Bolsa Mexicana de Valores",
                "country": "Mexico",
                "currency": "MXN",
                "market_cap": "$0.5 trillion",
                "stocks": BMV_STOCKS
            },
            "b3": {
                "name": "Brasil Bolsa Balcão",
                "country": "Brazil",
                "currency": "BRL",
                "market_cap": "$0.9 trillion",
                "stocks": B3_STOCKS
            },
            "jse": {
                "name": "Johannesburg Stock Exchange",
                "country": "South Africa",
                "currency": "ZAR",
                "market_cap": "$1 trillion",
                "stocks": JSE_STOCKS
            },
            "xetra": {
                "name": "Deutsche Börse Xetra",
                "country": "Germany",
                "currency": "EUR",
                "market_cap": "$2.3 trillion",
                "stocks": XETRA_STOCKS
            },
            "six": {
                "name": "SIX Swiss Exchange",
                "country": "Switzerland",
                "currency": "CHF",
                "market_cap": "$1.7 trillion",
                "stocks": SIX_STOCKS
            },
            "tase": {
                "name": "Tel Aviv Stock Exchange",
                "country": "Israel",
                "currency": "ILS",
                "market_cap": "$0.3 trillion",
                "stocks": TASE_STOCKS
            },
            "egx": {
                "name": "Egyptian Exchange",
                "country": "Egypt",
                "currency": "EGP",
                "market_cap": "$45 billion",
                "stocks": EGX_STOCKS
            },
            # European exchanges
            "vienna": {
                "name": "Vienna Stock Exchange",
                "country": "Austria",
                "currency": "EUR",
                "market_cap": "$0.15 trillion",
                "stocks": VIENNA_STOCKS
            },
            "bme": {
                "name": "Bolsa de Madrid",
                "country": "Spain",
                "currency": "EUR",
                "market_cap": "$0.8 trillion",
                "stocks": MADRID_STOCKS
            },
            "dublin": {
                "name": "Euronext Dublin",
                "country": "Ireland",
                "currency": "EUR",
                "market_cap": "$0.1 trillion",
                "stocks": DUBLIN_STOCKS
            },
            "lisbon": {
                "name": "Euronext Lisbon",
                "country": "Portugal",
                "currency": "EUR",
                "market_cap": "$0.075 trillion",
                "stocks": LISBON_STOCKS
            },
            # Nordics
            "copenhagen": {
                "name": "Nasdaq OMX Copenhagen",
                "country": "Denmark",
                "currency": "DKK",
                "market_cap": "$0.4 trillion",
                "stocks": COPENHAGEN_STOCKS
            },
            "helsinki": {
                "name": "Nasdaq OMX Helsinki",
                "country": "Finland",
                "currency": "EUR",
                "market_cap": "$0.2 trillion",
                "stocks": HELSINKI_STOCKS
            },
            "stockholm": {
                "name": "Nasdaq OMX Stockholm",
                "country": "Sweden",
                "currency": "SEK",
                "market_cap": "$0.9 trillion",
                "stocks": STOCKHOLM_STOCKS
            },
            "oslo": {
                "name": "Oslo Stock Exchange",
                "country": "Norway",
                "currency": "NOK",
                "market_cap": "$0.4 trillion",
                "stocks": OSLO_STOCKS
            },
            "iceland": {
                "name": "Nasdaq OMX Iceland",
                "country": "Iceland",
                "currency": "ISK",
                "market_cap": "$0.02 trillion",
                "stocks": ICELAND_STOCKS
            },
            # Baltics
            "tallinn": {
                "name": "Nasdaq OMX Tallinn",
                "country": "Estonia",
                "currency": "EUR",
                "market_cap": "$0.005 trillion",
                "stocks": TALLINN_STOCKS
            },
            "riga": {
                "name": "Nasdaq OMX Riga",
                "country": "Latvia",
                "currency": "EUR",
                "market_cap": "$0.004 trillion",
                "stocks": RIGA_STOCKS
            },
            "vilnius": {
                "name": "Nasdaq OMX Vilnius",
                "country": "Lithuania",
                "currency": "EUR",
                "market_cap": "$0.007 trillion",
                "stocks": VILNIUS_STOCKS
            },
            # Eastern Europe
            "prague": {
                "name": "Prague Stock Exchange",
                "country": "Czech Republic",
                "currency": "CZK",
                "market_cap": "$0.04 trillion",
                "stocks": PRAGUE_STOCKS
            },
            "warsaw": {
                "name": "Warsaw Stock Exchange",
                "country": "Poland",
                "currency": "PLN",
                "market_cap": "$0.17 trillion",
                "stocks": WARSAW_STOCKS
            },
            "budapest": {
                "name": "Budapest Stock Exchange",
                "country": "Hungary",
                "currency": "HUF",
                "market_cap": "$0.03 trillion",
                "stocks": BUDAPEST_STOCKS
            },
            "bucharest": {
                "name": "Bucharest Stock Exchange",
                "country": "Romania",
                "currency": "RON",
                "market_cap": "$0.05 trillion",
                "stocks": BUCHAREST_STOCKS
            },
            "athens": {
                "name": "Athens Stock Exchange",
                "country": "Greece",
                "currency": "EUR",
                "market_cap": "$0.08 trillion",
                "stocks": ATHENS_STOCKS
            },
            "istanbul": {
                "name": "Borsa Istanbul",
                "country": "Turkey",
                "currency": "TRY",
                "market_cap": "$0.2 trillion",
                "stocks": ISTANBUL_STOCKS
            },
            # Canada alt boards
            "tsxv": {
                "name": "TSX Venture Exchange",
                "country": "Canada",
                "currency": "CAD",
                "market_cap": "$0.04 trillion",
                "stocks": [
                    "GTE.V", "PGM.V", "SVM.V", "FCC.V", "ELO.V",
                    "MOZ.V", "LIO.V", "GGD.V", "TUF.V", "NXE.V",
                    "DV.V", "MTA.V", "PYF.V", "AAN.V", "BBB.V",
                ]
            },
            "cse": {
                "name": "Canadian Securities Exchange",
                "country": "Canada",
                "currency": "CAD",
                "market_cap": "$0.01 trillion",
                "stocks": [
                    "CURA.CN", "FIRE.CN", "ACB.CN", "TRUL.CN", "GTII.CN",
                    "HEXO.CN", "APHA.CN", "VFF.CN", "TLRY.CN", "CRON.CN",
                ]
            },
            # Latin America
            "byma": {
                "name": "Buenos Aires Stock Exchange",
                "country": "Argentina",
                "currency": "ARS",
                "market_cap": "$0.02 trillion",
                "stocks": BUENOS_AIRES_STOCKS
            },
            "santiago": {
                "name": "Santiago Stock Exchange",
                "country": "Chile",
                "currency": "CLP",
                "market_cap": "$0.2 trillion",
                "stocks": SANTIAGO_STOCKS
            },
            "bvc": {
                "name": "Colombia Stock Exchange",
                "country": "Colombia",
                "currency": "COP",
                "market_cap": "$0.13 trillion",
                "stocks": COLOMBIA_STOCKS
            },
            # Southeast Asia
            "hose": {
                "name": "Ho Chi Minh Stock Exchange",
                "country": "Vietnam",
                "currency": "VND",
                "market_cap": "$0.18 trillion",
                "stocks": VIETNAM_STOCKS
            },
            "pse": {
                "name": "Philippine Stock Exchange",
                "country": "Philippines",
                "currency": "PHP",
                "market_cap": "$0.25 trillion",
                "stocks": PHILIPPINES_STOCKS
            }
        }
    }


@router.get("/commodities")
async def get_commodities(group_by: str = Query("country")):
    """Return commodities grouped by the provided key (default: country).

    Each commodity includes the latest cached price (if available). If an external
    data provider rate-limits us, the commodity will be returned with price=None.
    """
    from ..data.commodities import COMMODITIES
    from ..data_manager import ExternalRateLimitError

    grouped: Dict[str, List] = {}
    for item in COMMODITIES:
        symbol: Optional[str] = item.get("symbol")
        if symbol is None:
            continue
        price = None
        ts = None
        try:
            # Use a short recent period to get the latest close price
            df = data_manager.fetch_stock_data(symbol, period='5d', interval='1d')
            if not df.empty:
                price = float(df['close'].iloc[-1])
                ts = str(df['timestamp'].iloc[-1])
        except ExternalRateLimitError:
            # Surface rate-limited results as None, frontend can show a notice
            price = None
        except Exception:
            price = None

        enriched = {**item, "price": price, "timestamp": ts}
        key = item.get(group_by) or "Unknown"
        grouped.setdefault(key, []).append(enriched)

    return clean_for_json(grouped)

from ..middleware.simple_rate_limit import rate_limit
from ..utils.timezone_utils import get_request_tz, now_local

@router.get("/predict/{symbol:path}")
async def get_prediction(
    request: Request,
    symbol: str,
    days: float = Query(default=7, ge=0.01, le=30),
    is_crypto: bool = Query(default=False),
    _rl=rate_limit(max_calls=12, period_seconds=60)  # limit to 12 predictions per IP per minute
):
    """
    Get price predictions for a stock or crypto asset
    
    - **symbol**: Ticker symbol (e.g., AAPL, BTC/USDT)
    - **days**: Number of days to predict (0.04=1h, 0.5=12h, 1-30 days)
    - **is_crypto**: Set to true for cryptocurrency
    """
    try:
        # Normalize symbol
        symbol = symbol.upper()
        # Auto-detect crypto if it looks like a crypto pair or contains common crypto suffixes
        suffixes = ['USDT', 'USDC', 'USD']
        if '/' in symbol or any(s in symbol for s in suffixes):
            is_crypto = True
        # Normalize concatenated symbols like BTCUSDT -> BTC/USDT
        if is_crypto and '/' not in symbol:
            for s in suffixes:
                if symbol.endswith(s):
                    base = symbol[:-len(s)]
                    if base:
                        symbol = f"{base}/{s}"
                        break
            else:
                # Fallback to standard USDT pair
                symbol = f"{symbol}/USDT"

        # Determine if this is a short-term (hourly) prediction
        is_short_term = days < 1
        prediction_hours = max(1, int(round(days * 24))) if is_short_term else None
        prediction_days = max(1, int(days)) if not is_short_term else 1
        
        print(f"📊 Processing prediction request for {symbol} ({days} days, hours={prediction_hours}, short_term={is_short_term})")
        
        # Check prediction cache first for fast response
        pred_cache_key = f"{symbol}_{days}_{is_crypto}"
        if pred_cache_key in prediction_cache:
            cache_time = prediction_cache_timestamps.get(pred_cache_key)
            if cache_time and (datetime.now() - cache_time).total_seconds() < PREDICTION_CACHE_SECONDS:
                print(f"⚡ Returning cached prediction for {symbol}")
                return prediction_cache[pred_cache_key]
        
        # Fetch historical data (this is cached by data_manager)
        try:
            if is_crypto:
                df = data_manager.fetch_crypto_data(symbol)
            else:
                df = data_manager.fetch_stock_data(symbol)
        except Exception as e:
            cls = type(e).__name__
            msg = str(e)
            lmsg = msg.lower()
            if cls == 'ExternalRateLimitError' or 'rate limit' in lmsg or 'too many requests' in lmsg:
                raise HTTPException(status_code=429, detail="Data provider is rate-limiting us — please retry in ~60 s.")
            if cls == 'DatabaseError' or 'database' in lmsg or 'disk image is malformed' in lmsg:
                from ..main import _repair_yfinance_cache
                _repair_yfinance_cache()
                raise HTTPException(status_code=503, detail="Data cache was repaired — please retry your request.")
            if 'connection' in lmsg or 'network' in lmsg or 'timeout' in lmsg or 'unreachable' in lmsg:
                raise HTTPException(status_code=503, detail="Data provider is temporarily unreachable — please try again.")
            if isinstance(e, ValueError) or 'no data' in lmsg or 'no timezone' in lmsg:
                raise HTTPException(status_code=404, detail=f"No data found for '{symbol}' — is this a valid ticker?")
            raise HTTPException(status_code=500, detail=msg)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data returned for '{symbol}' — verify the ticker symbol.")
        
        # For short-term predictions, use lightweight quick prediction
        if is_short_term:
            hours: int = prediction_hours or 1
            print(f"⚡ Using quick prediction for {hours}h forecast...")
            result = quick_predict(df, hours, is_crypto, symbol=symbol)
        else:
            # Model cache key - keep models for 6 hours to avoid retraining
            cache_hour = (datetime.now().hour // 6) * 6  # Group into 6-hour blocks
            model_cache_key = f"{symbol}_{datetime.now().strftime('%Y-%m-%d')}_{cache_hour:02d}"
            
            if model_cache_key not in model_cache:
                print(f"🧠 Training new ensemble model for {symbol}...")
                ensemble = EnsemblePredictor(symbol=symbol)
                ensemble.train(df, verbose=False)
                model_cache[model_cache_key] = ensemble
                model_cache_timestamps[model_cache_key] = datetime.now()
                # Clean old cache entries for this symbol
                old_keys = [k for k in list(model_cache.keys()) if k.startswith(f"{symbol}_") and k != model_cache_key]
                for old_key in old_keys:
                    del model_cache[old_key]
                    if old_key in model_cache_timestamps:
                        del model_cache_timestamps[old_key]
            else:
                print(f"⚡ Using cached model for {symbol}")
                ensemble = model_cache[model_cache_key]
            
            # Generate fresh predictions (this is fast)
            result = ensemble.predict(df, prediction_days)
        
        # Get asset info
        asset_info = data_manager.get_asset_info(symbol, is_crypto)
        
        # Get feature importance (only available for full ensemble predictions)
        feature_importance = None
        if not is_short_term and 'ensemble' in dir():
            try:
                feature_importance = ensemble.get_feature_importance()
            except:
                pass
        
        # Get news sentiment for the symbol (included in prediction response)
        news_sentiment = None
        try:
            from ..models.news_sentiment import news_sentiment_analyzer
            sentiment_data = news_sentiment_analyzer.fetch_and_analyze(symbol, limit=5)
            if sentiment_data and not sentiment_data.get('error'):
                news_sentiment = {
                    "direction": sentiment_data.get('overall_direction', 'neutral'),
                    "score": sentiment_data.get('overall_score', 0),
                    "confidence": sentiment_data.get('confidence', 0),
                    "bullish_count": sentiment_data.get('bullish_count', 0),
                    "bearish_count": sentiment_data.get('bearish_count', 0),
                    "headlines": sentiment_data.get('headlines', [])[:3]  # Top 3 headlines
                }
        except Exception as news_err:
            print(f"[News in Prediction] Could not fetch news sentiment: {news_err}")
        
        # Resolve user's timezone for the timestamp
        user_tz = get_request_tz(request)

        # Kimi AI brief — background-cache pattern (no added latency)
        ai_brief = None
        try:
            from ..models.kimi_analyst import get_cached_brief, start_brief_generation
            ai_brief = get_cached_brief(symbol)   # None on first call
            start_brief_generation(symbol, {      # warm cache for next call
                "current_price":   result["current_price"],
                "confidence":      result["confidence"],
                "analysis":        result["analysis"],
                "oracle_signals":  result["analysis"].get("oracle_signals"),
                "news_sentiment":  news_sentiment,
            })
        except Exception as kimi_err:
            print(f"[Kimi brief] {kimi_err}")

        # Council warmup — feeds signal scores to Model Council background thread
        council_verdict = None
        try:
            from ..models.council import get_council_score, get_council_verdict
            oracle_signals = result["analysis"].get("oracle_signals") or {}
            signal_scores = oracle_signals.get("signals") or {}
            council_verdict = get_council_verdict(symbol)
            get_council_score(  # warms cache for next call
                symbol,
                signal_scores,
                result["current_price"],
                result["confidence"],
                "UP" if result["analysis"].get("trend", "").lower() in ("up", "bullish") else "DOWN"
            )
        except Exception as council_err:
            council_verdict = None
            print(f"[Council] {council_err}")

        # Clean NaN/Inf values for JSON serialization
        response = clean_for_json({
            "symbol": symbol,
            "asset_info": asset_info,
            "current_price": result["current_price"],
            "predictions": result["predictions"],
            "dates": result["dates"],
            "confidence": result["confidence"],
            "individual_predictions": result["individual_predictions"],
            "technical_analysis": result.get("technical_analysis"),
            "technical_indicators": result.get("technical_indicators"),
            "analysis": result["analysis"],
            "feature_importance": feature_importance,
            "news_sentiment": news_sentiment,
            "ai_brief": ai_brief,          # Kimi K2.5 trading narrative
            "council_verdict": council_verdict,  # Model Council consensus
            "prediction_type": "quick_hourly" if is_short_term else "full_ensemble",
            "timestamp": now_local(user_tz),
            "timezone": str(user_tz),
        })

        # Cache the response for fast future requests
        prediction_cache[pred_cache_key] = response
        prediction_cache_timestamps[pred_cache_key] = datetime.now()

        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        msg = str(e).lower()
        if "no data" in msg or "not found" in msg or "no ticker" in msg:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found or returned no data.")
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.DatabaseError as e:
        from ..main import _repair_yfinance_cache
        _repair_yfinance_cache()
        raise HTTPException(status_code=503, detail="Data cache repaired — please retry your request.")
    except Exception as e:
        msg = str(e).lower()
        if 'connection' in msg or 'network' in msg or 'timeout' in msg or 'unreachable' in msg:
            raise HTTPException(status_code=503, detail="Data provider temporarily unreachable — please try again.")
        print(f"❌ Error processing {symbol}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/{symbol:path}")
async def get_historical_data(
    request: Request,
    symbol: str,
    period: str = Query(default="1y"),
    is_crypto: bool = Query(default=False)
):
    """Get historical OHLCV data for charting"""
    try:
        symbol = symbol.upper()
        if is_crypto and '/' not in symbol:
            symbol = f"{symbol}/USDT"
        
        # Map frontend periods to yfinance periods and intervals
        period_map = {
            "1h": ("1d", "1m"),      # 1 hour = 1 day data with 1 min interval
            "12h": ("1d", "5m"),     # 12 hours = 1 day data with 5 min interval
            "1d": ("1d", "5m"),      # 1 day = 1 day data with 5 min interval
            "1w": ("5d", "15m"),     # 1 week = 5 days with 15 min interval
            "1mo": ("1mo", "1h"),    # 1 month
            "3mo": ("3mo", "1d"),    # 3 months
            "6mo": ("6mo", "1d"),    # 6 months
            "1y": ("1y", "1d"),      # 1 year
            "5y": ("5y", "1wk"),     # 5 years
            "max": ("max", "1mo"),   # Max
        }
        
        yf_period, interval = period_map.get(period, ("1y", "1d"))

        try:
            if is_crypto:
                df = data_manager.fetch_crypto_data(symbol, period=yf_period, interval=interval)
            else:
                df = data_manager.fetch_stock_data(symbol, period=yf_period, interval=interval)
        except Exception as e:
            cls = type(e).__name__
            msg = str(e)
            lmsg = msg.lower()
            if cls == 'ExternalRateLimitError' or 'rate limit' in lmsg or 'too many requests' in lmsg:
                raise HTTPException(status_code=429, detail="Data provider rate limit — please retry in ~60 s.")
            if cls == 'DatabaseError' or 'disk image is malformed' in lmsg or 'database' in lmsg:
                from ..main import _repair_yfinance_cache
                _repair_yfinance_cache()
                raise HTTPException(status_code=503, detail="Data cache repaired — please retry.")
            if 'connection' in lmsg or 'network' in lmsg or 'timeout' in lmsg:
                raise HTTPException(status_code=503, detail="Data provider temporarily unreachable.")
            if isinstance(e, ValueError) or 'no data' in lmsg:
                raise HTTPException(status_code=404, detail=f"No historical data found for '{symbol}'.")
            raise HTTPException(status_code=500, detail=msg)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No historical data for '{symbol}' — check the ticker.")

        # Clean data for JSON serialization
        df = df.fillna(0).replace([np.inf, -np.inf], 0)
        
        return clean_for_json({
            "symbol": symbol,
            "data": df.to_dict(orient="records"),
            "count": len(df),
            "period": period,
            "interval": interval
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------- Internal test endpoints for DB ----------------------
@router.post('/internal/predictions/test')
async def internal_insert_prediction(symbol: str = Query('AAPL'), days: int = Query(7)):
    """Insert a test prediction into the Supabase/Postgres predictions table for local testing."""
    from sqlalchemy import text
    import json
    try:
        stmt = text("""
            INSERT INTO predictions (user_id, symbol, prediction_days, predicted_prices, model_weights, confidence, metadata)
            VALUES (:u, :s, :d, :p, :m, :c, :md)
            RETURNING id
        """)
        with engine.begin() as conn:
            res = conn.execute(stmt, {
                'u': 'local_test',
                's': symbol,
                'd': days,
                'p': json.dumps([100.0 + i for i in range(days)]),
                'm': json.dumps({'lstm': 0.3, 'xgboost': 0.7}),
                'c': 0.75,
                'md': json.dumps({'source': 'local_test_endpoint'})
            })
            inserted_id = res.scalar()
        return {'inserted_id': inserted_id}
    except Exception as e:
        print(f"[InternalTest] Insert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/internal/predictions')
async def internal_list_predictions(limit: int = Query(10)):
    from sqlalchemy import text
    try:
        stmt = text("SELECT id, user_id, symbol, requested_at, prediction_days, predicted_prices FROM predictions ORDER BY requested_at DESC LIMIT :l")
        with engine.begin() as conn:
            rows = conn.execute(stmt, {'l': limit}).fetchall()
        result = [dict(r) for r in rows]
        return {'rows': result}
    except Exception as e:
        print(f"[InternalTest] Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/internal/db/ping')
async def internal_db_ping():
    """Run a simple SELECT 1 against the configured DATABASE_URL to validate DB connectivity"""
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            r = conn.execute(text("SELECT 1")).scalar()
        return {"ok": True, "result": r}
    except Exception as e:
        print(f"[InternalTest] DB ping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/internal/users')
async def internal_list_users(limit: int = Query(20), db: Session = Depends(get_db)):
    """List users from the application's users table for testing/verification."""
    try:
        users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
        result = [
            {
                'id': u.id,
                'email': u.email,
                'created_at': u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
        return {'rows': result}
    except Exception as e:
        print(f"[InternalTest] users query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/news/{symbol:path}")
async def get_news(symbol: str, limit: int = 5):
    """
    Get recent news headlines for a symbol
    Uses yfinance API (more reliable than scraping)
    """
    try:
        # Clean symbol for yfinance
        yf_symbol = symbol.upper().replace("/", "-").replace("USDT", "-USD")
        if "BTC" in yf_symbol and "-" not in yf_symbol:
             yf_symbol = "BTC-USD"
             
        try:
            ticker = yf.Ticker(yf_symbol)
            news = ticker.news
            
            headlines = []
            if news:
                for item in news[:limit]:
                    title = item.get('title')
                    if not title and 'content' in item:
                        title = item['content'].get('title')
                    
                    if title:
                        headlines.append(title)
            
            # Fallback if empty
            if not headlines:
                 # Check related symbols if crypto
                 if "BTC" in symbol:
                     headlines = ["Bitcoin market volatility increases", "Crypto regulations update", "Institutional interest in BTC grows"]
                 else:
                     headlines = [f"Market analysis for {symbol}", f"{symbol} trading volume update", "Sector performance report"]

            return {
                "symbol": symbol,
                "headlines": headlines,
                "source": "Yahoo Finance API",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[News Error] {e}")
            return {
                "symbol": symbol,
                "headlines": [
                    f"Latest updates for {symbol}",
                    "Market limits volatility",
                    "Trading patterns analysis"
                ],
                "source": "Generated Fallback",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news-sentiment/{symbol:path}")
async def get_news_sentiment(symbol: str, limit: int = 10):
    """
    Get news sentiment analysis for a symbol
    Returns sentiment scores, direction, and confidence that influences predictions
    """
    try:
        from ..models.news_sentiment import news_sentiment_analyzer
        
        sentiment = news_sentiment_analyzer.fetch_and_analyze(symbol, limit)
        adjustment = news_sentiment_analyzer.get_prediction_adjustment(sentiment)
        
        return {
            "symbol": symbol,
            "sentiment": sentiment,
            "prediction_adjustment": adjustment,
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError:
        return {
            "symbol": symbol,
            "error": "News sentiment analyzer not available",
            "sentiment": {"overall_direction": "neutral", "overall_score": 0, "confidence": 0},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"[News Sentiment API Error] {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "sentiment": {"overall_direction": "neutral", "overall_score": 0, "confidence": 0},
            "timestamp": datetime.now().isoformat()
        }


@router.get("/quote/{symbol:path}")
async def get_realtime_quote(symbol: str):
    """
    Get ultra-fast real-time price data (optimized for 1s polling)
    Uses caching to reduce API calls while maintaining accuracy
    """
    try:
        symbol_upper = symbol.upper()
        
        # Check cache first (valid for 500ms)
        if symbol_upper in realtime_cache:
            cache_time = cache_timestamps.get(symbol_upper)
            if cache_time and (datetime.now() - cache_time).total_seconds() * 1000 < CACHE_TTL_MS:
                cached = realtime_cache[symbol_upper].copy()
                cached['timestamp'] = datetime.now().isoformat()
                cached['cached'] = True
                return cached
        
        # Handle crypto symbols (BTC/USDT -> BTC-USD)
        if "/" in symbol_upper and "USDT" in symbol_upper:
            yf_symbol = symbol_upper.replace("/USDT", "-USD")
        elif "/" in symbol_upper:
            yf_symbol = symbol_upper.replace("/", "-")
        else:
            yf_symbol = symbol_upper
            
        # Ensure BTC uses proper yfinance format
        if yf_symbol == "BTC" or yf_symbol.startswith("BTC-") and "USD" not in yf_symbol:
            yf_symbol = "BTC-USD"
        
        ticker = yf.Ticker(yf_symbol)
        
        # Fast info is faster than history
        info = ticker.fast_info
        
        # Use last_price if available, otherwise fallback
        price = info.last_price
        prev_close = info.previous_close
        open_price = info.open
        day_high = info.day_high
        day_low = info.day_low
        volume = info.last_volume
        
        if not price:
            # Fallback to history
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                if not prev_close:
                    prev_close = float(hist['Open'].iloc[0])
                if not open_price:
                    open_price = float(hist['Open'].iloc[0])
                if not day_high:
                    day_high = float(hist['High'].max())
                if not day_low:
                    day_low = float(hist['Low'].min())
                if not volume:
                    volume = float(hist['Volume'].sum())
        
        change = 0.0
        change_percent = 0.0
        
        if price and prev_close:
            change = price - prev_close
            change_percent = (change / prev_close) * 100
        
        result = {
            "symbol": symbol,
            "price": float(price or 0.0),
            "change": float(change),
            "change_percent": float(change_percent),
            "open": float(open_price or price or 0.0),
            "high": float(day_high or price or 0.0),
            "low": float(day_low or price or 0.0),
            "prev_close": float(prev_close or 0.0),
            "volume": int(volume or 0),
            "timestamp": datetime.now().isoformat(),
            "cached": False
        }
        
        # Update cache
        realtime_cache[symbol_upper] = result
        cache_timestamps[symbol_upper] = datetime.now()
        
        return result
        
    except Exception as e:
        # Don't crash on polling errors, just return nulls
        return {
            "symbol": symbol,
            "price": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "error": str(e)
        }


@router.websocket("/ws/{symbol:path}")
async def websocket_realtime(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time price streaming.
    Sends price updates every second.
    """
    await manager.connect(websocket, symbol.upper())
    try:
        while True:
            # Get fresh quote
            quote_data = await get_realtime_quote(symbol)
            
            # Send to client
            await websocket.send_json(quote_data)
            
            # Wait 1 second before next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol.upper())
    except Exception as e:
        print(f"WebSocket error for {symbol}: {e}")
        manager.disconnect(websocket, symbol.upper())

from fastapi.responses import StreamingResponse
import json as _json

# ── SSE Real-time price stream ─────────────────────────────────────────────────
@router.get("/prices/stream")
async def price_stream(
    symbols: str = Query(default="AAPL,BTC/USDT,TSLA,NVDA,ETH/USDT"),
    request: Request = None,
):
    """
    Server-Sent Events endpoint. Streams live price ticks every 3 seconds.
    Usage: const es = new EventSource('/api/prices/stream?symbols=AAPL,BTC/USDT')
    """
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:20]

    async def generate():
        from ..agents.realtime_feed import realtime_feed
        import asyncio as _asyncio

        while True:
            if await request.is_disconnected():
                break
            ticks = {}
            for sym in sym_list:
                tick = realtime_feed.get_tick(sym)
                if tick:
                    ticks[sym] = {
                        "price": tick.get("price"),
                        "change_pct": tick.get("change_pct"),
                        "volume": tick.get("volume"),
                        "momentum": tick.get("momentum_20t"),
                        "ts": tick.get("ts"),
                    }
            data = _json.dumps({"ticks": ticks, "ts": datetime.utcnow().isoformat()})
            yield f"data: {data}\n\n"
            await _asyncio.sleep(3)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/prices/snapshot")
async def price_snapshot(
    symbols: str = Query(default="AAPL,BTC/USDT,TSLA,NVDA,ETH/USDT,MSFT,SOL/USDT"),
):
    """Fast JSON snapshot of latest prices. No streaming."""
    from ..agents.realtime_feed import realtime_feed
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:30]
    result = {}
    for sym in sym_list:
        tick = realtime_feed.get_tick(sym)
        if tick:
            result[sym] = {
                "price": tick.get("price"),
                "change_pct": tick.get("change_pct"),
                "volume": tick.get("volume"),
                "ts": tick.get("ts"),
            }
    return {"prices": result, "count": len(result)}


@router.get("/performance/accuracy")
async def get_accuracy_stats():
    """Return prediction accuracy stats from the self-learning feedback loop."""
    try:
        from ..agents.feedback_loop import feedback_loop
        return feedback_loop.get_accuracy_summary()
    except Exception as e:
        return {"error": str(e), "message": "Feedback loop not yet initialized"}


@router.get("/performance/recent")
async def get_recent_outcomes(symbol: Optional[str] = None, limit: int = Query(default=20, le=100)):
    """Return recent evaluated predictions with actual vs predicted prices."""
    try:
        from ..agents.feedback_loop import feedback_loop
        return {"outcomes": feedback_loop.get_recent_outcomes(symbol=symbol, limit=limit)}
    except Exception as e:
        return {"outcomes": [], "error": str(e)}


@router.delete("/cache/{symbol:path}")
async def clear_cache(symbol: str):
    """Clear cached model for a symbol"""
    from urllib.parse import unquote
    symbol = unquote(symbol).upper()
    data_manager.clear_cache(symbol)
    
    # Clear model cache
    keys_to_remove = [k for k in model_cache if symbol in k]
    for key in keys_to_remove:
        del model_cache[key]
    
    return {"message": f"Cache cleared for {symbol}"}


def validate_symbol(symbol: str):
    """
    Security: Validate symbol format to prevent injection attacks
    Allow: Uppercase letters, numbers, dot, dash, equals, slash
    """
    if not re.match(r'^[A-Z0-9\-\.\=\/]+$', symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format. Potential injection detected.")
    return True


@router.get("/search")
async def search_assets(query: str):
    """
    Global Asset Search using Yahoo Finance
    """
    try:
        # Basic sanitization
        query = re.sub(r'[^a-zA-Z0-9\-\.\= ]', '', query)
        
        # Use yfinance Ticker to search (or just check existence)
        # yfinance doesn't have a broad search, so we check if the exact ticker exists
        # Or better, we can assume valid if yf.Ticker(query).info returns data
        
        # For a better search experience, we might want to just pass the query if it looks like a ticker
        # But to be helpful, let's try to fetch info
        
        ticker = yf.Ticker(query)
        info = ticker.fast_info
        
        # Check if it has a price (implies existence)
        if info.last_price:
            return {
                "symbol": query.upper(),
                "name": query.upper(), # yfinance fast_info often lacks name, kept simple
                "type": info.currency,
                "price": info.last_price,
                "exists": True
            }
        else:
            return {"exists": False, "symbol": query}
            
    except Exception as e:
        print(f"Search error: {e}")
        return {"exists": False, "error": str(e)}


@router.get("/scan/opportunities")
async def scan_market_opportunities():
    """
    AI Surveillance: returns the latest cached scan results (updated every 6 h).
    The background thread runs at startup and then every 6 hours automatically.
    """
    with _scan_cache_lock:
        cache = dict(_scan_cache)
    return {
        "opportunities": cache["opportunities"],
        "all_results":   cache.get("all_results", []),
        "scan_count":    cache["scan_count"],
        "last_run":      cache["last_run"],
        "next_run":      cache["next_run"],
        "status":        cache["status"],
    }


@router.post("/scan/refresh")
async def trigger_scan_refresh():
    """Force an immediate re-scan (runs in background, returns immediately)."""
    t = _threading.Thread(target=_do_market_scan, daemon=True, name="ai-scanner-manual")
    t.start()
    return {"status": "scan_started", "message": "Scan running in background — check /scan/opportunities in ~30 s"}


@router.get("/scan/exchanges")
async def get_exchanges_overview():
    """List all exchanges with scan status and buy-signal counts."""
    with _exchange_caches_lock:
        snapshot = {k: dict(v) for k, v in _exchange_caches.items()}
    return [
        {
            "id":           ex_id,
            "name":         _EXCHANGE_REGISTRY[ex_id]["name"],
            "full_name":    _EXCHANGE_REGISTRY[ex_id]["full_name"],
            "flag":         _EXCHANGE_REGISTRY[ex_id]["flag"],
            "currency":     _EXCHANGE_REGISTRY[ex_id]["currency"],
            "total_stocks": len(_EXCHANGE_REGISTRY[ex_id]["symbols"]),
            "buy_signals":  len(snapshot[ex_id]["buy_signals"]),
            "scan_count":   snapshot[ex_id]["scan_count"],
            "last_run":     snapshot[ex_id]["last_run"],
            "status":       snapshot[ex_id]["status"],
        }
        for ex_id in _EXCHANGE_REGISTRY
    ]


@router.get("/scan/exchange/{exchange_id}")
async def get_exchange_scan(exchange_id: str):
    """Get full prediction results for one exchange."""
    if exchange_id not in _EXCHANGE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Exchange '{exchange_id}' not found")
    with _exchange_caches_lock:
        cache = dict(_exchange_caches[exchange_id])
    ex = _EXCHANGE_REGISTRY[exchange_id]
    return {
        "exchange_id":   exchange_id,
        "name":          ex["name"],
        "full_name":     ex["full_name"],
        "flag":          ex["flag"],
        "results":       cache["results"],
        "buy_signals":   cache["buy_signals"],
        "last_run":      cache["last_run"],
        "next_run":      cache["next_run"],
        "status":        cache["status"],
        "scan_count":    cache["scan_count"],
        "total_symbols": len(ex["symbols"]),
    }


@router.post("/scan/exchange/{exchange_id}/refresh")
async def refresh_exchange_scan(exchange_id: str):
    """Force an immediate re-scan for one exchange."""
    if exchange_id not in _EXCHANGE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Exchange '{exchange_id}' not found")
    t = _threading.Thread(
        target=_do_exchange_scan, args=(exchange_id,),
        daemon=True, name=f"manual-scan-{exchange_id}"
    )
    t.start()
    return {"status": "scan_started", "exchange": exchange_id,
            "message": f"Scanning {_EXCHANGE_REGISTRY[exchange_id]['name']} in background"}


# ====================
# AI CHATBOT ENDPOINTS
# ====================

class ChatRequest(BaseModel):
    message: str
    symbol: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    symbol: Optional[str] = None
    intent: str
    disclaimer_shown: bool = True
    analysis: Optional[dict] = None


@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """
    AI Chatbot endpoint for stock market advice
    
    Send a natural language message and get intelligent buy/sell recommendations.
    
    Examples:
    - "Should I buy Apple stock?"
    - "Analyze TSLA"
    - "Is it time to sell NVDA?"
    - "Price target for Microsoft"
    
    DISCLAIMER: All responses are for educational purposes only and do not
    constitute financial advice. Users accept full responsibility for their
    investment decisions.
    """
    try:
        message = request.message.strip()
        if not message:
            return {
                "response": "Please enter a message. Ask me about any stock!",
                "intent": "error",
                "disclaimer_shown": True
            }
        
        # Process message with chatbot
        result = await stock_chatbot.process_message(message)
        
        # If chatbot needs market data, fetch it
        if result.get('needs_data') and result.get('symbol'):
            symbol = result['symbol']
            is_crypto = '/' in symbol or any(c in symbol for c in ['BTC', 'ETH', 'USDT'])
            
            # Fetch market data
            if is_crypto:
                if '/' not in symbol:
                    symbol = f"{symbol}/USDT"
                df = data_manager.fetch_crypto_data(symbol)
            else:
                df = data_manager.fetch_stock_data(symbol)
            
            if not df.empty:
                # Prepare market data for chatbot
                market_data = {
                    'data': df.to_dict(orient='records'),
                    'symbol': symbol
                }
                
                # Re-process with market data
                result = await stock_chatbot.process_message(message, market_data)
            else:
                result['response'] = f"❌ Could not fetch data for {symbol}. Please check the ticker symbol and try again."
        
        # Clean any analysis data for JSON
        if result.get('analysis'):
            result['analysis'] = clean_for_json(result['analysis'])
        
        return {
            "response": result.get('response', 'I couldn\'t process that request. Please try again.'),
            "symbol": result.get('symbol'),
            "intent": result.get('intent', 'unknown'),
            "disclaimer_shown": True,
            "analysis": result.get('analysis'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        traceback.print_exc()
        return {
            "response": f"⚠️ An error occurred while processing your request. Please try again.\n\nError: {str(e)}",
            "intent": "error",
            "disclaimer_shown": True
        }


@router.get("/chat/quick/{symbol:path}")
async def quick_recommendation(symbol: str):
    """
    Get a quick one-line recommendation for a symbol
    """
    try:
        symbol = symbol.upper()
        is_crypto = '/' in symbol or any(c in symbol for c in ['BTC', 'ETH', 'USDT'])
        
        if is_crypto and '/' not in symbol:
            symbol = f"{symbol}/USDT"
        
        # Fetch data
        if is_crypto:
            df = data_manager.fetch_crypto_data(symbol)
        else:
            df = data_manager.fetch_stock_data(symbol)
        
        if df.empty:
            return {"error": f"No data for {symbol}"}
        
        # Get news sentiment
        news_sentiment = None
        try:
            from ..models.news_sentiment import news_sentiment_analyzer
            news_sentiment = news_sentiment_analyzer.fetch_and_analyze(symbol.split('/')[0])
        except:
            pass
        
        # Get enhanced prediction (news_sentiment defaults to {} if unavailable)
        analysis = get_enhanced_prediction(df, symbol, days=7, news_sentiment=news_sentiment or {})
        
        # Get quick recommendation
        quick_rec = stock_chatbot.get_quick_recommendation(symbol, analysis)
        
        return {
            "symbol": symbol,
            "recommendation": quick_rec,
            "prediction": clean_for_json(analysis.get('final_prediction', {})),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Quick recommendation error: {e}")
        return {"error": str(e)}


@router.get("/enhanced-predict/{symbol:path}")
async def get_enhanced_prediction_endpoint(
    symbol: str,
    days: int = Query(default=7, ge=1, le=30),
    is_crypto: bool = Query(default=False)
):
    """
    Get enhanced prediction using all models (Random Forest, GB, SVM, etc.)
    This provides more detailed analysis than the standard prediction endpoint.
    """
    try:
        symbol = symbol.upper()
        if is_crypto and '/' not in symbol:
            symbol = f"{symbol}/USDT"
        
        # Fetch data
        if is_crypto:
            df = data_manager.fetch_crypto_data(symbol)
        else:
            df = data_manager.fetch_stock_data(symbol)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        
        # Get news sentiment
        news_sentiment = None
        try:
            from ..models.news_sentiment import news_sentiment_analyzer
            news_sentiment = news_sentiment_analyzer.fetch_and_analyze(symbol.split('/')[0])
        except:
            pass
        
        # Get enhanced prediction (news_sentiment defaults to {} if unavailable)
        result = get_enhanced_prediction(df, symbol, days=days, news_sentiment=news_sentiment or {})
        
        return clean_for_json({
            "symbol": symbol,
            "prediction": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Enhanced prediction error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ====================================================================================
# AGENT SYSTEM ENDPOINTS
# ====================================================================================

@router.get("/agents/status")
async def get_agent_status():
    """
    Returns the status of all background agents:
    - Prediction loop stats (cycles, symbols cached, running state)
    - Master agent last scan summary
    """
    try:
        from ..agents.prediction_loop import prediction_loop
        from ..agents.master_agent import master_agent

        loop_stats = prediction_loop.get_stats()
        last_scan = master_agent.get_last_scan()

        return clean_for_json({
            "prediction_loop": loop_stats,
            "last_market_scan": {
                "scan_timestamp": last_scan.get("scan_timestamp"),
                "symbols_scanned": last_scan.get("symbols_scanned", 0),
                "market_bias": last_scan.get("market_bias", "UNKNOWN"),
                "buy_signals": last_scan.get("buy_signals", 0),
                "sell_signals": last_scan.get("sell_signals", 0),
            },
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@router.get("/agents/predictions")
async def get_all_cached_predictions():
    """
    Return all predictions currently cached by the continuous prediction loop.
    These are ultra-fast (no ML compute required) — data is always fresh.
    """
    try:
        from ..agents.prediction_loop import get_all_predictions
        preds = get_all_predictions()
        return clean_for_json({
            "total": len(preds),
            "predictions": preds,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/predict/{symbol:path}")
async def get_agent_prediction(symbol: str):
    """
    Get the latest cached prediction for a symbol from the prediction loop.
    If the symbol hasn't been predicted yet, triggers an immediate prediction.
    """
    try:
        from ..agents.prediction_loop import get_latest_prediction, prediction_loop
        symbol_upper = symbol.upper()

        result = get_latest_prediction(symbol_upper)
        if not result:
            # Trigger immediate prediction
            result = prediction_loop.predict_now(symbol_upper)

        if not result:
            raise HTTPException(status_code=404, detail=f"Could not predict {symbol_upper}")

        return clean_for_json(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/scan")
async def run_market_scan(force: bool = Query(default=False)):
    """
    Run the multi-agent market scanner across all default symbols.
    Returns top trade opportunities ranked by composite score.

    Each result includes:
    - Composite score (-100 to +100)
    - Grade (A+ to F)
    - Entry / Stop-loss / Target prices
    - Per-agent breakdown (Technical, Momentum, Volume, Breakout, Sentiment, Fundamental, Macro)
    - Key reasons for the signal

    Cached for 10 minutes unless force=true.
    """
    try:
        from ..agents.master_agent import master_agent

        # Run in thread pool (scan is CPU/IO intensive)
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: master_agent.full_market_scan(force=force)
        )

        return clean_for_json(result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/analyze/{symbol:path}")
async def analyze_symbol_agents(symbol: str):
    """
    Run all 7 scanner agents against a single symbol and return the full breakdown.
    Includes composite score, trade setup, and per-agent reasoning.
    """
    try:
        from ..agents.master_agent import master_agent

        symbol_upper = symbol.upper()
        validate_symbol(symbol_upper.replace("/", "").replace("-", ""))

        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: master_agent.analyze_symbol(symbol_upper)
        )

        return clean_for_json(result)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/opportunities")
async def get_best_opportunities(
    min_score: float = Query(default=25.0, ge=0, le=100),
    min_confidence: float = Query(default=60.0, ge=0, le=100),
    max_results: int = Query(default=10, ge=1, le=50),
):
    """
    Get the best current trade opportunities from the master agent.
    Filters by minimum composite score and minimum confidence.
    Returns structured trade setups with entry, stop, and targets.
    """
    try:
        from ..agents.master_agent import master_agent

        # Use cached scan results
        last_scan = master_agent.get_last_scan()
        all_results = last_scan.get("all_results", [])

        if not all_results:
            # Trigger a quick scan of tier-1 assets
            symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN",
                       "BTC/USDT", "ETH/USDT", "SOL/USDT"]
            import asyncio
            loop = asyncio.get_event_loop()
            all_results = await loop.run_in_executor(
                None,
                lambda: master_agent.scan_symbols(symbols, max_parallel=6)
            )

        # Filter opportunities
        opportunities = []
        for r in all_results:
            score = abs(r.get("composite_score", 0.0))
            conf = r.get("overall_confidence", 0.0)
            if score >= min_score and conf >= min_confidence:
                opp = r.get("trade_opportunity", {})
                if opp:
                    opp["overall_confidence"] = conf
                    opportunities.append(opp)

        # Sort by abs composite score
        opportunities.sort(key=lambda x: abs(x.get("composite_score", 0)), reverse=True)

        return clean_for_json({
            "opportunities": opportunities[:max_results],
            "total_found": len(opportunities),
            "min_score_filter": min_score,
            "min_confidence_filter": min_confidence,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/web-search")
async def web_search_financial(
    query: str = Query(..., min_length=3, max_length=200),
    symbol: Optional[str] = None,
):
    """
    Multi-source financial web search.
    Queries 6+ verified financial domains simultaneously:
    Yahoo Finance, Reuters, CNBC, MarketWatch, Finviz, Investing.com

    For symbol-specific queries, also returns real-time fundamentals from Finviz.
    """
    try:
        from ..agents.web_search import web_searcher

        import asyncio
        loop = asyncio.get_event_loop()

        if symbol:
            result = await loop.run_in_executor(
                None,
                lambda: web_searcher.search_symbol_news(symbol.upper(), max_sources=6)
            )
        else:
            result = await loop.run_in_executor(
                None,
                lambda: web_searcher.search_question(query, max_sources=6)
            )

        return clean_for_json(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ====================================================================================
# SELF-LEARNING FEEDBACK LOOP ENDPOINTS
# ====================================================================================

@router.get("/learning/summary")
async def get_learning_summary():
    """
    Full accuracy and learning summary for the self-improving prediction system.

    Returns:
    - Overall directional accuracy (last 30 days)
    - Per-model MAE% and directional accuracy
    - Current learned ensemble weights (updated automatically as predictions are evaluated)
    - Current learned scanner agent weights
    - Total predictions recorded and outcomes evaluated
    """
    try:
        from ..agents.feedback_loop import feedback_loop
        return clean_for_json(feedback_loop.get_accuracy_summary())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/model-metrics")
async def get_model_metrics():
    """
    Per-model accuracy metrics computed from real outcomes vs predictions.
    Updates every time a prediction horizon passes (1d, 3d, 7d after prediction).
    """
    try:
        from ..agents.feedback_loop import feedback_loop
        return clean_for_json({
            "model_metrics": feedback_loop.get_model_metrics(),
            "current_weights": feedback_loop.get_model_weights(),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/agent-metrics")
async def get_agent_metrics():
    """
    Per-scanner-agent accuracy metrics showing which signal generators are most reliable.
    Weights are updated automatically as agent signals are back-tested.
    """
    try:
        from ..agents.feedback_loop import feedback_loop
        return clean_for_json({
            "agent_metrics": feedback_loop.get_agent_metrics(),
            "current_weights": feedback_loop.get_agent_weights(),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/outcomes")
async def get_recent_outcomes(
    symbol: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Recent prediction outcomes: actual price vs predicted price, direction accuracy.
    Optionally filter by symbol. Shows the raw learning data feeding the model.
    """
    try:
        from ..agents.feedback_loop import feedback_loop
        outcomes = feedback_loop.get_recent_outcomes(symbol=symbol, limit=limit)
        return clean_for_json({
            "outcomes": outcomes,
            "total": len(outcomes),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/evaluate-now")
async def trigger_evaluation():
    """
    Force an immediate evaluation cycle (normally runs hourly automatically).
    Useful for testing the learning system or after a major market event.
    Returns newly evaluated outcomes and updated weights.
    """
    try:
        from ..agents.feedback_loop import feedback_loop
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, feedback_loop.force_evaluate_now)
        return clean_for_json(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/weight-history")
async def get_weight_history():
    """
    Current learned weights vs default weights — shows how much the system has learned.
    """
    try:
        from ..agents.feedback_loop import feedback_loop
        from ..config import DEFAULT_WEIGHTS

        learned = feedback_loop.get_model_weights()
        default = DEFAULT_WEIGHTS.copy()

        comparison = {}
        for model in set(list(learned.keys()) + list(default.keys())):
            l_w = learned.get(model, 0.0)
            d_w = default.get(model, 0.0)
            comparison[model] = {
                "default_weight": round(d_w, 4),
                "learned_weight": round(l_w, 4),
                "change": round(l_w - d_w, 4),
                "change_pct": round((l_w - d_w) / (d_w + 1e-9) * 100, 1),
            }

        return clean_for_json({
            "weight_comparison": comparison,
            "using_learned_weights": len(feedback_loop.get_model_metrics()) >= 3,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Real-Time Price Feed ─────────────────────────────────────────────────────

@router.get("/realtime/price/{symbol}")
async def get_realtime_price(symbol: str):
    """
    Return the latest real-time price for a symbol.
    Crypto: fetched via ccxt Binance (5s cache).
    Stocks: fetched via yfinance fast_info (60s cache).
    """
    try:
        from ..agents.realtime_feed import realtime_feed
        tick = realtime_feed.get_tick(symbol.upper())
        if tick is None:
            raise HTTPException(status_code=404, detail=f"Could not fetch price for {symbol}")
        return clean_for_json(tick)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/prices")
async def get_all_realtime_prices(
    symbols: str = Query(default="", description="Comma-separated symbols. Empty = return all cached")
):
    """
    Return real-time prices for multiple symbols.
    Pass ?symbols=AAPL,TSLA,BTC/USDT or omit for all cached ticks.
    """
    try:
        from ..agents.realtime_feed import realtime_feed
        if symbols.strip():
            sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
            result = {}
            for sym in sym_list:
                tick = realtime_feed.get_tick(sym)
                if tick:
                    result[sym] = tick
        else:
            result = realtime_feed.get_all_ticks()

        return clean_for_json({
            "prices": result,
            "count": len(result),
            "timestamp": datetime.now().isoformat(),
            "feed_stats": realtime_feed.get_stats(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/signal/{symbol}")
async def get_realtime_signal(symbol: str):
    """
    Return Kalman filter + Wavelet trend signal for a symbol.
    Useful for short-term momentum confirmation.
    """
    try:
        from ..data_manager import data_manager
        from ..models.kalman_filter import KalmanPriceFilter
        from ..models.wavelet_features import WaveletDecomposer
        from ..agents.realtime_feed import realtime_feed

        sym = symbol.upper()
        is_crypto = "/" in sym or any(
            c in sym for c in ["BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "USDT"]
        )
        if is_crypto:
            clean_sym = sym if "/" in sym else f"{sym}/USDT"
            df = data_manager.fetch_crypto_data(clean_sym, timeframe="1d", limit=60)
        else:
            df = data_manager.fetch_stock_data(sym, period="3mo", interval="1d")

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {sym}")

        df.columns = [c.lower() for c in df.columns]

        kf = KalmanPriceFilter()
        wd = WaveletDecomposer()

        kalman_signal = kf.get_trend_signal(df)
        wavelet_signal = wd.get_signal(df)

        # Enrich with live price
        live_price = realtime_feed.get_price(sym)

        return clean_for_json({
            "symbol": sym,
            "live_price": live_price,
            "kalman": kalman_signal,
            "wavelet": wavelet_signal,
            "combined_score": round(
                kalman_signal.get("score", 0) * 0.6 + wavelet_signal.get("score", 0) * 0.4, 2
            ),
            "timestamp": datetime.now().isoformat(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
