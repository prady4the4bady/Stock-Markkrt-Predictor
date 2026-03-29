"""
NexusTrader — Self-Evolving Evolution Engine
==============================================
Learns from every prediction outcome to continuously improve all
weight layers in the prediction pipeline. This is the meta-learning
system that makes NexusTrader get smarter over time.

Evolution Targets (what gets learned):
  1. Oracle signal weights   — 24 signal layers, which ones predict best?
  2. Council model weights   — 12 NIM models, which ones are most accurate?
  3. Pipeline blend ratios   — tech/oracle/council/strategy mix
  4. Per-symbol preferences  — some signals work better for crypto vs stocks
  5. Regime-specific weights — different signal combos for trending vs ranging

Learning Algorithm:
  - Every prediction records its component scores (oracle signals, council
    votes, strategy outputs) alongside the final prediction.
  - When outcomes are evaluated (1d/3d/7d), the engine computes which
    components predicted correctly and which didn't.
  - Uses multiplicative weight update (MWU / Hedge algorithm):
      w_i(t+1) = w_i(t) * exp(η * reward_i)
    where reward_i = +1 if component predicted correct direction, -1 otherwise.
  - Weights are renormalized after each update to maintain probability simplex.
  - EMA smoothing prevents overreaction to single outcomes.
  - Per-symbol specialization allows AAPL oracle weights to differ from BTC.
  - Regime-specific weights adapt signal blending to market conditions.

Persistence:
  - All learned weights saved to JSON on disk (survives restarts).
  - Evolution cycle runs every 30 minutes (faster than feedback_loop's 1h).
  - Force-evolution API available for immediate learning.

Thread-safe, singleton pattern.
"""

import json
import math
import threading
import time
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Configuration ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EVOLUTION_STATE_PATH = DATA_DIR / "evolution_state.json"
EVOLUTION_LOG_PATH = DATA_DIR / "evolution_log.jsonl"

# Learning rate for multiplicative weight update
LEARNING_RATE = 0.08

# EMA alpha for smoothing weight updates (prevents overreaction)
EMA_ALPHA = 0.12

# Min/max weight clamps (no component ever goes to zero or dominates entirely)
MIN_WEIGHT = 0.005
MAX_WEIGHT = 0.30

# How many recent outcomes to consider per evolution cycle
LOOKBACK_OUTCOMES = 100

# Evolution cycle interval (seconds)
EVOLUTION_INTERVAL = 1800  # 30 minutes

_lock = threading.Lock()

# ── Default weights (starting point before any learning) ─────────────────────

DEFAULT_ORACLE_WEIGHTS = {
    "macro": 0.035, "market_breadth": 0.035, "fundamentals": 0.044,
    "options": 0.035, "smart_money": 0.044, "earnings": 0.035,
    "sector": 0.035, "fear_greed": 0.035, "social": 0.035,
    "google_trends": 0.018, "seasonal": 0.009, "cross_asset": 0.018,
    "chart_patterns": 0.044, "news_sentiment": 0.035, "polymarket": 0.070,
    "bloomberg_rss": 0.026, "barebone_ta": 0.044, "kimi_meta": 0.070,
    "council": 0.105, "options_gex": 0.044, "regime": 0.061,
    "momentum_composite": 0.050, "volume_profile": 0.040, "correlation_beta": 0.040,
}

DEFAULT_COUNCIL_WEIGHTS = {
    "nvidia/llama-3.1-nemotron-ultra-253b-v1": 0.14,
    "moonshotai/kimi-k2.5": 0.13,
    "deepseek-ai/deepseek-r1": 0.12,
    "qwen/qwq-32b": 0.11,
    "nvidia/llama-3.3-nemotron-super-120b-v1": 0.10,
    "microsoft/phi-4-reasoning-plus": 0.09,
    "meta/llama-4-maverick-17b-128e-instruct": 0.09,
    "minimaxi/minimax-m2-5": 0.08,
    "thudm/glm-5-32b-instruct": 0.06,
    "baidu/ernie-4.5-21b-preview": 0.03,
    "google/gemma-3-27b-it": 0.03,
    "meta/llama-3.3-70b-instruct": 0.02,
}

DEFAULT_PIPELINE_BLEND = {
    "technical": 0.25,
    "oracle": 0.35,
    "council": 0.20,
    "strategy": 0.20,
}

DEFAULT_REGIME_MODIFIERS = {
    "strong_trend": {"technical": 0.85, "oracle": 1.1, "council": 1.0, "strategy": 1.2},
    "mean_revert":  {"technical": 1.2, "oracle": 0.9, "council": 1.0, "strategy": 1.1},
    "high_vol":     {"technical": 0.7, "oracle": 1.2, "council": 1.3, "strategy": 0.9},
    "consolidation":{"technical": 1.3, "oracle": 0.8, "council": 0.9, "strategy": 1.1},
    "breakout":     {"technical": 0.9, "oracle": 1.0, "council": 1.1, "strategy": 1.3},
    "normal":       {"technical": 1.0, "oracle": 1.0, "council": 1.0, "strategy": 1.0},
}


# ── Utility ──────────────────────────────────────────────────────────────────

def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalize weights to sum to 1.0 while respecting min/max clamps."""
    total = sum(weights.values()) or 1.0
    normed = {k: max(MIN_WEIGHT, min(MAX_WEIGHT, v / total))
              for k, v in weights.items()}
    t2 = sum(normed.values()) or 1.0
    return {k: round(v / t2, 6) for k, v in normed.items()}


def _multiplicative_update(weights: Dict[str, float],
                           rewards: Dict[str, float],
                           lr: float = LEARNING_RATE) -> Dict[str, float]:
    """
    Multiplicative Weight Update (Hedge algorithm).
    w_i(t+1) = w_i(t) * exp(η * reward_i)
    Reward ∈ [-1, +1]: positive for correct prediction, negative for wrong.
    """
    updated = {}
    for k, w in weights.items():
        r = rewards.get(k, 0.0)
        updated[k] = w * math.exp(lr * r)
    return _normalize_weights(updated)


def _ema_blend(old: Dict[str, float], new: Dict[str, float],
               alpha: float = EMA_ALPHA) -> Dict[str, float]:
    """EMA blend between old and new weight dicts."""
    result = {}
    all_keys = set(old.keys()) | set(new.keys())
    for k in all_keys:
        o = old.get(k, 0.0)
        n = new.get(k, o)
        result[k] = alpha * n + (1 - alpha) * o
    return _normalize_weights(result)


# ── Prediction Snapshot (what we record with each prediction) ────────────────

class PredictionSnapshot:
    """Captures all component outputs at prediction time for later learning."""

    def __init__(self, symbol: str, current_price: float, direction: str,
                 confidence: float, oracle_signals: Dict[str, float],
                 council_votes: Dict[str, float],
                 strategy_scores: Dict[str, float],
                 pipeline_components: Dict[str, float],
                 regime: str = "normal",
                 timestamp: Optional[str] = None):
        self.symbol = symbol
        self.current_price = current_price
        self.direction = direction
        self.confidence = confidence
        self.oracle_signals = oracle_signals      # {signal_name: score}
        self.council_votes = council_votes        # {model_name: score}
        self.strategy_scores = strategy_scores    # {strategy: score}
        self.pipeline_components = pipeline_components  # {tech/oracle/council/strategy: weighted_score}
        self.regime = regime
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "direction": self.direction,
            "confidence": self.confidence,
            "oracle_signals": self.oracle_signals,
            "council_votes": self.council_votes,
            "strategy_scores": self.strategy_scores,
            "pipeline_components": self.pipeline_components,
            "regime": self.regime,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "PredictionSnapshot":
        return cls(
            symbol=d["symbol"],
            current_price=d["current_price"],
            direction=d["direction"],
            confidence=d["confidence"],
            oracle_signals=d.get("oracle_signals", {}),
            council_votes=d.get("council_votes", {}),
            strategy_scores=d.get("strategy_scores", {}),
            pipeline_components=d.get("pipeline_components", {}),
            regime=d.get("regime", "normal"),
            timestamp=d.get("timestamp"),
        )


# ── Evolution Engine ─────────────────────────────────────────────────────────

class EvolutionEngine:
    """
    Self-evolving meta-learner. Tracks prediction component contributions,
    evaluates outcomes, and evolves all weight layers using multiplicative
    weight updates with EMA smoothing.
    """

    def __init__(self):
        self._oracle_weights: Dict[str, float] = DEFAULT_ORACLE_WEIGHTS.copy()
        self._council_weights: Dict[str, float] = DEFAULT_COUNCIL_WEIGHTS.copy()
        self._pipeline_blend: Dict[str, float] = DEFAULT_PIPELINE_BLEND.copy()
        self._regime_modifiers: Dict[str, Dict[str, float]] = {
            k: dict(v) for k, v in DEFAULT_REGIME_MODIFIERS.items()
        }
        self._symbol_overrides: Dict[str, Dict[str, Dict[str, float]]] = {}

        # Pending snapshots waiting for outcome evaluation
        self._pending_snapshots: List[Dict] = []

        # Evolution history
        self._generation: int = 0
        self._last_evolution: Optional[str] = None
        self._evolution_log: List[Dict] = []

        # Stats
        self.stats = {
            "snapshots_recorded": 0,
            "evolutions_run": 0,
            "total_outcomes_learned": 0,
            "best_oracle_signal": None,
            "worst_oracle_signal": None,
            "started_at": None,
        }

        # Background thread
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Load saved state
        self._load_state()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load_state(self):
        """Load evolved weights from disk."""
        if EVOLUTION_STATE_PATH.exists():
            try:
                with open(EVOLUTION_STATE_PATH, "r") as f:
                    state = json.load(f)
                self._oracle_weights = state.get("oracle_weights", self._oracle_weights)
                self._council_weights = state.get("council_weights", self._council_weights)
                self._pipeline_blend = state.get("pipeline_blend", self._pipeline_blend)
                self._regime_modifiers = state.get("regime_modifiers", self._regime_modifiers)
                self._symbol_overrides = state.get("symbol_overrides", {})
                self._generation = state.get("generation", 0)
                self._last_evolution = state.get("last_evolution")
                self._pending_snapshots = state.get("pending_snapshots", [])
                print(f"[Evolution] Loaded state: generation {self._generation}, "
                      f"{len(self._pending_snapshots)} pending snapshots")
            except Exception as e:
                print(f"[Evolution] Failed to load state: {e}")

    def _save_state(self):
        """Persist evolved weights to disk."""
        try:
            state = {
                "oracle_weights": self._oracle_weights,
                "council_weights": self._council_weights,
                "pipeline_blend": self._pipeline_blend,
                "regime_modifiers": self._regime_modifiers,
                "symbol_overrides": self._symbol_overrides,
                "generation": self._generation,
                "last_evolution": self._last_evolution,
                "pending_snapshots": self._pending_snapshots[-500:],  # cap storage
            }
            with open(EVOLUTION_STATE_PATH, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[Evolution] Failed to save state: {e}")

    def _log_evolution(self, entry: Dict):
        """Append to evolution log (JSONL)."""
        try:
            entry["timestamp"] = datetime.now().isoformat()
            entry["generation"] = self._generation
            with open(EVOLUTION_LOG_PATH, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    # ── Public: Record a prediction snapshot ─────────────────────────────────

    def record_snapshot(self, snapshot: PredictionSnapshot):
        """
        Called by the prediction pipeline after every prediction.
        Records component-level scores for later outcome evaluation.
        """
        with _lock:
            self._pending_snapshots.append(snapshot.to_dict())
            self.stats["snapshots_recorded"] += 1

            # Periodic auto-save (every 20 snapshots)
            if self.stats["snapshots_recorded"] % 20 == 0:
                self._save_state()

    # ── Public: Get evolved weights ──────────────────────────────────────────

    def get_oracle_weights(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """Get evolved oracle signal weights, optionally per-symbol."""
        with _lock:
            base = dict(self._oracle_weights)
            if symbol and symbol in self._symbol_overrides:
                overrides = self._symbol_overrides[symbol].get("oracle", {})
                for k, v in overrides.items():
                    if k in base:
                        base[k] = v
                base = _normalize_weights(base)
            return base

    def get_council_weights(self) -> Dict[str, float]:
        with _lock:
            return dict(self._council_weights)

    def get_pipeline_blend(self, regime: str = "normal") -> Dict[str, float]:
        """Get evolved pipeline blend ratios, adjusted for market regime."""
        with _lock:
            base = dict(self._pipeline_blend)
            modifiers = self._regime_modifiers.get(regime, {})
            if modifiers:
                adjusted = {k: v * modifiers.get(k, 1.0) for k, v in base.items()}
                return _normalize_weights(adjusted)
            return base

    # ── Core: Evolution cycle ────────────────────────────────────────────────

    def evolve(self) -> Dict:
        """
        Run one evolution cycle:
        1. Find snapshots with elapsed outcomes (1d+)
        2. Fetch actual prices to determine correctness
        3. Compute per-component rewards
        4. Update weights via MWU + EMA
        5. Persist and log
        """
        now = datetime.now()
        outcomes_learned = 0
        oracle_rewards_accum: Dict[str, List[float]] = {}
        council_rewards_accum: Dict[str, List[float]] = {}
        pipeline_rewards_accum: Dict[str, List[float]] = {}
        regime_rewards: Dict[str, Dict[str, List[float]]] = {}

        evaluated_indices = []

        with _lock:
            snapshots = list(self._pending_snapshots)

        for idx, snap_dict in enumerate(snapshots):
            try:
                snap = PredictionSnapshot.from_dict(snap_dict)
                pred_time = datetime.fromisoformat(snap.timestamp)

                # Need at least 1 day elapsed
                if (now - pred_time).total_seconds() < 86400:
                    continue

                # Fetch actual price
                actual = self._fetch_actual(snap.symbol, pred_time + timedelta(days=1))
                if actual is None:
                    continue

                # Determine if prediction was correct
                pred_up = snap.direction.lower() in ("up", "bullish", "buy")
                actual_up = actual > snap.current_price
                correct = (pred_up == actual_up)
                reward = 1.0 if correct else -1.0

                # Scale reward by confidence (high-confidence wrong = bigger penalty)
                conf_scale = snap.confidence / 100.0
                scaled_reward = reward * (0.5 + 0.5 * conf_scale)

                # ── Oracle signal rewards ────────────────────────────────
                for sig_name, sig_score in snap.oracle_signals.items():
                    if sig_name not in oracle_rewards_accum:
                        oracle_rewards_accum[sig_name] = []
                    # Signal aligned with outcome → positive reward
                    sig_aligned = (sig_score > 0 and actual_up) or (sig_score < 0 and not actual_up)
                    sig_reward = abs(sig_score) if sig_aligned else -abs(sig_score)
                    oracle_rewards_accum[sig_name].append(sig_reward)

                # ── Council model rewards ────────────────────────────────
                for model_name, vote_score in snap.council_votes.items():
                    if model_name not in council_rewards_accum:
                        council_rewards_accum[model_name] = []
                    vote_aligned = (vote_score > 0 and actual_up) or (vote_score < 0 and not actual_up)
                    vote_reward = abs(vote_score) if vote_aligned else -abs(vote_score)
                    council_rewards_accum[model_name].append(vote_reward)

                # ── Pipeline component rewards ───────────────────────────
                for comp, score in snap.pipeline_components.items():
                    if comp not in pipeline_rewards_accum:
                        pipeline_rewards_accum[comp] = []
                    comp_aligned = (score > 0 and actual_up) or (score < 0 and not actual_up)
                    comp_reward = 1.0 if comp_aligned else -1.0
                    pipeline_rewards_accum[comp].append(comp_reward)

                # ── Regime-specific tracking ─────────────────────────────
                regime = snap.regime
                if regime not in regime_rewards:
                    regime_rewards[regime] = {}
                for comp, score in snap.pipeline_components.items():
                    if comp not in regime_rewards[regime]:
                        regime_rewards[regime][comp] = []
                    comp_aligned = (score > 0 and actual_up) or (score < 0 and not actual_up)
                    regime_rewards[regime][comp].append(1.0 if comp_aligned else -1.0)

                evaluated_indices.append(idx)
                outcomes_learned += 1

            except Exception as e:
                print(f"[Evolution] Snapshot eval error: {e}")
                evaluated_indices.append(idx)  # Remove bad snapshots

        if outcomes_learned == 0:
            return {"evolved": False, "reason": "no_mature_outcomes",
                    "pending": len(snapshots)}

        # ── Apply weight updates ─────────────────────────────────────────────

        # 1. Oracle weights
        oracle_mean_rewards = {
            k: float(np.mean(v)) for k, v in oracle_rewards_accum.items() if v
        }
        if oracle_mean_rewards:
            new_oracle = _multiplicative_update(self._oracle_weights, oracle_mean_rewards)
            with _lock:
                self._oracle_weights = _ema_blend(self._oracle_weights, new_oracle)

        # 2. Council weights
        council_mean_rewards = {
            k: float(np.mean(v)) for k, v in council_rewards_accum.items() if v
        }
        if council_mean_rewards:
            new_council = _multiplicative_update(self._council_weights, council_mean_rewards)
            with _lock:
                self._council_weights = _ema_blend(self._council_weights, new_council)

        # 3. Pipeline blend
        pipeline_mean_rewards = {
            k: float(np.mean(v)) for k, v in pipeline_rewards_accum.items() if v
        }
        if pipeline_mean_rewards:
            new_blend = _multiplicative_update(self._pipeline_blend, pipeline_mean_rewards)
            with _lock:
                self._pipeline_blend = _ema_blend(self._pipeline_blend, new_blend)

        # 4. Regime modifiers
        for regime, comps in regime_rewards.items():
            mean_r = {k: float(np.mean(v)) for k, v in comps.items() if v}
            if mean_r and regime in self._regime_modifiers:
                current_mods = self._regime_modifiers[regime]
                for comp, reward in mean_r.items():
                    if comp in current_mods:
                        old_mod = current_mods[comp]
                        # Shift modifier toward what works
                        current_mods[comp] = old_mod * math.exp(LEARNING_RATE * 0.5 * reward)
                        current_mods[comp] = max(0.3, min(2.0, current_mods[comp]))

        # ── Remove evaluated snapshots ───────────────────────────────────────
        with _lock:
            remaining = [s for i, s in enumerate(self._pending_snapshots)
                         if i not in set(evaluated_indices)]
            self._pending_snapshots = remaining

        # ── Update stats ─────────────────────────────────────────────────────
        self._generation += 1
        self._last_evolution = now.isoformat()
        self.stats["evolutions_run"] += 1
        self.stats["total_outcomes_learned"] += outcomes_learned

        # Track best/worst oracle signals
        if oracle_mean_rewards:
            best = max(oracle_mean_rewards, key=oracle_mean_rewards.get)
            worst = min(oracle_mean_rewards, key=oracle_mean_rewards.get)
            self.stats["best_oracle_signal"] = best
            self.stats["worst_oracle_signal"] = worst

        # Persist
        self._save_state()

        result = {
            "evolved": True,
            "generation": self._generation,
            "outcomes_learned": outcomes_learned,
            "remaining_pending": len(self._pending_snapshots),
            "oracle_weight_changes": oracle_mean_rewards,
            "council_weight_changes": council_mean_rewards,
            "pipeline_blend": self._pipeline_blend,
        }

        self._log_evolution(result)
        print(f"[Evolution] Gen {self._generation}: learned from {outcomes_learned} outcomes, "
              f"{len(self._pending_snapshots)} pending")

        return result

    # ── Price fetcher ────────────────────────────────────────────────────────

    @staticmethod
    def _fetch_actual(symbol: str, target_dt: datetime) -> Optional[float]:
        """Fetch actual closing price on target date."""
        try:
            import yfinance as yf

            if "/" in symbol:
                yf_sym = symbol.replace("/USDT", "-USD").replace("/", "-")
            else:
                yf_sym = symbol

            start = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            end = (target_dt + timedelta(days=3)).strftime("%Y-%m-%d")
            hist = yf.Ticker(yf_sym).history(start=start, end=end)
            if hist.empty:
                return None
            return float(hist["Close"].iloc[0])
        except Exception:
            return None

    # ── Public: Status / Metrics ─────────────────────────────────────────────

    def get_status(self) -> Dict:
        """Full evolution engine status."""
        with _lock:
            return {
                "generation": self._generation,
                "last_evolution": self._last_evolution,
                "pending_snapshots": len(self._pending_snapshots),
                "oracle_weights": dict(self._oracle_weights),
                "council_weights": dict(self._council_weights),
                "pipeline_blend": dict(self._pipeline_blend),
                "regime_modifiers": {k: dict(v) for k, v in self._regime_modifiers.items()},
                "symbol_overrides_count": len(self._symbol_overrides),
                "stats": dict(self.stats),
            }

    def get_weight_drift(self) -> Dict:
        """Show how much weights have drifted from defaults."""
        oracle_drift = {}
        for k in DEFAULT_ORACLE_WEIGHTS:
            default = DEFAULT_ORACLE_WEIGHTS[k]
            current = self._oracle_weights.get(k, default)
            pct_change = ((current - default) / (default + 1e-9)) * 100
            if abs(pct_change) > 1.0:  # Only show meaningful drift
                oracle_drift[k] = round(pct_change, 1)

        pipeline_drift = {}
        for k in DEFAULT_PIPELINE_BLEND:
            default = DEFAULT_PIPELINE_BLEND[k]
            current = self._pipeline_blend.get(k, default)
            pct_change = ((current - default) / (default + 1e-9)) * 100
            if abs(pct_change) > 1.0:
                pipeline_drift[k] = round(pct_change, 1)

        return {
            "generation": self._generation,
            "oracle_drift_pct": oracle_drift,
            "pipeline_drift_pct": pipeline_drift,
            "total_outcomes_learned": self.stats["total_outcomes_learned"],
        }

    def reset_to_defaults(self) -> Dict:
        """Reset all evolved weights to defaults (emergency use)."""
        with _lock:
            self._oracle_weights = DEFAULT_ORACLE_WEIGHTS.copy()
            self._council_weights = DEFAULT_COUNCIL_WEIGHTS.copy()
            self._pipeline_blend = DEFAULT_PIPELINE_BLEND.copy()
            self._regime_modifiers = {
                k: dict(v) for k, v in DEFAULT_REGIME_MODIFIERS.items()
            }
            self._symbol_overrides = {}
            self._generation = 0
        self._save_state()
        return {"reset": True, "generation": 0}

    # ── Background evolution loop ────────────────────────────────────────────

    def _evolution_loop(self):
        print("[Evolution] Background evolution thread started")
        self.stats["started_at"] = datetime.now().isoformat()

        while self._running:
            try:
                # Only evolve if we have enough pending snapshots
                if len(self._pending_snapshots) >= 5:
                    result = self.evolve()
                    if result.get("evolved"):
                        print(f"[Evolution] Auto-evolved: gen {result['generation']}, "
                              f"learned {result['outcomes_learned']}")
            except Exception as e:
                print(f"[Evolution] Loop error: {e}")

            # Sleep for EVOLUTION_INTERVAL, checking for shutdown
            for _ in range(EVOLUTION_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)

        print("[Evolution] Background thread stopped")

    def start(self):
        """Start background evolution thread."""
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._evolution_loop, daemon=True, name="EvolutionEngine"
        )
        self._thread.start()
        print(f"[Evolution] Started — generation {self._generation}, "
              f"learning rate {LEARNING_RATE}")

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def force_evolve(self) -> Dict:
        """Trigger immediate evolution cycle (for API/testing)."""
        return self.evolve()


# ── Singleton ────────────────────────────────────────────────────────────────
evolution_engine = EvolutionEngine()
