"""
Market Oracle - ARIMA Model
Classic statistical time-series model for price prediction
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    print("[Warning] statsmodels not available. ARIMA model will use fallback.")


class ARIMAModel:
    """
    ARIMA (AutoRegressive Integrated Moving Average) model.
    Excellent for capturing linear trends and seasonality in time series.
    """
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.order = (5, 1, 2)  # (p, d, q) - will be auto-tuned
        self.last_prices = None
        self.aic = None
        self.forecast_accuracy = None
    
    def _find_best_order(self, data: np.ndarray) -> tuple:
        """Find optimal ARIMA order using AIC"""
        if not ARIMA_AVAILABLE:
            return (5, 1, 2)
        
        best_aic = float('inf')
        best_order = (5, 1, 2)
        
        # Test different combinations
        for p in [1, 2, 3, 5]:
            for d in [0, 1, 2]:
                for q in [0, 1, 2]:
                    try:
                        model = ARIMA(data, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except:
                        continue
        
        return best_order
    
    def train(self, df: pd.DataFrame, verbose: bool = False) -> Dict:
        """Train ARIMA model"""
        self.last_prices = df['close'].astype(float).values
        
        if not ARIMA_AVAILABLE or len(self.last_prices) < 30:
            self.is_trained = True
            return {"status": "trained_fallback", "method": "exponential_smoothing"}
        
        try:
            # Use recent data for training
            train_data = self.last_prices[-252:]  # Last year of data
            
            # Find best order (limited search for speed)
            self.order = self._find_best_order(train_data[-100:])
            
            # Fit model
            self.model = ARIMA(train_data, order=self.order)
            self.fitted_model = self.model.fit()
            self.aic = self.fitted_model.aic
            
            self.is_trained = True
            
            return {
                "status": "trained",
                "method": "arima",
                "order": self.order,
                "aic": float(self.aic)
            }
        except Exception as e:
            print(f"[ARIMA] Training failed, using fallback: {e}")
            self.is_trained = True
            return {"status": "trained_fallback", "error": str(e)}
    
    def predict(self, df: pd.DataFrame, days: int = 7) -> np.ndarray:
        """Generate predictions"""
        if self.last_prices is None:
            self.last_prices = df['close'].astype(float).values
        
        if ARIMA_AVAILABLE and hasattr(self, 'fitted_model') and self.fitted_model:
            try:
                forecast = self.fitted_model.forecast(steps=days)
                return np.array(forecast)
            except:
                pass
        
        # Fallback: Exponential smoothing with trend
        return self._fallback_predict(days)
    
    def _fallback_predict(self, days: int) -> np.ndarray:
        """Fallback prediction using exponential smoothing"""
        prices = self.last_prices[-60:]
        
        # Double exponential smoothing (Holt's method)
        alpha = 0.3
        beta = 0.1
        
        # Initialize
        level = prices[-1]
        trend = (prices[-1] - prices[-5]) / 5
        
        predictions = []
        for i in range(days):
            forecast = level + (i + 1) * trend
            # Dampen trend over time
            dampening = 0.95 ** i
            predictions.append(level + (i + 1) * trend * dampening)
        
        return np.array(predictions)
    
    def get_confidence(self, predictions: np.ndarray) -> float:
        """Calculate confidence based on model fit and data characteristics"""
        if self.last_prices is None:
            return 55.0
        
        base_confidence = 60.0
        
        # AIC bonus (lower is better)
        if self.aic and self.aic < 1000:
            aic_bonus = min(8, (1000 - self.aic) / 200)
        else:
            aic_bonus = 0
        
        # Volatility penalty
        recent = self.last_prices[-30:]
        volatility = np.std(recent) / np.mean(recent)
        volatility_penalty = min(15, volatility * 100)
        
        # Trend consistency bonus
        price_changes = np.diff(recent)
        trend_consistency = abs(np.sum(price_changes > 0) - np.sum(price_changes < 0)) / len(price_changes)
        trend_bonus = trend_consistency * 8
        
        confidence = base_confidence + aic_bonus - volatility_penalty + trend_bonus
        return max(45.0, min(75.0, confidence))
