"""
NexusTrader - Self-Learning Feedback Loop
==========================================
Compares predictions against actual outcomes and continuously improves
ensemble model weights and scanner agent weights.

Pipeline:
  1. RECORD  — When a prediction is made, store it with per-model details
  2. EVALUATE — Every hour, check predictions whose horizon has passed;
               fetch actual prices and compute errors
  3. LEARN   — Update per-model accuracy metrics using EMA
  4. ADJUST  — Recompute ensemble weights: w_i ∝ score_i^2
               (quadratic scaling: accurate models gain disproportionately)
  5. PERSIST — Save learned weights to JSON so they survive restarts

Accuracy metrics per model:
  - directional_accuracy  : % of predictions with correct up/down direction
  - mae_pct               : Mean Absolute Error as % of price
  - ema_score             : EMA blend of dir_acc and (1 - mae_normalized)
  - n_evaluated           : number of outcomes evaluated

Weight formula:
  raw = ema_score ^ 2
  w_model = raw_model / sum(raw_all)
  Clamped to [MIN_WEIGHT, MAX_WEIGHT] to keep all models alive.
"""

import json
import math
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent.parent / "data" / "feedback.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

WEIGHTS_PATH = Path(__file__).parent.parent.parent / "data" / "learned_weights.json"

# Horizons to evaluate (days after prediction)
HORIZONS = [1, 3, 7]

# EMA decay factor — controls how fast old data is forgotten
# alpha=0.15 means ~6-7 most recent predictions dominate
EMA_ALPHA = 0.15

# Weight clamping — no model ever goes below MIN or above MAX
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.50

DEFAULT_MODEL_WEIGHTS = {
    "lstm":     0.20,
    "prophet":  0.17,
    "xgboost":  0.25,
    "arima":    0.12,
    "lightgbm": 0.26,
}

DEFAULT_AGENT_WEIGHTS = {
    "TechnicalAgent":   0.22,
    "MomentumAgent":    0.18,
    "VolumeAgent":      0.16,
    "BreakoutAgent":    0.13,
    "SentimentAgent":   0.09,
    "FundamentalAgent": 0.07,
    "MacroAgent":       0.05,
    "OptionsFlowAgent": 0.10,   # 8th agent — options market microstructure
}

_lock = threading.Lock()


# ── Database setup ─────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS prediction_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            predicted_at    TEXT NOT NULL,
            current_price   REAL NOT NULL,
            pred_1d         REAL,
            pred_3d         REAL,
            pred_7d         REAL,
            direction       TEXT,
            confidence      REAL,
            model_preds     TEXT,   -- JSON: {model: [price_1d..7d]}
            weights_used    TEXT,   -- JSON: {model: weight}
            status          TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS outcome_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id   INTEGER NOT NULL,
            symbol          TEXT NOT NULL,
            horizon         INTEGER NOT NULL,  -- days (1, 3, 7)
            model_name      TEXT NOT NULL,     -- 'ensemble' or individual model
            predicted_price REAL NOT NULL,
            actual_price    REAL,
            price_error_pct REAL,
            direction_pred  TEXT,              -- 'up'/'down'
            direction_actual TEXT,
            direction_correct INTEGER,         -- 0/1
            evaluated_at    TEXT,
            FOREIGN KEY (prediction_id) REFERENCES prediction_records(id)
        );

        CREATE TABLE IF NOT EXISTS model_performance (
            model_name          TEXT NOT NULL,
            symbol              TEXT DEFAULT '__global__',
            directional_acc     REAL DEFAULT 0.5,
            mae_pct             REAL DEFAULT 0.02,
            ema_score           REAL DEFAULT 0.5,
            n_evaluated         INTEGER DEFAULT 0,
            current_weight      REAL,
            updated_at          TEXT,
            PRIMARY KEY (model_name, symbol)
        );

        CREATE TABLE IF NOT EXISTS agent_performance (
            agent_name          TEXT PRIMARY KEY,
            signal_accuracy     REAL DEFAULT 0.5,
            profit_factor       REAL DEFAULT 1.0,
            ema_score           REAL DEFAULT 0.5,
            n_evaluated         INTEGER DEFAULT 0,
            current_weight      REAL,
            updated_at          TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_pred_symbol ON prediction_records(symbol);
        CREATE INDEX IF NOT EXISTS idx_pred_status ON prediction_records(status);
        CREATE INDEX IF NOT EXISTS idx_outcome_pred ON outcome_records(prediction_id);
        """)


# ── Weight persistence ─────────────────────────────────────────────────────────

def _load_weights_file() -> Dict:
    if WEIGHTS_PATH.exists():
        try:
            with open(WEIGHTS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"model_weights": DEFAULT_MODEL_WEIGHTS.copy(),
            "agent_weights": DEFAULT_AGENT_WEIGHTS.copy()}


def _save_weights_file(model_weights: Dict, agent_weights: Dict):
    try:
        with open(WEIGHTS_PATH, "w") as f:
            json.dump({"model_weights": model_weights,
                       "agent_weights": agent_weights}, f, indent=2)
    except Exception as e:
        print(f"[FeedbackLoop] Failed to save weights: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_actual_price(symbol: str, target_date: datetime) -> Optional[float]:
    """Fetch the closing price on or after target_date from yfinance."""
    try:
        import yfinance as yf

        # Normalise symbol
        if "/" in symbol:
            yfSym = symbol.replace("/USDT", "-USD").replace("/", "-")
        else:
            yfSym = symbol

        # Fetch a window around the target date
        start = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
        end   = (target_date + timedelta(days=4)).strftime("%Y-%m-%d")

        hist = yf.Ticker(yfSym).history(start=start, end=end)
        if hist.empty:
            return None

        return float(hist["Close"].iloc[0])
    except Exception:
        return None


def _clamp_weights(raw: Dict[str, float]) -> Dict[str, float]:
    """Normalise and clamp weights to [MIN_WEIGHT, MAX_WEIGHT]."""
    total = sum(raw.values()) or 1.0
    clamped = {k: max(MIN_WEIGHT, min(MAX_WEIGHT, v / total)) for k, v in raw.items()}
    # Re-normalise after clamping
    t2 = sum(clamped.values())
    return {k: v / t2 for k, v in clamped.items()}


def _ema_update(current: float, new_sample: float, alpha: float = EMA_ALPHA) -> float:
    return alpha * new_sample + (1 - alpha) * current


# ── FeedbackLoop class ────────────────────────────────────────────────────────

class FeedbackLoop:
    """
    Self-learning engine. All public methods are thread-safe.
    A background evaluator thread wakes every hour to process pending outcomes.
    """

    def __init__(self):
        _init_db()
        weights = _load_weights_file()
        self._model_weights: Dict[str, float] = weights.get("model_weights", DEFAULT_MODEL_WEIGHTS.copy())
        self._agent_weights: Dict[str, float] = weights.get("agent_weights", DEFAULT_AGENT_WEIGHTS.copy())

        self._eval_thread: Optional[threading.Thread] = None
        self._running = False

        # Runtime stats for API
        self.stats = {
            "predictions_recorded": 0,
            "outcomes_evaluated":   0,
            "weight_updates":       0,
            "started_at":           None,
        }

    # ── Public: weights ───────────────────────────────────────────────────────

    def get_model_weights(self) -> Dict[str, float]:
        with _lock:
            return dict(self._model_weights)

    def get_agent_weights(self) -> Dict[str, float]:
        with _lock:
            return dict(self._agent_weights)

    # ── Public: record a prediction ───────────────────────────────────────────

    def record_prediction(
        self,
        symbol: str,
        current_price: float,
        predictions: List[float],     # 7-day price array
        direction: str,
        confidence: float,
        model_preds: Dict[str, List[float]],   # per-model 7d arrays
        weights_used: Dict[str, float],
    ):
        """
        Persist a new prediction to the database.
        Called by the prediction loop after every successful ensemble run.
        """
        try:
            pred_1d = predictions[0] if len(predictions) > 0 else None
            pred_3d = predictions[2] if len(predictions) > 2 else None
            pred_7d = predictions[6] if len(predictions) > 6 else predictions[-1] if predictions else None

            # Serialise per-model predictions (first 7 values each)
            model_json = json.dumps({
                m: [float(p) for p in v[:7]] for m, v in model_preds.items()
            })
            weights_json = json.dumps({k: float(v) for k, v in weights_used.items()})

            with _get_conn() as conn:
                conn.execute(
                    """INSERT INTO prediction_records
                       (symbol, predicted_at, current_price,
                        pred_1d, pred_3d, pred_7d, direction,
                        confidence, model_preds, weights_used, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
                    (symbol.upper(), datetime.now().isoformat(),
                     float(current_price),
                     float(pred_1d) if pred_1d else None,
                     float(pred_3d) if pred_3d else None,
                     float(pred_7d) if pred_7d else None,
                     direction, float(confidence),
                     model_json, weights_json)
                )

            with threading.Lock():
                self.stats["predictions_recorded"] += 1

        except Exception as e:
            print(f"[FeedbackLoop] record_prediction error: {e}")

    # ── Evaluation ────────────────────────────────────────────────────────────

    def _evaluate_pending(self):
        """
        Check all pending predictions whose horizon has passed.
        Fetch actual prices, compute errors, store outcomes.
        """
        evaluated_count = 0
        try:
            now = datetime.now()
            with _get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM prediction_records WHERE status='pending'"
                ).fetchall()

            for row in rows:
                pred_at = datetime.fromisoformat(row["predicted_at"])
                model_preds = json.loads(row["model_preds"] or "{}")
                weights_used = json.loads(row["weights_used"] or "{}")
                current_price = float(row["current_price"])
                direction_pred = row["direction"] or "neutral"

                horizons_done = []

                for h in HORIZONS:
                    target_dt = pred_at + timedelta(days=h)
                    if now < target_dt:
                        continue  # Not time yet

                    # Fetch actual price
                    actual = _fetch_actual_price(row["symbol"], target_dt)
                    if actual is None:
                        continue

                    direction_actual = "up" if actual > current_price else "down"
                    direction_pred_norm = ("up" if direction_pred in ("bullish", "up")
                                           else "down")
                    dir_correct = int(direction_pred_norm == direction_actual)

                    # Ensemble record
                    pred_price_key = {1: "pred_1d", 3: "pred_3d", 7: "pred_7d"}[h]
                    ensemble_pred = row[pred_price_key]
                    if ensemble_pred:
                        err_pct = abs(float(ensemble_pred) - actual) / (actual + 1e-9) * 100
                        with _get_conn() as conn:
                            conn.execute(
                                """INSERT OR IGNORE INTO outcome_records
                                   (prediction_id, symbol, horizon, model_name,
                                    predicted_price, actual_price, price_error_pct,
                                    direction_pred, direction_actual, direction_correct, evaluated_at)
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                (row["id"], row["symbol"], h, "ensemble",
                                 float(ensemble_pred), actual, err_pct,
                                 direction_pred_norm, direction_actual, dir_correct,
                                 now.isoformat())
                            )

                    # Per-model records
                    for model_name, preds in model_preds.items():
                        idx = h - 1
                        if idx < len(preds):
                            m_pred = preds[idx]
                            m_err = abs(m_pred - actual) / (actual + 1e-9) * 100
                            m_dir = "up" if m_pred > current_price else "down"
                            m_dir_ok = int(m_dir == direction_actual)
                            with _get_conn() as conn:
                                conn.execute(
                                    """INSERT OR IGNORE INTO outcome_records
                                       (prediction_id, symbol, horizon, model_name,
                                        predicted_price, actual_price, price_error_pct,
                                        direction_pred, direction_actual, direction_correct, evaluated_at)
                                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                    (row["id"], row["symbol"], h, model_name,
                                     m_pred, actual, m_err,
                                     m_dir, direction_actual, m_dir_ok,
                                     now.isoformat())
                                )
                    horizons_done.append(h)
                    evaluated_count += 1

                # Mark completed when all 3 horizons done
                if len(horizons_done) >= 3:
                    with _get_conn() as conn:
                        conn.execute(
                            "UPDATE prediction_records SET status='evaluated' WHERE id=?",
                            (row["id"],)
                        )

        except Exception as e:
            print(f"[FeedbackLoop] _evaluate_pending error: {e}")

        return evaluated_count

    def _update_model_performance(self):
        """
        Recompute per-model accuracy from recent outcomes and update EMA scores.
        Only uses outcomes from the past 90 days for rolling relevance.
        """
        try:
            cutoff = (datetime.now() - timedelta(days=90)).isoformat()
            models = ["ensemble", "lstm", "prophet", "xgboost", "arima", "lightgbm"]

            new_weights: Dict[str, float] = {}

            with _get_conn() as conn:
                for model in models:
                    rows = conn.execute(
                        """SELECT price_error_pct, direction_correct
                           FROM outcome_records
                           WHERE model_name=? AND evaluated_at > ? AND horizon=7
                           ORDER BY evaluated_at DESC LIMIT 200""",
                        (model, cutoff)
                    ).fetchall()

                    if len(rows) < 3:
                        # Insufficient data — use defaults
                        continue

                    errs = [r["price_error_pct"] for r in rows if r["price_error_pct"] is not None]
                    dirs = [r["direction_correct"] for r in rows if r["direction_correct"] is not None]

                    if not errs or not dirs:
                        continue

                    mae = float(np.mean(errs))
                    dir_acc = float(np.mean(dirs))
                    n = len(errs)

                    # Normalise MAE: 0%→perfect(1.0), 5%→bad(0.0), capped
                    mae_score = max(0.0, 1.0 - mae / 5.0)
                    # Combined score: 60% directional accuracy + 40% price accuracy
                    combined = dir_acc * 0.60 + mae_score * 0.40

                    # EMA update of ema_score from DB
                    existing = conn.execute(
                        "SELECT ema_score, n_evaluated FROM model_performance WHERE model_name=? AND symbol='__global__'",
                        (model,)
                    ).fetchone()

                    if existing:
                        old_ema = existing["ema_score"]
                        old_n = existing["n_evaluated"]
                        new_ema = _ema_update(old_ema, combined)
                    else:
                        new_ema = combined
                        old_n = 0

                    conn.execute(
                        """INSERT OR REPLACE INTO model_performance
                           (model_name, symbol, directional_acc, mae_pct, ema_score, n_evaluated,
                            current_weight, updated_at)
                           VALUES (?, '__global__', ?, ?, ?, ?, ?, ?)""",
                        (model, dir_acc, mae, new_ema, old_n + n,
                         self._model_weights.get(model, 0.2),
                         datetime.now().isoformat())
                    )

                    if model != "ensemble":
                        new_weights[model] = new_ema

            # Recompute weights if we have enough data (≥3 models scored)
            if len(new_weights) >= 3:
                # Fill missing models with average score
                avg_score = float(np.mean(list(new_weights.values())))
                for m in DEFAULT_MODEL_WEIGHTS:
                    if m not in new_weights:
                        new_weights[m] = avg_score

                # Quadratic scaling: accurate models gain more influence
                raw = {m: s ** 2 for m, s in new_weights.items()}
                learned = _clamp_weights(raw)

                with _lock:
                    self._model_weights = learned

                print(f"[FeedbackLoop] Updated model weights: "
                      + ", ".join(f"{k}={v:.3f}" for k, v in sorted(learned.items())))
                return learned

        except Exception as e:
            print(f"[FeedbackLoop] _update_model_performance error: {e}")
        return {}

    def _update_agent_weights(self):
        """
        Update scanner agent weights based on signal accuracy.
        Agent accuracy is tracked in agent_performance table.
        (Agent outcomes are registered via record_agent_outcome() from master_agent.)
        """
        try:
            with _get_conn() as conn:
                rows = conn.execute(
                    "SELECT agent_name, ema_score FROM agent_performance WHERE n_evaluated >= 5"
                ).fetchall()

            if len(rows) < 3:
                return  # Not enough data yet

            scores = {r["agent_name"]: r["ema_score"] for r in rows}
            # Fill missing
            avg = float(np.mean(list(scores.values())))
            for a in DEFAULT_AGENT_WEIGHTS:
                if a not in scores:
                    scores[a] = avg

            raw = {a: s ** 2 for a, s in scores.items()}
            learned = _clamp_weights(raw)

            with _lock:
                self._agent_weights = learned

            print(f"[FeedbackLoop] Updated agent weights")

        except Exception as e:
            print(f"[FeedbackLoop] _update_agent_weights error: {e}")

    def record_agent_outcome(
        self,
        agent_name: str,
        signal: str,         # 'BUY', 'SELL', 'HOLD', 'WATCH'
        score: float,
        actual_change_pct: float,  # actual % price change over next 7d
    ):
        """
        Record whether a scanner agent's signal was correct.
        A BUY/WATCH signal is correct if price rose; SELL if price fell.
        """
        try:
            signal_dir = 1 if signal in ("BUY", "WATCH") else (-1 if signal == "SELL" else 0)
            actual_dir = 1 if actual_change_pct > 0 else -1
            correct = int(signal_dir == actual_dir) if signal_dir != 0 else 0.5

            with _get_conn() as conn:
                existing = conn.execute(
                    "SELECT ema_score, n_evaluated FROM agent_performance WHERE agent_name=?",
                    (agent_name,)
                ).fetchone()

                if existing:
                    new_ema = _ema_update(existing["ema_score"], correct)
                    new_n = existing["n_evaluated"] + 1
                else:
                    new_ema = correct
                    new_n = 1

                conn.execute(
                    """INSERT OR REPLACE INTO agent_performance
                       (agent_name, signal_accuracy, ema_score, n_evaluated, current_weight, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (agent_name, correct, new_ema, new_n,
                     self._agent_weights.get(agent_name, 0.14),
                     datetime.now().isoformat())
                )

        except Exception as e:
            print(f"[FeedbackLoop] record_agent_outcome error: {e}")

    # ── Metrics API ───────────────────────────────────────────────────────────

    def get_model_metrics(self) -> List[Dict]:
        """Return current accuracy metrics for all models."""
        try:
            with _get_conn() as conn:
                rows = conn.execute(
                    """SELECT model_name, directional_acc, mae_pct, ema_score,
                              n_evaluated, current_weight, updated_at
                       FROM model_performance WHERE symbol='__global__'
                       ORDER BY ema_score DESC"""
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_agent_metrics(self) -> List[Dict]:
        """Return current accuracy metrics for all scanner agents."""
        try:
            with _get_conn() as conn:
                rows = conn.execute(
                    """SELECT agent_name, signal_accuracy, ema_score,
                              n_evaluated, current_weight, updated_at
                       FROM agent_performance ORDER BY ema_score DESC"""
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_recent_outcomes(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Return recent evaluated predictions with actual vs predicted."""
        try:
            with _get_conn() as conn:
                if symbol:
                    rows = conn.execute(
                        """SELECT o.*, p.predicted_at, p.confidence, p.direction
                           FROM outcome_records o
                           JOIN prediction_records p ON p.id = o.prediction_id
                           WHERE o.symbol=? AND o.model_name='ensemble'
                           ORDER BY o.evaluated_at DESC LIMIT ?""",
                        (symbol.upper(), limit)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT o.*, p.predicted_at, p.confidence, p.direction
                           FROM outcome_records o
                           JOIN prediction_records p ON p.id = o.prediction_id
                           WHERE o.model_name='ensemble'
                           ORDER BY o.evaluated_at DESC LIMIT ?""",
                        (limit,)
                    ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_accuracy_summary(self) -> Dict:
        """Overall system accuracy snapshot."""
        try:
            with _get_conn() as conn:
                total_preds = conn.execute(
                    "SELECT COUNT(*) as n FROM prediction_records"
                ).fetchone()["n"]
                total_outcomes = conn.execute(
                    "SELECT COUNT(*) as n FROM outcome_records WHERE model_name='ensemble'"
                ).fetchone()["n"]
                overall_dir = conn.execute(
                    """SELECT AVG(direction_correct) as acc FROM outcome_records
                       WHERE model_name='ensemble' AND evaluated_at > ?""",
                    ((datetime.now() - timedelta(days=30)).isoformat(),)
                ).fetchone()["acc"]
                overall_mae = conn.execute(
                    """SELECT AVG(price_error_pct) as mae FROM outcome_records
                       WHERE model_name='ensemble' AND evaluated_at > ?""",
                    ((datetime.now() - timedelta(days=30)).isoformat(),)
                ).fetchone()["mae"]

            return {
                "total_predictions_recorded": total_preds,
                "total_outcomes_evaluated":   total_outcomes,
                "last_30d_directional_accuracy": round(float(overall_dir or 0) * 100, 1),
                "last_30d_mae_pct":  round(float(overall_mae or 0), 2),
                "current_model_weights": self.get_model_weights(),
                "current_agent_weights": self.get_agent_weights(),
                "model_metrics": self.get_model_metrics(),
                "agent_metrics": self.get_agent_metrics(),
                "runner_stats": self.stats,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Background evaluator ─────────────────────────────────────────────────

    def _evaluator_loop(self):
        print("[FeedbackLoop] Evaluator thread started")
        self.stats["started_at"] = datetime.now().isoformat()

        while self._running:
            try:
                n_eval = self._evaluate_pending()
                if n_eval > 0:
                    self.stats["outcomes_evaluated"] += n_eval
                    print(f"[FeedbackLoop] Evaluated {n_eval} outcomes")

                    # Update performance metrics + weights
                    new_w = self._update_model_performance()
                    self._update_agent_weights()

                    if new_w:
                        self.stats["weight_updates"] += 1
                        # Persist to disk
                        _save_weights_file(self._model_weights, self._agent_weights)

            except Exception as e:
                print(f"[FeedbackLoop] Evaluator loop error: {e}")

            # Sleep 1 hour between evaluation passes
            for _ in range(3600):
                if not self._running:
                    break
                time.sleep(1)

        print("[FeedbackLoop] Evaluator thread stopped")

    def start(self):
        if self._eval_thread and self._eval_thread.is_alive():
            return
        self._running = True
        self._eval_thread = threading.Thread(
            target=self._evaluator_loop, daemon=True, name="FeedbackEvaluator"
        )
        self._eval_thread.start()
        print("[FeedbackLoop] Started — model weights will improve with every evaluated trade")

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return bool(self._eval_thread and self._eval_thread.is_alive())

    def force_evaluate_now(self) -> Dict:
        """Trigger an immediate evaluation cycle (for testing/API)."""
        n = self._evaluate_pending()
        w = self._update_model_performance()
        self._update_agent_weights()
        if w:
            _save_weights_file(self._model_weights, self._agent_weights)
        return {
            "outcomes_evaluated": n,
            "updated_weights": w,
            "current_model_weights": self.get_model_weights(),
        }


# Singleton
feedback_loop = FeedbackLoop()
