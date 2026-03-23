"""
NexusTrader - LightGBM Prediction Model
Gradient boosting with leaf-wise tree growth — faster and often more accurate
than XGBoost for financial time-series with many features.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("[LightGBM] Not available — LightGBM model disabled")

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error


class LightGBMModel:
    """
    LightGBM gradient boosting model optimised for financial prediction.
    Uses leaf-wise tree growth (lower loss per iteration than XGBoost's
    level-wise approach) with comprehensive lag/rolling feature engineering.
    """

    def __init__(self, n_estimators: int = 500, max_depth: int = -1,
                 num_leaves: int = 63, learning_rate: float = 0.02):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.learning_rate = learning_rate
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names: List[str] = []
        self.training_mae = None
        self.validation_mae = None

    # ── Feature engineering ───────────────────────────────────────────────────
    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create a rich feature matrix from OHLCV data.
        Includes lags, rolling statistics, momentum, and volatility features.
        """
        close = df['close'].astype(float)
        high  = df['high'].astype(float) if 'high' in df.columns else close
        low   = df['low'].astype(float)  if 'low'  in df.columns else close
        volume = df['volume'].astype(float) if 'volume' in df.columns else pd.Series(
            np.ones(len(df)), index=df.index)

        feat = pd.DataFrame(index=df.index)

        # Log-returns
        feat['log_return'] = np.log(close / close.shift(1))

        # Lag features (1-21 days)
        for lag in [1, 2, 3, 5, 7, 10, 14, 21]:
            feat[f'close_lag_{lag}'] = close.shift(lag)
            feat[f'return_lag_{lag}'] = close.pct_change(lag)

        # Rolling stats
        for w in [5, 10, 20, 50]:
            feat[f'roll_mean_{w}']  = close.rolling(w).mean()
            feat[f'roll_std_{w}']   = close.rolling(w).std()
            feat[f'roll_min_{w}']   = close.rolling(w).min()
            feat[f'roll_max_{w}']   = close.rolling(w).max()
            feat[f'roll_range_{w}'] = feat[f'roll_max_{w}'] - feat[f'roll_min_{w}']
            feat[f'price_vs_mean_{w}'] = (close - feat[f'roll_mean_{w}']) / (feat[f'roll_std_{w}'] + 1e-9)

        # Moving averages & crossovers
        for p in [5, 10, 20, 50, 100, 200]:
            if len(close) > p:
                feat[f'sma_{p}'] = close.rolling(p).mean()
                feat[f'ema_{p}'] = close.ewm(span=p, adjust=False).mean()
                feat[f'close_vs_sma_{p}'] = (close - feat[f'sma_{p}']) / (feat[f'sma_{p}'] + 1e-9)

        # RSI (14)
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / (loss + 1e-9)
        feat['rsi_14'] = 100 - (100 / (1 + rs))
        feat['rsi_overbought'] = (feat['rsi_14'] > 70).astype(int)
        feat['rsi_oversold']   = (feat['rsi_14'] < 30).astype(int)

        # RSI (7)
        gain7  = delta.clip(lower=0).rolling(7).mean()
        loss7  = (-delta.clip(upper=0)).rolling(7).mean()
        rs7    = gain7 / (loss7 + 1e-9)
        feat['rsi_7'] = 100 - (100 / (1 + rs7))

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        feat['macd']        = ema12 - ema26
        feat['macd_signal'] = feat['macd'].ewm(span=9, adjust=False).mean()
        feat['macd_hist']   = feat['macd'] - feat['macd_signal']
        feat['macd_cross']  = (feat['macd'] > feat['macd_signal']).astype(int)

        # Bollinger Bands
        bb_mid   = close.rolling(20).mean()
        bb_std   = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        feat['bb_pos']   = (close - bb_lower) / (bb_upper - bb_lower + 1e-9)
        feat['bb_width'] = (bb_upper - bb_lower) / (bb_mid + 1e-9)
        feat['bb_squeeze'] = (feat['bb_width'] < feat['bb_width'].rolling(50).mean()).astype(int)

        # ATR & Volatility
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        feat['atr_14']     = tr.rolling(14).mean()
        feat['atr_pct']    = feat['atr_14'] / (close + 1e-9)
        feat['volatility'] = close.pct_change().rolling(20).std()

        # Stochastic %K / %D
        low14  = low.rolling(14).min()
        high14 = high.rolling(14).max()
        feat['stoch_k'] = 100 * (close - low14) / (high14 - low14 + 1e-9)
        feat['stoch_d'] = feat['stoch_k'].rolling(3).mean()

        # Momentum & ROC
        for p in [3, 7, 14, 21]:
            feat[f'momentum_{p}'] = close - close.shift(p)
            feat[f'roc_{p}']      = (close - close.shift(p)) / (close.shift(p) + 1e-9)

        # Volume features
        feat['volume_sma20']    = volume.rolling(20).mean()
        feat['volume_ratio']    = volume / (feat['volume_sma20'] + 1e-9)
        feat['volume_trend']    = volume.rolling(5).mean() / (volume.rolling(20).mean() + 1e-9)
        # OBV
        obv_sign = np.sign(close.diff().fillna(0))
        feat['obv'] = (obv_sign * volume).cumsum()
        feat['obv_sma20'] = feat['obv'].rolling(20).mean()
        feat['obv_divergence'] = feat['obv'] - feat['obv_sma20']

        # CCI
        tp = (high + low + close) / 3
        feat['cci'] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std() + 1e-9)

        # Williams %R
        feat['williams_r'] = -100 * (high14 - close) / (high14 - low14 + 1e-9)

        # Price acceleration (2nd derivative)
        feat['price_accel'] = close.diff().diff()

        # Calendar features
        if hasattr(df.index, 'dayofweek'):
            feat['day_of_week'] = df.index.dayofweek
            feat['month']       = df.index.month
            feat['quarter']     = df.index.quarter
        else:
            feat['day_of_week'] = 0
            feat['month']       = 1
            feat['quarter']     = 1

        # Gap (open-close)
        if 'open' in df.columns:
            feat['gap'] = (df['open'].astype(float) - close.shift(1)) / (close.shift(1) + 1e-9)
            feat['body'] = (close - df['open'].astype(float)).abs() / (close + 1e-9)
        else:
            feat['gap'] = 0
            feat['body'] = 0

        return feat

    # ── Training ──────────────────────────────────────────────────────────────
    def train(self, df: pd.DataFrame, verbose: bool = False) -> Dict:
        if not HAS_LIGHTGBM:
            return {"error": "LightGBM not installed", "mae": None}

        try:
            df = df.copy()
            df.columns = [c.lower() for c in df.columns]

            feat = self._build_features(df)
            # Target: next-day return (more stationary than raw price)
            target = df['close'].astype(float).pct_change().shift(-1)

            combined = feat.join(target.rename('target'))
            combined = combined.replace([np.inf, -np.inf], np.nan).dropna()

            if len(combined) < 60:
                return {"error": "Insufficient data", "mae": None}

            X = combined.drop('target', axis=1)
            y = combined['target']
            self.feature_names = list(X.columns)

            # TimeSeriesSplit validation
            tscv = TimeSeriesSplit(n_splits=5)
            val_maes = []
            X_np = X.values
            y_np = y.values

            # Scale features
            X_scaled = self.scaler.fit_transform(X_np)

            for train_idx, val_idx in tscv.split(X_scaled):
                X_tr, X_val = X_scaled[train_idx], X_scaled[val_idx]
                y_tr, y_val = y_np[train_idx],     y_np[val_idx]

                m = lgb.LGBMRegressor(
                    n_estimators=self.n_estimators,
                    num_leaves=self.num_leaves,
                    max_depth=self.max_depth,
                    learning_rate=self.learning_rate,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    min_child_samples=20,
                    reg_alpha=0.1,
                    reg_lambda=0.1,
                    n_jobs=-1,
                    verbose=-1,
                )
                m.fit(X_tr, y_tr,
                      eval_set=[(X_val, y_val)],
                      callbacks=[lgb.early_stopping(50, verbose=False),
                                 lgb.log_evaluation(-1)])
                preds = m.predict(X_val)
                val_maes.append(mean_absolute_error(y_val, preds))

            # Final model on all data
            self.model = lgb.LGBMRegressor(
                n_estimators=self.n_estimators,
                num_leaves=self.num_leaves,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_samples=20,
                reg_alpha=0.1,
                reg_lambda=0.1,
                n_jobs=-1,
                verbose=-1,
            )
            self.model.fit(X_scaled, y_np)
            self.validation_mae = float(np.mean(val_maes))
            self.is_trained = True

            return {
                "status": "trained",
                "validation_mae": self.validation_mae,
                "n_features": len(self.feature_names),
            }

        except Exception as e:
            print(f"[LightGBM] Training failed: {e}")
            self.is_trained = False
            return {"error": str(e)}

    # ── Prediction ────────────────────────────────────────────────────────────
    def predict(self, df: pd.DataFrame, days: int = 7) -> np.ndarray:
        if not HAS_LIGHTGBM or not self.is_trained or self.model is None:
            return self._fallback_predict(df, days)

        try:
            df = df.copy()
            df.columns = [c.lower() for c in df.columns]
            current_price = float(df['close'].iloc[-1])

            # Rolling forecast: each step appends the predicted price
            sim_df = df.copy()
            predictions = []

            for _ in range(days):
                feat = self._build_features(sim_df)
                last_row = feat.iloc[[-1]]

                # Align columns to training features
                for col in self.feature_names:
                    if col not in last_row.columns:
                        last_row[col] = 0
                last_row = last_row[self.feature_names]
                last_row = last_row.replace([np.inf, -np.inf], np.nan).fillna(0)

                X_scaled = self.scaler.transform(last_row.values)
                pred_return = float(self.model.predict(X_scaled)[0])

                # Dampen extreme predictions (max ±5% per day)
                pred_return = np.clip(pred_return, -0.05, 0.05)
                next_price  = float(sim_df['close'].iloc[-1]) * (1 + pred_return)
                predictions.append(next_price)

                # Append synthetic row
                new_row = sim_df.iloc[[-1]].copy()
                new_row['close'] = next_price
                if 'high' in new_row.columns:
                    new_row['high'] = next_price * 1.005
                if 'low' in new_row.columns:
                    new_row['low'] = next_price * 0.995
                sim_df = pd.concat([sim_df, new_row], ignore_index=True)

            return np.array(predictions)

        except Exception as e:
            print(f"[LightGBM] Prediction failed: {e}")
            return self._fallback_predict(df, days)

    def _fallback_predict(self, df: pd.DataFrame, days: int) -> np.ndarray:
        """Linear trend fallback"""
        prices = df['close'].astype(float).tail(30).values
        x = np.arange(len(prices))
        slope, intercept = np.polyfit(x, prices, 1)
        return np.array([intercept + slope * (len(prices) + i) for i in range(days)])

    def get_confidence(self) -> float:
        """Return model confidence based on validation MAE"""
        if not self.is_trained or self.validation_mae is None:
            return 50.0
        # Lower MAE → higher confidence. Typical return MAE is 0.005–0.02
        base = 92.0
        mae_penalty = min(12.0, self.validation_mae * 800)
        return float(np.clip(base - mae_penalty, 72.0, 96.0))

    def get_top_features(self, n: int = 10) -> List[Dict]:
        if not self.is_trained or self.model is None or not HAS_LIGHTGBM:
            return []
        importances = self.model.feature_importances_
        top_idx = np.argsort(importances)[-n:][::-1]
        return [
            {"feature": self.feature_names[i], "importance": float(importances[i])}
            for i in top_idx if i < len(self.feature_names)
        ]
