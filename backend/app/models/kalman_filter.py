"""
Kalman Filter for real-time price smoothing and trend extraction.
State vector: [price, velocity, acceleration]
Pure numpy — no extra dependencies required.

Why Kalman for markets?
  - Optimally balances trust in historical model vs noisy new measurement
  - Tracks true underlying price separate from market microstructure noise
  - Velocity component is a real-time momentum proxy
  - Uncertainty output flags when signal reliability drops (choppy markets)
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional


class KalmanPriceFilter:
    """
    3-state Kalman filter: [price, velocity, acceleration].

    - process_noise (Q): how fast the true state can change; higher = more
      responsive to new data but less smooth.
    - measurement_noise (R): how noisy raw prices are; higher = trust model
      more than raw price (smoother but laggier).
    Both are auto-tuned from the price series volatility at runtime.
    """

    def __init__(
        self,
        process_noise: float = 0.001,
        measurement_noise: float = 0.01,
        initial_uncertainty: float = 1.0,
    ):
        self.Q_base = process_noise
        self.R_base = measurement_noise
        self.P0 = initial_uncertainty

        # State transition: constant-velocity + acceleration model
        self.F = np.array([
            [1, 1, 0.5],  # price  ← price + velocity + 0.5*accel
            [0, 1, 1  ],  # velocity ← velocity + accel
            [0, 0, 1  ],  # accel stays constant
        ], dtype=float)

        # Observation matrix: we observe price only
        self.H = np.array([[1.0, 0.0, 0.0]])

    # ── Private helpers ───────────────────────────────────────────────────────

    def _tune_noise(self, prices: np.ndarray) -> tuple:
        """Auto-scale Q and R to the price series volatility."""
        returns = np.diff(prices) / (np.abs(prices[:-1]) + 1e-9)
        vol = float(np.std(returns))
        vol = max(vol, 1e-6)
        R_val = vol ** 2 * 2.0
        Q_mat = np.eye(3) * (vol ** 2 * 0.1)
        return Q_mat, R_val

    # ── Public API ────────────────────────────────────────────────────────────

    def filter(self, prices: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Run forward Kalman pass on a price series.

        Returns:
            smoothed     — noise-reduced price estimate
            velocity     — rate of change (momentum proxy, in price units/bar)
            acceleration — second derivative
            uncertainty  — filter P[0,0]; high = less reliable
        """
        prices = np.asarray(prices, dtype=float)
        n = len(prices)

        smoothed = np.empty(n)
        velocity = np.empty(n)
        acceleration = np.empty(n)
        uncertainty = np.empty(n)

        Q_mat, R_val = self._tune_noise(prices)

        # Initialise state
        x = np.array([prices[0], 0.0, 0.0])
        P = np.eye(3) * self.P0

        for i, z in enumerate(prices):
            # Predict
            x_pred = self.F @ x
            P_pred = self.F @ P @ self.F.T + Q_mat

            # Update
            innov = z - float(self.H @ x_pred)
            S = float(self.H @ P_pred @ self.H.T) + R_val
            K = (P_pred @ self.H.T) / S           # shape (3,1)

            x = x_pred + K.flatten() * innov
            P = (np.eye(3) - np.outer(K.flatten(), self.H[0])) @ P_pred

            smoothed[i] = x[0]
            velocity[i] = x[1]
            acceleration[i] = x[2]
            uncertainty[i] = P[0, 0]

        return {
            "smoothed": smoothed,
            "velocity": velocity,
            "acceleration": acceleration,
            "uncertainty": uncertainty,
        }

    def apply_to_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply Kalman filter to an OHLCV DataFrame.
        Adds kalman_price, kalman_velocity, kalman_uncertainty, kalman_trend.
        Returns a copy — original df is not modified.
        """
        out = df.copy()
        col = "close" if "close" in df.columns else "Close"
        prices = df[col].values.astype(float)

        res = self.filter(prices)
        out["kalman_price"] = res["smoothed"]
        out["kalman_velocity"] = res["velocity"]
        out["kalman_uncertainty"] = res["uncertainty"]

        # Normalise velocity to % terms for trend classification
        norm_vel = res["velocity"] / (np.abs(prices) + 1e-9)
        thresh = float(np.std(norm_vel)) * 0.5
        out["kalman_trend"] = np.where(
            norm_vel > thresh, "up",
            np.where(norm_vel < -thresh, "down", "sideways")
        )
        return out

    def get_trend_signal(self, df: pd.DataFrame) -> Dict:
        """
        Quick summary signal for scanner integration.
        Score range: −100 (strong downtrend) to +100 (strong uptrend).
        """
        col = "close" if "close" in df.columns else "Close"
        prices = df[col].values.astype(float)
        res = self.filter(prices)

        last_vel = float(res["velocity"][-1])
        last_unc = float(res["uncertainty"][-1])
        last_smooth = float(res["smoothed"][-1])
        raw_price = float(prices[-1])

        # Velocity in % per bar → score
        vel_pct = last_vel / (abs(raw_price) + 1e-9) * 100
        score = float(np.clip(vel_pct * 50, -100, 100))

        # Uncertainty penalty: high uncertainty reduces score magnitude
        unc_penalty = min(last_unc / (abs(raw_price) + 1e-9) * 10, 0.8)
        score *= (1.0 - unc_penalty)

        return {
            "kalman_price": round(last_smooth, 4),
            "kalman_velocity": round(last_vel, 6),
            "kalman_uncertainty": round(last_unc, 6),
            "vel_pct": round(vel_pct, 4),
            "score": round(score, 2),
            "signal": "BUY" if score > 5 else ("SELL" if score < -5 else "HOLD"),
        }


# ── Module-level convenience ──────────────────────────────────────────────────

def apply_kalman(df: pd.DataFrame) -> pd.DataFrame:
    """One-liner: apply Kalman filter to OHLCV df, return enriched copy."""
    return KalmanPriceFilter().apply_to_df(df)
