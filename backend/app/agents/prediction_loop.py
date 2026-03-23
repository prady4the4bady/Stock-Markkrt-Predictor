"""
NexusTrader - Continuous Prediction Loop
Runs 24/7 in a daemon thread, predicting all symbols in batches with no downtime.

Key properties:
- Never crashes: every symbol wrapped in try/except, loop restarts on unexpected errors
- No blocking: entirely in a background daemon thread, FastAPI never waits
- Low latency: warm predictions stored in-memory; API reads without re-computing
- Parallel: each batch uses ThreadPoolExecutor for concurrent symbol prediction
- Smart backoff: rate-limit friendly — small sleep between symbols
"""

import time
import threading
import queue
import traceback
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Shared prediction store — read by API endpoints for instant responses
# ─────────────────────────────────────────────────────────────────────────────
_prediction_store: Dict[str, Dict] = {}   # symbol → latest prediction
_store_lock = threading.Lock()


def get_latest_prediction(symbol: str) -> Optional[Dict]:
    """Thread-safe read of the latest cached prediction."""
    with _store_lock:
        return _prediction_store.get(symbol.upper())


def get_all_predictions() -> Dict[str, Dict]:
    """Return a snapshot of all current predictions."""
    with _store_lock:
        return dict(_prediction_store)


def get_prediction_count() -> int:
    with _store_lock:
        return len(_prediction_store)


# ─────────────────────────────────────────────────────────────────────────────
# Prediction worker — runs one symbol
# ─────────────────────────────────────────────────────────────────────────────

def _predict_symbol(symbol: str) -> Optional[Dict]:
    """
    Fetch data and run the full ensemble prediction for one symbol.
    Returns a standardised prediction dict or None on failure.
    """
    try:
        from ..data_manager import data_manager
        from ..models.ensemble import EnsemblePredictor

        # Fetch OHLCV
        is_crypto = "/" in symbol or any(
            c in symbol for c in ["BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "DOT", "USDT"]
        )
        if is_crypto:
            clean = symbol if "/" in symbol else f"{symbol}/USDT"
            df = data_manager.fetch_crypto_data(clean, timeframe="1d", limit=365)
        else:
            df = data_manager.fetch_stock_data(symbol, period="1y", interval="1d")

        if df is None or df.empty:
            return None

        df.columns = [c.lower() for c in df.columns]

        # Instantiate a fresh ensemble predictor per run
        # (they self-cache models internally for 6h — this just dispatches)
        predictor = EnsemblePredictor()
        result = predictor.predict(df, days=7)

        if not result:
            return None

        predictions = result.get("predictions", [])
        direction = result.get("direction", "neutral")
        confidence = result.get("confidence", 50.0)
        current_price = float(df["close"].iloc[-1])

        # Extract per-model predictions for feedback recording
        individual = result.get("individual_predictions", {})
        model_preds = {m: v.get("values", []) for m, v in individual.items()}
        weights_used = {m: v.get("weight", 0.2) for m, v in individual.items()}

        # ── Record to self-learning feedback store ──────────────────────────
        try:
            from .feedback_loop import feedback_loop
            feedback_loop.record_prediction(
                symbol=symbol,
                current_price=current_price,
                predictions=predictions,
                direction=direction,
                confidence=confidence,
                model_preds=model_preds,
                weights_used=weights_used,
            )
        except Exception as fe:
            print(f"[PredictionLoop] Feedback record failed for {symbol}: {fe}")

        return {
            "symbol": symbol,
            "current_price": current_price,
            "predictions": predictions,
            "confidence": confidence,
            "direction": direction,
            "recommendation": result.get("recommendation", "HOLD"),
            "predicted_change_pct": result.get("price_change_pct", 0.0),
            "model_count": len(individual),
            "risk_metrics": result.get("risk_metrics", {}),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"[PredictionLoop] {symbol} failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# PredictionLoop class
# ─────────────────────────────────────────────────────────────────────────────

class PredictionLoop:
    """
    Continuous background prediction engine.
    - Processes symbols in batches of `batch_size` using a thread pool.
    - Rotates through ALL symbols then immediately restarts.
    - Pauses `inter_symbol_sleep` seconds between symbols (rate-limit friendly).
    - Never exits — any unhandled exception restarts the loop after a short delay.
    """

    def __init__(
        self,
        batch_size: int = 5,
        inter_symbol_sleep: float = 0.5,
        batch_sleep: float = 2.0,
        max_workers: int = 5,
    ):
        self.batch_size = batch_size
        self.inter_symbol_sleep = inter_symbol_sleep
        self.batch_sleep = batch_sleep
        self.max_workers = max_workers

        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Runtime statistics
        self.stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "cycles_completed": 0,
            "started_at": None,
            "last_cycle_at": None,
            "symbols_covered": 0,
        }
        self._stats_lock = threading.Lock()

    # ── Internals ────────────────────────────────────────────────────────────

    def _build_tiered_symbols(self) -> Dict[str, List[str]]:
        """
        Build a three-tier symbol registry from all configured exchanges.

        Tier 1 — highest liquidity globally, run every cycle   (~80 symbols)
        Tier 2 — regional blue-chips + mid-cap crypto, every 2nd cycle (~300)
        Tier 3 — long-tail: all remaining exchange stocks, every 3rd cycle (~2000+)

        Returns dict with keys 't1', 't2', 't3'.
        """
        try:
            from ..config import (
                DEFAULT_CRYPTO, NYSE_STOCKS, NASDAQ_STOCKS,
                # Asia Pacific
                TOKYO_STOCKS, HONGKONG_STOCKS, KRX_STOCKS, TWSE_STOCKS,
                SGX_STOCKS, ASX_STOCKS, NZX_STOCKS, IDX_STOCKS, SET_STOCKS,
                KLSE_STOCKS,
                # China
                SHANGHAI_STOCKS, SHENZHEN_STOCKS,
                # India
                NSE_INDIA_STOCKS, BSE_INDIA_STOCKS,
                # Europe
                LONDON_STOCKS, EURONEXT_STOCKS, XETRA_STOCKS, SIX_STOCKS,
                MADRID_STOCKS, VIENNA_STOCKS, COPENHAGEN_STOCKS, HELSINKI_STOCKS,
                STOCKHOLM_STOCKS, OSLO_STOCKS, ICELAND_STOCKS,
                PRAGUE_STOCKS, WARSAW_STOCKS, BUDAPEST_STOCKS, BUCHAREST_STOCKS,
                ATHENS_STOCKS, ISTANBUL_STOCKS,
                DUBLIN_STOCKS, LISBON_STOCKS,
                # Baltics
                TALLINN_STOCKS, RIGA_STOCKS, VILNIUS_STOCKS,
                # Canada
                TORONTO_STOCKS,
                # Middle East
                TADAWUL_STOCKS, ADX_STOCKS, DFM_STOCKS, QSE_STOCKS, KUWAIT_STOCKS,
                TASE_STOCKS,
                # Africa
                JSE_STOCKS, EGX_STOCKS,
                # Latin America
                BMV_STOCKS, B3_STOCKS, BUENOS_AIRES_STOCKS, SANTIAGO_STOCKS,
                COLOMBIA_STOCKS,
                # Southeast Asia
                VIETNAM_STOCKS, PHILIPPINES_STOCKS,
            )

            # Tier 1: global mega-caps + top crypto — warmup within minutes
            t1_stocks = [
                # US mega-cap
                "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "AVGO",
                "AMD", "INTC", "JPM", "V", "MA", "JNJ", "XOM", "UNH", "WMT",
                # India top 10 NSE
                "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
                "HINDUNILVR.NS", "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BAJFINANCE.NS",
                # Japan top 5
                "7203.T", "6758.T", "8306.T", "9984.T", "8035.T",
                # UK top 5
                "HSBA.L", "BP.L", "SHEL.L", "AZN.L", "ULVR.L",
                # HK top 5
                "0700.HK", "9988.HK", "0005.HK", "3690.HK", "1398.HK",
                # China top 5
                "600519.SS", "601398.SS", "002594.SZ", "300750.SZ", "000858.SZ",
                # Korea top 3
                "005930.KS", "000660.KS", "035420.KS",
                # Australia top 3
                "BHP.AX", "CBA.AX", "CSL.AX",
                # Canada top 3
                "SHOP.TO", "RY.TO", "TD.TO",
                # Saudi top 3
                "2222.SR", "1120.SR", "2010.SR",
            ]
            t1_crypto = DEFAULT_CRYPTO[:40]   # top 40 coins by our tier ranking

            t1 = list(dict.fromkeys(t1_stocks + t1_crypto))  # dedup, preserve order

            # Tier 2: full NYSE/NASDAQ + mid-cap crypto + regional blue-chips
            t2_stocks = (
                NYSE_STOCKS + NASDAQ_STOCKS +
                NSE_INDIA_STOCKS[:50] + BSE_INDIA_STOCKS[:30] +
                TOKYO_STOCKS + HONGKONG_STOCKS +
                LONDON_STOCKS[:40] + EURONEXT_STOCKS[:40] +
                KRX_STOCKS + TWSE_STOCKS + SGX_STOCKS + ASX_STOCKS[:30] +
                TORONTO_STOCKS[:40] + TADAWUL_STOCKS[:20]
            )
            t2_crypto = DEFAULT_CRYPTO[40:120]  # coins 41-120
            t2 = [s for s in dict.fromkeys(t2_stocks + t2_crypto) if s not in t1]

            # Tier 3: all remaining — long tail of global exchange stocks + remaining crypto
            t3_stocks = (
                SHANGHAI_STOCKS + SHENZHEN_STOCKS +
                XETRA_STOCKS + SIX_STOCKS + MADRID_STOCKS + VIENNA_STOCKS +
                COPENHAGEN_STOCKS + HELSINKI_STOCKS + STOCKHOLM_STOCKS +
                OSLO_STOCKS + ICELAND_STOCKS + PRAGUE_STOCKS + WARSAW_STOCKS +
                BUDAPEST_STOCKS + BUCHAREST_STOCKS + ATHENS_STOCKS + ISTANBUL_STOCKS +
                DUBLIN_STOCKS + LISBON_STOCKS + TALLINN_STOCKS + RIGA_STOCKS +
                VILNIUS_STOCKS + NZX_STOCKS + IDX_STOCKS + SET_STOCKS + KLSE_STOCKS +
                ADX_STOCKS + DFM_STOCKS + QSE_STOCKS + KUWAIT_STOCKS + TASE_STOCKS +
                JSE_STOCKS + EGX_STOCKS + BMV_STOCKS + B3_STOCKS +
                BUENOS_AIRES_STOCKS + SANTIAGO_STOCKS + COLOMBIA_STOCKS +
                VIETNAM_STOCKS + PHILIPPINES_STOCKS +
                NSE_INDIA_STOCKS[50:] + BSE_INDIA_STOCKS[30:] +
                LONDON_STOCKS[40:] + EURONEXT_STOCKS[40:] +
                TORONTO_STOCKS[40:] + ASX_STOCKS[30:] + TADAWUL_STOCKS[20:]
            )
            t3_crypto = DEFAULT_CRYPTO[120:]  # long-tail coins
            t3 = [s for s in dict.fromkeys(t3_stocks + t3_crypto)
                  if s not in t1 and s not in t2]

            return {"t1": t1, "t2": t2, "t3": t3}

        except Exception as e:
            print(f"[PredictionLoop] Symbol registry build failed: {e}")
            return {
                "t1": ["AAPL", "MSFT", "TSLA", "NVDA", "BTC/USDT", "ETH/USDT",
                       "SOL/USDT", "XRP/USDT", "RELIANCE.NS", "7203.T"],
                "t2": [],
                "t3": [],
            }

    def _get_symbol_list(self) -> List[str]:
        """
        Return the symbols to predict for this cycle.
        Uses a rotating tier strategy so all global exchanges are covered
        while high-priority assets are refreshed every single cycle.
        """
        tiers = self._build_tiered_symbols()
        cycle = self.stats.get("cycles_completed", 0)

        symbols = list(tiers["t1"])         # t1 always included
        if cycle % 2 == 0:
            symbols += tiers["t2"]          # t2 on even cycles
        if cycle % 3 == 0:
            symbols += tiers["t3"]          # t3 on every 3rd cycle

        # Deduplicate while preserving priority order
        seen: set = set()
        result = []
        for s in symbols:
            if s not in seen:
                seen.add(s)
                result.append(s)
        return result

    def _process_batch(self, batch: List[str]):
        """Run prediction for a batch of symbols concurrently."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(_predict_symbol, sym): sym for sym in batch}
            for fut in as_completed(futures, timeout=60):
                sym = futures[fut]
                try:
                    result = fut.result(timeout=30)
                    with self._stats_lock:
                        self.stats["total_predictions"] += 1
                    if result:
                        with _store_lock:
                            _prediction_store[sym.upper()] = result
                        with self._stats_lock:
                            self.stats["successful_predictions"] += 1
                    else:
                        with self._stats_lock:
                            self.stats["failed_predictions"] += 1
                except Exception as e:
                    print(f"[PredictionLoop] Batch error for {sym}: {e}")
                    with self._stats_lock:
                        self.stats["failed_predictions"] += 1

    def _work_loop(self):
        """Main infinite loop — never exits while _running is True."""
        print("[PredictionLoop] Worker thread started")
        with self._stats_lock:
            self.stats["started_at"] = datetime.now().isoformat()

        while self._running:
            try:
                symbols = self._get_symbol_list()

                # Process in batches
                for i in range(0, len(symbols), self.batch_size):
                    if not self._running:
                        break
                    batch = symbols[i: i + self.batch_size]
                    self._process_batch(batch)
                    # Brief sleep between batches (rate-limit pressure relief)
                    time.sleep(self.batch_sleep)

                # Cycle complete
                with self._stats_lock:
                    self.stats["cycles_completed"] += 1
                    self.stats["last_cycle_at"] = datetime.now().isoformat()
                    self.stats["symbols_covered"] = len(_prediction_store)

                n = get_prediction_count()
                print(f"[PredictionLoop] Cycle {self.stats['cycles_completed']} done "
                      f"— {n} symbols cached. Restarting immediately.")

            except Exception as e:
                print(f"[PredictionLoop] Unexpected error in main loop: {e}")
                traceback.print_exc()
                # Don't die — restart after 10 seconds
                time.sleep(10)

        print("[PredictionLoop] Worker thread stopped")

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Start the continuous prediction loop in a daemon thread."""
        if self._thread and self._thread.is_alive():
            print("[PredictionLoop] Already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._work_loop, daemon=True, name="PredictionLoop")
        self._thread.start()
        print("[PredictionLoop] Started background prediction thread")

    def stop(self):
        """Signal the loop to stop (it will finish the current batch first)."""
        self._running = False
        print("[PredictionLoop] Stop signal sent")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def get_stats(self) -> Dict:
        with self._stats_lock:
            return {
                **self.stats,
                "is_running": self.is_running(),
                "symbols_in_store": get_prediction_count(),
            }

    def predict_now(self, symbol: str) -> Optional[Dict]:
        """
        Force an immediate prediction for a single symbol (synchronous).
        Useful when a user requests a symbol not yet in the store.
        """
        result = _predict_symbol(symbol.upper())
        if result:
            with _store_lock:
                _prediction_store[symbol.upper()] = result
        return result


# Singleton
prediction_loop = PredictionLoop(
    batch_size=5,
    inter_symbol_sleep=0.3,
    batch_sleep=1.5,
    max_workers=5,
)
