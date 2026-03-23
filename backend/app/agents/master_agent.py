"""
NexusTrader - Master Orchestrator Agent
Coordinates all sub-agents in parallel, aggregates signals, and ranks
trade opportunities by composite score.

Flow:
  1. For each symbol, run all sub-agents concurrently (ThreadPoolExecutor)
  2. Weight each agent's score by its stated confidence
  3. Compute composite score, grade, and trade opportunity struct
  4. Rank all symbols by composite score (best opportunities first)
  5. Cache results for 5 minutes (configurable)
"""

import time
import threading
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Protocol
from concurrent.futures import Future, ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime

from .scanner_agents import ALL_AGENTS


class _ScannerAgent(Protocol):
    name: str
    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict: ...


# ─────────────────────────────────────────────────────────────────────────────
# Agent weights (how much each agent's score influences the composite)
# ─────────────────────────────────────────────────────────────────────────────
AGENT_WEIGHTS = {
    "TechnicalAgent":    0.22,
    "MomentumAgent":     0.18,
    "VolumeAgent":       0.16,
    "BreakoutAgent":     0.13,
    "SentimentAgent":    0.09,
    "FundamentalAgent":  0.07,
    "MacroAgent":        0.05,
    "OptionsFlowAgent":  0.10,   # 8th agent: options market microstructure
}


def _grade(score: float) -> str:
    if score >= 60:
        return "A+ — Strong Buy"
    if score >= 40:
        return "A  — Buy"
    if score >= 20:
        return "B+ — Mild Buy"
    if score >= 10:
        return "B  — Watch Long"
    if score >= -10:
        return "C  — Neutral"
    if score >= -25:
        return "D  — Watch Short"
    if score >= -45:
        return "D- — Mild Sell"
    return "F  — Strong Sell"


def _trade_opportunity(symbol: str, score: float, df: pd.DataFrame, agent_results: List[Dict]) -> Dict:
    """Build a structured trade opportunity from composite score + price data."""
    last_price = 0.0
    try:
        close = df["close"] if "close" in df.columns else df["Close"]
        last_price = float(close.iloc[-1])
    except Exception:
        pass

    direction = "LONG" if score > 10 else ("SHORT" if score < -10 else "NEUTRAL")

    # Risk management
    if direction == "LONG":
        entry = last_price
        stop = round(last_price * 0.95, 4)
        target1 = round(last_price * 1.07, 4)
        target2 = round(last_price * 1.15, 4)
        risk_reward = round((target1 - entry) / (entry - stop + 1e-9), 2)
    elif direction == "SHORT":
        entry = last_price
        stop = round(last_price * 1.05, 4)
        target1 = round(last_price * 0.93, 4)
        target2 = round(last_price * 0.85, 4)
        risk_reward = round((entry - target1) / (stop - entry + 1e-9), 2)
    else:
        entry = last_price
        stop = None
        target1 = None
        target2 = None
        risk_reward = 0.0

    # Strongest reasoning points across all agents
    top_reasons = []
    for r in agent_results:
        for reason in r.get("reasoning", [])[:1]:  # top reason from each agent
            if reason and "unavailable" not in reason.lower() and "insufficient" not in reason.lower():
                top_reasons.append(f"[{r['agent'].replace('Agent','')}] {reason}")

    return {
        "symbol": symbol,
        "direction": direction,
        "composite_score": round(score, 1),
        "grade": _grade(score),
        "current_price": last_price,
        "entry": entry,
        "stop_loss": stop,
        "target_1": target1,
        "target_2": target2,
        "risk_reward": risk_reward,
        "key_reasons": top_reasons[:5],
        "agent_breakdown": [
            {"agent": r["agent"], "signal": r["signal"], "score": r["score"],
             "confidence": r["confidence"]}
            for r in agent_results
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# MasterAgent
# ─────────────────────────────────────────────────────────────────────────────

class MasterAgent:
    """
    Orchestrates all sub-agents, ranks symbols, and surfaces best opportunities.
    Thread-safe: all public methods can be called from multiple threads/coroutines.
    """

    def __init__(self, max_workers: int = 8, agent_timeout: float = 15.0):
        self.max_workers = max_workers
        self.agent_timeout = agent_timeout

        # Cache: symbol → (timestamp, result)
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5 minutes

        # Latest full scan results
        self._last_scan: Dict = {}
        self._last_scan_ts: float = 0.0
        self._scan_lock = threading.Lock()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _analyze_symbol(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Run all agents on one symbol in parallel."""
        agent_results: List[Dict] = []

        with ThreadPoolExecutor(max_workers=len(ALL_AGENTS)) as pool:
            futures: Dict[Future[Dict], _ScannerAgent] = {
                pool.submit(agent.analyze, symbol, df): agent  # type: ignore[arg-type]
                for agent in ALL_AGENTS
            }
            for fut in as_completed(futures, timeout=self.agent_timeout):
                try:
                    result = fut.result(timeout=self.agent_timeout)
                    agent_results.append(result)
                except Exception as e:
                    _agent: _ScannerAgent = futures[fut]
                    agent_results.append({
                        "agent": _agent.name,
                        "signal": "HOLD",
                        "score": 0.0,
                        "confidence": 30.0,
                        "reasoning": [f"Error: {str(e)[:60]}"],
                    })

        # Load learned agent weights (updated by feedback loop)
        try:
            from .feedback_loop import feedback_loop
            live_weights = feedback_loop.get_agent_weights()
        except Exception:
            live_weights = {}

        # Weighted composite score
        total_weight = 0.0
        weighted_score = 0.0
        for r in agent_results:
            name = r["agent"]
            # Prefer live learned weights, fall back to static AGENT_WEIGHTS
            base_weight = live_weights.get(name, AGENT_WEIGHTS.get(name, 0.10))
            # Scale weight by confidence (higher confidence → more influence)
            conf_mult = r.get("confidence", 50.0) / 100.0
            effective_weight = base_weight * (0.5 + 0.5 * conf_mult)
            weighted_score += r["score"] * effective_weight
            total_weight += effective_weight

        composite = weighted_score / total_weight if total_weight > 0 else 0.0
        composite = float(np.clip(composite, -100, 100))

        # Overall confidence = weighted average of agent confidences
        confidences = [r.get("confidence", 50.0) for r in agent_results]
        avg_conf = float(np.mean(confidences)) if confidences else 50.0
        # Boost if agents agree (low std = high agreement)
        score_std = float(np.std([r["score"] for r in agent_results]))
        agreement_bonus = max(0, 10 - score_std * 0.15)
        overall_conf = min(96.0, avg_conf + agreement_bonus)

        return {
            "symbol": symbol,
            "composite_score": round(composite, 1),
            "overall_confidence": round(overall_conf, 1),
            "grade": _grade(composite),
            "agent_results": agent_results,
            "timestamp": datetime.now().isoformat(),
        }

    def _fetch_df(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data with graceful error handling."""
        try:
            from ..data_manager import data_manager
            if "/" in symbol or any(c in symbol for c in ["BTC", "ETH", "BNB", "XRP", "USDT"]):
                # Crypto
                clean = symbol if "/" in symbol else f"{symbol}/USDT"
                df = data_manager.fetch_crypto_data(clean, timeframe="1d", limit=365)
            else:
                df = data_manager.fetch_stock_data(symbol, period="1y", interval="1d")

            if df is not None and not df.empty:
                df.columns = [c.lower() for c in df.columns]
            return df
        except Exception:
            return None

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze_symbol(self, symbol: str, df: Optional[pd.DataFrame] = None) -> Dict:
        """
        Full multi-agent analysis for a single symbol.
        Returns composite score, grade, trade setup, and per-agent breakdown.
        """
        key = symbol.upper()

        # Cache hit
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data

        if df is None:
            df = self._fetch_df(key)

        if df is None or df.empty:
            return {
                "symbol": key,
                "composite_score": 0.0,
                "overall_confidence": 30.0,
                "grade": "C  — Neutral",
                "error": "Could not fetch price data",
                "agent_results": [],
                "timestamp": datetime.now().isoformat(),
            }

        analysis = self._analyze_symbol(key, df)
        opportunity = _trade_opportunity(key, analysis["composite_score"], df,
                                         analysis["agent_results"])
        analysis["trade_opportunity"] = opportunity

        self._cache[key] = (time.time(), analysis)
        return analysis

    def scan_symbols(self, symbols: List[str], max_parallel: int = 6) -> List[Dict]:
        """
        Scan a list of symbols in parallel.
        Returns sorted list (best composite score first).
        """
        results = []

        def _job(sym: str) -> Dict:
            try:
                return self.analyze_symbol(sym)
            except Exception as e:
                return {"symbol": sym, "composite_score": 0.0,
                        "error": str(e), "agent_results": []}

        with ThreadPoolExecutor(max_workers=max_parallel) as pool:
            futures = {pool.submit(_job, sym): sym for sym in symbols}
            for fut in as_completed(futures, timeout=120):
                try:
                    results.append(fut.result(timeout=30))
                except Exception:
                    pass

        # Sort by composite score descending
        results.sort(key=lambda x: x.get("composite_score", 0.0), reverse=True)
        return results

    def get_best_opportunities(
        self,
        symbols: List[str],
        min_score: float = 25.0,
        min_confidence: float = 60.0,
        max_results: int = 10,
    ) -> List[Dict]:
        """
        Scan symbols and return only strong buy/sell opportunities.
        Filters by minimum composite score AND minimum confidence.
        """
        all_results = self.scan_symbols(symbols)

        opportunities = []
        for r in all_results:
            score = abs(r.get("composite_score", 0.0))  # absolute — catches SELL too
            conf = r.get("overall_confidence", 0.0)
            if score >= min_score and conf >= min_confidence:
                opp = r.get("trade_opportunity", {})
                opp["overall_confidence"] = conf
                opportunities.append(opp)

        return opportunities[:max_results]

    def full_market_scan(self, force: bool = False) -> Dict:
        """
        Run a complete scan of all default stocks + crypto.
        Returns ranked opportunities + market summary.
        Cached for 10 minutes unless force=True.
        """
        with self._scan_lock:
            if not force and time.time() - self._last_scan_ts < 600:
                return self._last_scan

        try:
            from ..config import DEFAULT_STOCKS, DEFAULT_CRYPTO
            symbols = (DEFAULT_CRYPTO[:15] + DEFAULT_STOCKS[:20])
        except ImportError:
            symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL",
                       "BTC/USDT", "ETH/USDT", "BNB/USDT"]

        all_results = self.scan_symbols(symbols, max_parallel=8)

        buy_ops = [r for r in all_results if r.get("composite_score", 0) >= 30]
        sell_ops = [r for r in all_results if r.get("composite_score", 0) <= -30]
        watch_ops = [r for r in all_results if 15 <= abs(r.get("composite_score", 0)) < 30]

        avg_score = float(np.mean([r.get("composite_score", 0) for r in all_results])) if all_results else 0.0
        market_bias = "BULLISH" if avg_score > 10 else ("BEARISH" if avg_score < -10 else "NEUTRAL")

        # Best trade setups (absolute score ≥ 30, sorted)
        top_trades = sorted(all_results, key=lambda x: abs(x.get("composite_score", 0)), reverse=True)[:5]

        scan_result = {
            "scan_timestamp": datetime.now().isoformat(),
            "symbols_scanned": len(all_results),
            "market_bias": market_bias,
            "average_score": round(avg_score, 1),
            "buy_signals": len(buy_ops),
            "sell_signals": len(sell_ops),
            "watch_signals": len(watch_ops),
            "top_opportunities": [r.get("trade_opportunity", {}) for r in top_trades
                                   if r.get("trade_opportunity")],
            "all_results": all_results,
        }

        with self._scan_lock:
            self._last_scan = scan_result
            self._last_scan_ts = time.time()

        return scan_result

    def get_last_scan(self) -> Dict:
        """Return the most recent scan results without re-scanning."""
        return self._last_scan or {
            "error": "No scan has run yet",
            "scan_timestamp": None,
            "top_opportunities": [],
            "all_results": [],
        }


# Singleton
master_agent = MasterAgent()
