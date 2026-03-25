"""
NexusTrader — Prediction Tracker & Self-Calibration Engine
===========================================================
Records every quick_predict() outcome, verifies it after the prediction
window expires by fetching the actual market price, then computes per-layer
accuracy statistics that are fed back to Market Oracle as calibration
multipliers.

Self-learning loop:
  1. quick_predict() calls prediction_tracker.record(...)
  2. Background daemon wakes every 30 min, verifies pending outcomes via yfinance
  3. get_layer_calibration() returns weight multipliers per oracle layer:
       accuracy 40% → 0.4×  (dampen: layer consistently wrong)
       accuracy 50% → 0.8×  (neutral)
       accuracy 65% → 1.2×  (amplify: layer reliably correct)
       accuracy 80% → 1.6×  (max amplification)
  4. quick_predict() applies multipliers BEFORE computing combined_signal
"""

import json
import threading
import time as _time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np
import yfinance as yf
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text

from ..database import Base, get_db_context


# ── Oracle layer weight table (mirrors market_oracle._WEIGHTS) ────────────────
_ORACLE_WEIGHTS: Dict[str, float] = {
    "macro":          0.13,
    "market_breadth": 0.11,
    "fundamentals":   0.11,
    "options":        0.09,
    "smart_money":    0.08,
    "earnings":       0.07,
    "sector":         0.07,
    "fear_greed":     0.06,
    "social":         0.06,
    "google_trends":  0.03,
    "seasonal":       0.02,
    "cross_asset":    0.02,
    "chart_patterns": 0.09,
    "news_sentiment": 0.06,
}


# ── SQLAlchemy model ──────────────────────────────────────────────────────────

class PredictionOutcome(Base):
    """One row per prediction emitted by quick_predict()."""
    __tablename__ = "prediction_outcomes"

    id                  = Column(Integer, primary_key=True, index=True)
    symbol              = Column(String(30), index=True, nullable=False)
    predicted_at        = Column(DateTime, default=datetime.utcnow, index=True)
    verify_at           = Column(DateTime, index=True)   # when to check actual price
    hours               = Column(Integer, default=24)

    # ── What was predicted ───────────────────────────────────────────────────
    price_at_prediction = Column(Float, nullable=False)
    recommendation      = Column(String(10))             # BUY / SELL / HOLD
    confidence          = Column(Float)
    combined_signal     = Column(Float)
    oracle_direction    = Column(Integer, default=0)
    tech_direction      = Column(Integer, default=0)
    oracle_signals      = Column(Text)                   # JSON of layer scores

    # ── Trade plan at prediction time ────────────────────────────────────────
    entry_price   = Column(Float)
    stop_loss     = Column(Float)
    target_price  = Column(Float)
    risk_reward   = Column(Float)

    # ── Outcome (filled by verifier thread) ──────────────────────────────────
    outcome_checked   = Column(Boolean, default=False)
    price_at_outcome  = Column(Float)
    direction_correct = Column(Boolean)
    target_hit        = Column(Boolean)
    stop_hit          = Column(Boolean)
    pct_change_actual = Column(Float)
    outcome_at        = Column(DateTime)


# ── Tracker ───────────────────────────────────────────────────────────────────

class PredictionTracker:
    """
    Records, verifies, and calibrates predictions.

    Calibration math
    ----------------
    We map each layer's rolling 30-day accuracy onto a multiplier:
      acc=0.40 → mult=0.40   (worse than chance → heavily dampen)
      acc=0.50 → mult=0.80   (random → slightly dampen)
      acc=0.60 → mult=1.20   (good → amplify)
      acc=0.70 → mult=1.60   (excellent → max amplify, capped)

    Formula: mult = 0.40 + (acc - 0.40) / 0.40 * 1.20   [clamped 0.40–1.60]
    """

    _MIN_MULT = 0.40
    _MAX_MULT = 1.60

    def __init__(self):
        self._lock         = threading.Lock()
        self._calib_cache: Dict[str, float] = {}
        self._calib_at:    Optional[datetime] = None
        self._calib_ttl    = timedelta(minutes=30)

        t = threading.Thread(target=self._verify_loop, daemon=True, name="pred-verifier")
        t.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def record(self, *, symbol: str, price: float, recommendation: str,
               confidence: float, combined_signal: float,
               oracle_direction: int, tech_direction: int,
               oracle_signals: Dict[str, float], hours: int,
               entry: float, stop: float, target: float,
               risk_reward: float) -> None:
        """Persist a prediction so its outcome can be verified later."""
        try:
            with get_db_context() as db:
                db.add(PredictionOutcome(
                    symbol              = symbol.upper(),
                    predicted_at        = datetime.utcnow(),
                    verify_at           = datetime.utcnow() + timedelta(hours=max(hours, 1)),
                    hours               = hours,
                    price_at_prediction = price,
                    recommendation      = recommendation,
                    confidence          = confidence,
                    combined_signal     = combined_signal,
                    oracle_direction    = oracle_direction,
                    tech_direction      = tech_direction,
                    oracle_signals      = json.dumps({k: round(float(v), 4)
                                                     for k, v in oracle_signals.items()}),
                    entry_price         = entry,
                    stop_loss           = stop,
                    target_price        = target,
                    risk_reward         = risk_reward,
                ))
        except Exception as e:
            print(f"[Tracker] record() failed: {e}")

    def get_recent_outcomes(self, symbol: Optional[str] = None,
                            limit: int = 20) -> List[Dict]:
        """Most recent verified predictions, newest first."""
        try:
            with get_db_context() as db:
                q = db.query(PredictionOutcome).filter(
                    PredictionOutcome.outcome_checked == True  # noqa: E712
                )
                if symbol:
                    q = q.filter(PredictionOutcome.symbol == symbol.upper())
                rows = q.order_by(PredictionOutcome.predicted_at.desc()).limit(limit).all()
                return [self._to_dict(r) for r in rows]
        except Exception as e:
            print(f"[Tracker] get_recent_outcomes() failed: {e}")
            return []

    def get_pending_count(self) -> int:
        """How many predictions are awaiting verification."""
        try:
            with get_db_context() as db:
                return db.query(PredictionOutcome).filter(
                    PredictionOutcome.outcome_checked == False  # noqa: E712
                ).count()
        except Exception:
            return 0

    def get_accuracy_stats(self, symbol: Optional[str] = None,
                           days: int = 30) -> Dict:
        """
        Overall accuracy over the last N days.
        Returns direction hit-rate, target hit-rate, avg R:R,
        and a calibration_factor (actual_acc / stated_conf) that
        quick_predict() can apply to final_confidence.
        """
        try:
            since = datetime.utcnow() - timedelta(days=days)
            with get_db_context() as db:
                q = db.query(PredictionOutcome).filter(
                    PredictionOutcome.outcome_checked == True,  # noqa: E712
                    PredictionOutcome.predicted_at   >= since,
                )
                if symbol:
                    q = q.filter(PredictionOutcome.symbol == symbol.upper())
                rows = q.all()

            if not rows:
                return {"total": 0, "calibration_factor": 1.0,
                        "message": "No verified predictions yet — calibration disabled."}

            total       = len(rows)
            correct_dir = sum(1 for r in rows if r.direction_correct)
            tgt_hits    = sum(1 for r in rows if r.target_hit)
            stop_hits   = sum(1 for r in rows if r.stop_hit)

            rr_vals  = [r.risk_reward     for r in rows if r.risk_reward     is not None]
            pct_vals = [r.pct_change_actual for r in rows if r.pct_change_actual is not None]
            conf_vals = [r.confidence      for r in rows if r.confidence     is not None]

            avg_rr       = float(np.mean(rr_vals))   if rr_vals   else 0.0
            avg_pct      = float(np.mean(pct_vals))  if pct_vals  else 0.0
            stated_conf  = float(np.mean(conf_vals)) if conf_vals else 75.0
            actual_acc   = correct_dir / total * 100.0

            # Calibration factor: scale confidence toward what's actually accurate
            # Clamped so we never overcorrect wildly
            calib = max(0.60, min(1.20, actual_acc / stated_conf if stated_conf > 0 else 1.0))

            return {
                "total":              total,
                "direction_accuracy": round(actual_acc, 1),
                "target_hit_rate":    round(tgt_hits  / total * 100, 1),
                "stop_hit_rate":      round(stop_hits / total * 100, 1),
                "avg_risk_reward":    round(avg_rr,   2),
                "avg_pct_change":     round(avg_pct,  2),
                "stated_confidence":  round(stated_conf, 1),
                "calibration_factor": round(calib, 3),
                "days_window":        days,
            }
        except Exception as e:
            print(f"[Tracker] get_accuracy_stats() failed: {e}")
            return {"total": 0, "calibration_factor": 1.0, "error": str(e)}

    def get_layer_accuracy(self, days: int = 30) -> Dict[str, Dict]:
        """
        Per oracle layer accuracy — did each layer's signal direction
        match the actual price move?
        """
        try:
            since = datetime.utcnow() - timedelta(days=days)
            with get_db_context() as db:
                rows = db.query(PredictionOutcome).filter(
                    PredictionOutcome.outcome_checked   == True,   # noqa
                    PredictionOutcome.predicted_at      >= since,
                    PredictionOutcome.oracle_signals    != None,   # noqa
                    PredictionOutcome.pct_change_actual != None,   # noqa
                ).all()

            if not rows:
                return {}

            layer_stats: Dict[str, Dict] = {}
            for r in rows:
                try:
                    signals = json.loads(r.oracle_signals or "{}")
                except Exception:
                    continue
                actual_dir = 1 if (r.pct_change_actual or 0) > 0 else -1
                for layer, score in signals.items():
                    layer_dir = 1 if score > 0.05 else -1 if score < -0.05 else 0
                    if layer_dir == 0:
                        continue
                    ls = layer_stats.setdefault(layer, {"correct": 0, "total": 0})
                    ls["total"]  += 1
                    ls["correct"] += 1 if layer_dir == actual_dir else 0

            result = {}
            for layer, s in layer_stats.items():
                if s["total"] >= 3:
                    acc = s["correct"] / s["total"] * 100
                    result[layer] = {
                        "accuracy": round(acc, 1),
                        "total":    s["total"],
                        "correct":  s["correct"],
                    }
            return result
        except Exception as e:
            print(f"[Tracker] get_layer_accuracy() failed: {e}")
            return {}

    def get_layer_calibration(self, days: int = 30) -> Dict[str, float]:
        """
        Returns a weight multiplier for each oracle layer based on recent
        directional accuracy.  Cached for 30 minutes.
        """
        with self._lock:
            if (self._calib_at
                    and datetime.utcnow() - self._calib_at < self._calib_ttl
                    and self._calib_cache):
                return dict(self._calib_cache)

        layer_acc = self.get_layer_accuracy(days)
        if not layer_acc:
            return {}

        calib: Dict[str, float] = {}
        for layer, stats in layer_acc.items():
            acc  = stats["accuracy"] / 100.0           # 0–1
            # Linear: acc=0.40→0.40, acc=0.80→1.60
            mult = self._MIN_MULT + (acc - 0.40) / 0.40 * 1.20
            mult = max(self._MIN_MULT, min(self._MAX_MULT, round(mult, 3)))
            calib[layer] = mult

        with self._lock:
            self._calib_cache = calib
            self._calib_at    = datetime.utcnow()

        return dict(calib)

    # ── Background verifier thread ────────────────────────────────────────────

    def _verify_loop(self) -> None:
        """Daemon: check pending predictions every 30 minutes."""
        _time.sleep(60)   # give the app time to start up first
        while True:
            try:
                self._verify_pending()
            except Exception as e:
                print(f"[Tracker] _verify_loop error: {e}")
            _time.sleep(1800)

    def _verify_pending(self) -> None:
        now = datetime.utcnow()
        try:
            with get_db_context() as db:
                pending = db.query(PredictionOutcome).filter(
                    PredictionOutcome.outcome_checked == False,  # noqa
                    PredictionOutcome.verify_at       <= now,
                ).limit(50).all()

                updated = 0
                for rec in pending:
                    try:
                        self._verify_one(rec)
                        updated += 1
                    except Exception as e:
                        print(f"[Tracker] verify {rec.symbol}#{rec.id}: {e}")

                if updated:
                    print(f"[Tracker] Verified {updated} prediction(s)")
        except Exception as e:
            print(f"[Tracker] _verify_pending error: {e}")

    def _verify_one(self, rec: "PredictionOutcome") -> None:
        """Fetch actual price and evaluate outcome for one record."""
        # yfinance symbol mapping: BTC/USDT → BTC-USD, RELIANCE.NS stays
        yf_symbol = rec.symbol
        if "/" in yf_symbol:
            base = yf_symbol.split("/")[0]
            yf_symbol = f"{base}-USD"

        actual_price = 0.0
        try:
            fi = yf.Ticker(yf_symbol).fast_info
            actual_price = float(fi.last_price or fi.previous_close or 0)
        except Exception:
            pass

        if actual_price <= 0:
            return  # No data available yet — skip, try next cycle

        entry = rec.price_at_prediction
        pct   = (actual_price - entry) / entry * 100

        direction_correct = (
            (rec.recommendation == "BUY"  and pct > 0) or
            (rec.recommendation == "SELL" and pct < 0) or
            (rec.recommendation == "HOLD" and abs(pct) < 2.0)
        )

        target_hit = False
        stop_hit   = False
        if rec.target_price and rec.stop_loss:
            if rec.recommendation == "BUY":
                target_hit = actual_price >= rec.target_price
                stop_hit   = actual_price <= rec.stop_loss
            elif rec.recommendation == "SELL":
                target_hit = actual_price <= rec.target_price
                stop_hit   = actual_price >= rec.stop_loss

        rec.outcome_checked   = True
        rec.price_at_outcome  = round(actual_price, 6)
        rec.direction_correct = direction_correct
        rec.target_hit        = target_hit
        rec.stop_hit          = stop_hit
        rec.pct_change_actual = round(pct, 3)
        rec.outcome_at        = datetime.utcnow()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(r: "PredictionOutcome") -> Dict:
        return {
            "id":                  r.id,
            "symbol":              r.symbol,
            "predicted_at":        r.predicted_at.isoformat() if r.predicted_at else None,
            "hours":               r.hours,
            "recommendation":      r.recommendation,
            "confidence":          r.confidence,
            "price_at_prediction": r.price_at_prediction,
            "entry":               r.entry_price,
            "stop":                r.stop_loss,
            "target":              r.target_price,
            "risk_reward":         r.risk_reward,
            "direction_correct":   r.direction_correct,
            "target_hit":          r.target_hit,
            "stop_hit":            r.stop_hit,
            "price_at_outcome":    r.price_at_outcome,
            "pct_change_actual":   r.pct_change_actual,
            "outcome_at":          r.outcome_at.isoformat() if r.outcome_at else None,
        }


# Module-level singleton
prediction_tracker = PredictionTracker()
