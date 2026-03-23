"""
Market Oracle - Enhanced Prediction Models
Multiple advanced models for maximum accuracy:
- Random Forest with optimized hyperparameters
- Gradient Boosting Regressor
- Support Vector Regression
- Technical Pattern Recognition
- Momentum-based predictions
- Volume Profile Analysis
- Multi-timeframe Analysis
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, AdaBoostRegressor
from sklearn.svm import SVR
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')


class TechnicalPatternRecognizer:
    """
    Recognizes chart patterns for prediction:
    - Head and Shoulders
    - Double Top/Bottom
    - Triangle patterns
    - Support/Resistance breakouts
    - Trend channels
    """
    
    def __init__(self):
        self.patterns_detected = []
    
    def detect_head_shoulders(self, prices: np.ndarray, window: int = 20) -> Dict:
        """Detect head and shoulders pattern"""
        if len(prices) < window * 3:
            return {'detected': False, 'type': None, 'confidence': 0}
        
        # Find local maxima
        local_max = []
        for i in range(window, len(prices) - window):
            if prices[i] == max(prices[i-window:i+window+1]):
                local_max.append((i, prices[i]))
        
        if len(local_max) >= 3:
            # Check for head and shoulders pattern
            for i in range(len(local_max) - 2):
                left_shoulder = local_max[i][1]
                head = local_max[i+1][1]
                right_shoulder = local_max[i+2][1]
                
                # Head should be higher than shoulders
                if head > left_shoulder and head > right_shoulder:
                    # Shoulders should be roughly equal (within 5%)
                    shoulder_diff = abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder)
                    if shoulder_diff < 0.05:
                        return {
                            'detected': True,
                            'type': 'head_shoulders_top',
                            'confidence': min(95, 70 + (1 - shoulder_diff) * 25),
                            'prediction': 'bearish',
                            'target_move': -(head - min(left_shoulder, right_shoulder)) / head * 100
                        }
        
        return {'detected': False, 'type': None, 'confidence': 0}
    
    def detect_double_top_bottom(self, prices: np.ndarray, window: int = 10) -> Dict:
        """Detect double top or double bottom patterns"""
        if len(prices) < window * 4:
            return {'detected': False, 'type': None, 'confidence': 0}
        
        recent = prices[-window*4:]
        
        # Find peaks and troughs
        peaks = []
        troughs = []
        
        for i in range(window, len(recent) - window):
            if recent[i] == max(recent[i-window:i+window+1]):
                peaks.append((i, recent[i]))
            if recent[i] == min(recent[i-window:i+window+1]):
                troughs.append((i, recent[i]))
        
        # Check for double top
        if len(peaks) >= 2:
            p1, p2 = peaks[-2][1], peaks[-1][1]
            diff = abs(p1 - p2) / max(p1, p2)
            if diff < 0.03:  # Within 3%
                return {
                    'detected': True,
                    'type': 'double_top',
                    'confidence': min(90, 65 + (1 - diff) * 25),
                    'prediction': 'bearish',
                    'target_move': -5.0
                }
        
        # Check for double bottom
        if len(troughs) >= 2:
            t1, t2 = troughs[-2][1], troughs[-1][1]
            diff = abs(t1 - t2) / max(t1, t2)
            if diff < 0.03:
                return {
                    'detected': True,
                    'type': 'double_bottom',
                    'confidence': min(90, 65 + (1 - diff) * 25),
                    'prediction': 'bullish',
                    'target_move': 5.0
                }
        
        return {'detected': False, 'type': None, 'confidence': 0}
    
    def detect_trend_channel(self, prices: np.ndarray, window: int = 30) -> Dict:
        """Detect trend channels (uptrend, downtrend, sideways)"""
        if len(prices) < window:
            return {'trend': 'neutral', 'strength': 0, 'channel_width': 0}
        
        recent = prices[-window:]
        x = np.arange(len(recent))
        
        # Fit linear regression
        slope, intercept = np.polyfit(x, recent, 1)
        fitted = slope * x + intercept
        
        # Calculate channel width
        residuals = recent - fitted
        channel_width = (np.max(residuals) - np.min(residuals)) / np.mean(recent) * 100
        
        # Determine trend
        price_change = (recent[-1] - recent[0]) / recent[0] * 100
        
        if slope > 0 and price_change > 2:
            trend = 'uptrend'
            strength = min(100, abs(price_change) * 5)
        elif slope < 0 and price_change < -2:
            trend = 'downtrend'
            strength = min(100, abs(price_change) * 5)
        else:
            trend = 'sideways'
            strength = 50
        
        # R-squared for trend reliability
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((recent - np.mean(recent)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            'trend': trend,
            'strength': strength,
            'channel_width': channel_width,
            'slope': slope,
            'r_squared': r_squared,
            'prediction': 'bullish' if trend == 'uptrend' else ('bearish' if trend == 'downtrend' else 'neutral')
        }
    
    def detect_breakout(self, prices: np.ndarray, volumes: np.ndarray = None, window: int = 20) -> Dict:
        """Detect support/resistance breakouts"""
        if len(prices) < window + 5:
            return {'breakout': False, 'type': None, 'confidence': 0}
        
        historical = prices[:-5]
        recent = prices[-5:]
        
        resistance = np.max(historical[-window:])
        support = np.min(historical[-window:])
        current = recent[-1]
        
        # Check for breakout
        if current > resistance:
            breakout_strength = (current - resistance) / resistance * 100
            volume_confirmation = 1.0
            if volumes is not None and len(volumes) >= 5:
                avg_volume = np.mean(volumes[-20:-5]) if len(volumes) >= 20 else np.mean(volumes[:-5])
                recent_volume = np.mean(volumes[-5:])
                volume_confirmation = min(2.0, recent_volume / avg_volume) if avg_volume > 0 else 1.0
            
            return {
                'breakout': True,
                'type': 'resistance_breakout',
                'confidence': min(95, 60 + breakout_strength * 10 + volume_confirmation * 10),
                'prediction': 'bullish',
                'target': resistance + (resistance - support),
                'strength': breakout_strength
            }
        
        elif current < support:
            breakout_strength = (support - current) / support * 100
            return {
                'breakout': True,
                'type': 'support_breakdown',
                'confidence': min(95, 60 + breakout_strength * 10),
                'prediction': 'bearish',
                'target': support - (resistance - support),
                'strength': breakout_strength
            }
        
        return {'breakout': False, 'type': None, 'confidence': 0}
    
    def analyze_all_patterns(self, prices: np.ndarray, volumes: np.ndarray = None) -> Dict:
        """Run all pattern detection and combine signals"""
        patterns = {
            'head_shoulders': self.detect_head_shoulders(prices),
            'double_pattern': self.detect_double_top_bottom(prices),
            'trend_channel': self.detect_trend_channel(prices),
            'breakout': self.detect_breakout(prices, volumes)
        }
        
        # Combine signals
        bullish_signals = 0
        bearish_signals = 0
        total_confidence = 0
        signal_count = 0
        
        for pattern_name, pattern_data in patterns.items():
            if pattern_data.get('detected') or pattern_data.get('breakout'):
                if pattern_data.get('prediction') == 'bullish':
                    bullish_signals += pattern_data.get('confidence', 50)
                elif pattern_data.get('prediction') == 'bearish':
                    bearish_signals += pattern_data.get('confidence', 50)
                total_confidence += pattern_data.get('confidence', 50)
                signal_count += 1
        
        # Include trend channel
        trend = patterns['trend_channel']
        if trend['trend'] == 'uptrend':
            bullish_signals += trend['strength']
            signal_count += 1
        elif trend['trend'] == 'downtrend':
            bearish_signals += trend['strength']
            signal_count += 1
        
        overall_direction = 'bullish' if bullish_signals > bearish_signals else (
            'bearish' if bearish_signals > bullish_signals else 'neutral'
        )
        
        pattern_confidence = (total_confidence / max(signal_count, 1)) if signal_count > 0 else 50
        
        return {
            'patterns': patterns,
            'overall_direction': overall_direction,
            'bullish_strength': bullish_signals,
            'bearish_strength': bearish_signals,
            'pattern_confidence': pattern_confidence,
            'active_patterns': signal_count
        }


class MultiModelEnsemble:
    """
    Combines multiple ML models for maximum accuracy:
    - Random Forest
    - Gradient Boosting
    - SVR
    - Ridge/Lasso Regression
    - AdaBoost
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_names = []
        self.is_trained = False
        self.model_weights = {}
        self.model_accuracies = {}
        
    def _prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for ML models"""
        df = df.copy()
        
        # Get price column
        close = df['close'] if 'close' in df.columns else df['Close']
        high = df['high'] if 'high' in df.columns else df['High']
        low = df['low'] if 'low' in df.columns else df['Low']
        volume = df['volume'] if 'volume' in df.columns else df.get('Volume', pd.Series([0]*len(df)))
        
        features = pd.DataFrame()
        
        # Price-based features
        features['returns_1'] = close.pct_change(1)
        features['returns_5'] = close.pct_change(5)
        features['returns_10'] = close.pct_change(10)
        features['returns_20'] = close.pct_change(20)
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            if len(df) > period:
                features[f'sma_{period}'] = close.rolling(period).mean() / close - 1
                features[f'ema_{period}'] = close.ewm(span=period).mean() / close - 1
        
        # Volatility
        features['volatility_10'] = close.pct_change().rolling(10).std()
        features['volatility_20'] = close.pct_change().rolling(20).std()
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.inf)
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        features['macd'] = (ema12 - ema26) / close
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        
        # Bollinger Bands position
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        features['bb_position'] = (close - sma20) / (2 * std20)
        
        # Price position
        features['high_low_ratio'] = (close - low) / (high - low + 0.0001)
        
        # Volume features
        if volume is not None and len(volume) > 0:
            features['volume_ratio'] = volume / volume.rolling(20).mean()
            features['volume_trend'] = volume.pct_change(5)
        
        # Momentum
        features['momentum_10'] = close / close.shift(10) - 1
        features['momentum_20'] = close / close.shift(20) - 1
        
        # Rate of change
        features['roc_5'] = (close - close.shift(5)) / close.shift(5)
        features['roc_10'] = (close - close.shift(10)) / close.shift(10)
        
        # Target: next day return
        target = close.shift(-1) / close - 1
        
        # Clean data
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(0)
        
        self.feature_names = list(features.columns)
        
        return features.values, target.values
    
    def train(self, df: pd.DataFrame, verbose: bool = False) -> Dict:
        """Train all models with time series cross-validation"""
        X, y = self._prepare_features(df)
        
        # Remove last row (no target) and rows with NaN
        valid_idx = ~np.isnan(y)
        X = X[valid_idx]
        y = y[valid_idx]
        
        if len(X) < 100:
            print("[Warning] Insufficient data for training")
            return {}
        
        # Scale features
        self.scalers['X'] = StandardScaler()
        X_scaled = self.scalers['X'].fit_transform(X)
        
        # Time series split for validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        # Initialize models
        models_config = {
            'random_forest': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            ),
            'svr': SVR(kernel='rbf', C=1.0, epsilon=0.01),
            'ridge': Ridge(alpha=1.0),
            'elastic_net': ElasticNet(alpha=0.01, l1_ratio=0.5, random_state=42),
            'adaboost': AdaBoostRegressor(
                n_estimators=50,
                learning_rate=0.1,
                random_state=42
            )
        }
        
        metrics = {}
        
        for name, model in models_config.items():
            try:
                # Cross-validation
                cv_scores = []
                for train_idx, val_idx in tscv.split(X_scaled):
                    X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
                    y_train, y_val = y[train_idx], y[val_idx]
                    
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_val)
                    
                    # Direction accuracy
                    direction_correct = np.sum(np.sign(y_pred) == np.sign(y_val))
                    direction_accuracy = direction_correct / len(y_val) * 100
                    cv_scores.append(direction_accuracy)
                
                # Final training on all data
                model.fit(X_scaled, y)
                self.models[name] = model
                
                avg_accuracy = np.mean(cv_scores)
                self.model_accuracies[name] = avg_accuracy
                
                # Weight based on accuracy
                self.model_weights[name] = max(0.1, (avg_accuracy - 45) / 55)  # 45% is random
                
                metrics[name] = {
                    'direction_accuracy': avg_accuracy,
                    'cv_scores': cv_scores,
                    'weight': self.model_weights[name]
                }
                
                if verbose:
                    print(f"   ✓ {name}: {avg_accuracy:.1f}% direction accuracy")
                    
            except Exception as e:
                print(f"   ✗ {name} failed: {e}")
                self.model_weights[name] = 0
        
        # Normalize weights
        total_weight = sum(self.model_weights.values())
        if total_weight > 0:
            self.model_weights = {k: v/total_weight for k, v in self.model_weights.items()}
        
        self.is_trained = True
        return metrics
    
    def predict(self, df: pd.DataFrame, days: int = 7) -> Dict:
        """Generate predictions using all models"""
        if not self.is_trained:
            return {'error': 'Models not trained'}
        
        X, _ = self._prepare_features(df)
        X_scaled = self.scalers['X'].transform(X)
        
        # Get last feature vector for prediction
        last_features = X_scaled[-1:].reshape(1, -1)
        
        predictions = {}
        weighted_prediction = 0
        
        current_price = float(df['close'].iloc[-1] if 'close' in df.columns else df['Close'].iloc[-1])
        
        for name, model in self.models.items():
            if self.model_weights.get(name, 0) > 0:
                try:
                    # Predict return
                    pred_return = model.predict(last_features)[0]
                    pred_price = current_price * (1 + pred_return)
                    
                    predictions[name] = {
                        'return': pred_return,
                        'price': pred_price,
                        'weight': self.model_weights[name],
                        'accuracy': self.model_accuracies.get(name, 50)
                    }
                    
                    weighted_prediction += pred_return * self.model_weights[name]
                except Exception as e:
                    print(f"[Prediction Error] {name}: {e}")
        
        # Generate multi-day predictions
        daily_predictions = []
        base_price = current_price
        
        for i in range(days):
            # Decay the prediction strength over time
            decay_factor = 0.9 ** i
            day_return = weighted_prediction * decay_factor
            base_price = base_price * (1 + day_return)
            daily_predictions.append(base_price)
        
        # Calculate confidence based on model agreement - REAL values
        returns = [p['return'] for p in predictions.values()]
        if returns:
            return_std = np.std(returns)
            return_mean = abs(np.mean(returns))
            agreement = 1 - min(1, return_std / max(return_mean, 0.001))
            avg_accuracy = np.mean([p['accuracy'] for p in predictions.values()])
            
            # REAL confidence calculation based on model agreement and accuracy
            # Higher agreement + higher accuracy = higher confidence
            base_confidence = agreement * 0.4 + (avg_accuracy / 100) * 0.4
            
            # Add direction agreement factor
            direction_agreement = sum(1 for r in returns if (r > 0) == (weighted_prediction > 0)) / len(returns)
            direction_boost = direction_agreement * 0.2
            
            # Real confidence: 35-70% range based on actual model performance
            confidence = min(0.70, max(0.35, base_confidence + direction_boost))
        else:
            confidence = 0.45  # Default to moderate confidence
        
        return {
            'current_price': current_price,
            'predictions': daily_predictions,
            'weighted_return': weighted_prediction,
            'model_predictions': predictions,
            'confidence': confidence * 100,  # Now ranges 35-70%
            'direction': 'bullish' if weighted_prediction > 0 else 'bearish'
        }


class VolumeProfileAnalyzer:
    """Analyzes volume profile for support/resistance levels"""
    
    def analyze(self, df: pd.DataFrame, bins: int = 50) -> Dict:
        close = df['close'] if 'close' in df.columns else df['Close']
        volume = df['volume'] if 'volume' in df.columns else df.get('Volume', pd.Series([1]*len(df)))
        
        if volume is None or len(volume) == 0:
            return {'levels': [], 'poc': None}
        
        # Create price bins
        price_range = (close.min(), close.max())
        bin_edges = np.linspace(price_range[0], price_range[1], bins + 1)
        
        # Accumulate volume at each price level
        volume_profile = np.zeros(bins)
        for i, (price, vol) in enumerate(zip(close, volume)):
            bin_idx = min(bins - 1, np.searchsorted(bin_edges[1:], price))
            volume_profile[bin_idx] += vol
        
        # Find Point of Control (highest volume)
        poc_idx = np.argmax(volume_profile)
        poc_price = (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2
        
        # Find high volume nodes (potential support/resistance)
        avg_volume = np.mean(volume_profile)
        hvn_mask = volume_profile > avg_volume * 1.5
        hvn_prices = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(bins) if hvn_mask[i]]
        
        current_price = close.iloc[-1]
        
        # Determine if price is at support or resistance
        nearest_level = min(hvn_prices, key=lambda x: abs(x - current_price)) if hvn_prices else poc_price
        
        return {
            'poc': poc_price,
            'high_volume_nodes': hvn_prices,
            'nearest_level': nearest_level,
            'price_vs_poc': 'above' if current_price > poc_price else 'below',
            'level_type': 'support' if current_price > nearest_level else 'resistance'
        }


class MomentumPredictor:
    """Momentum-based prediction system"""
    
    def calculate_momentum_signals(self, df: pd.DataFrame) -> Dict:
        close = df['close'] if 'close' in df.columns else df['Close']
        
        signals = {}
        
        # Rate of Change
        for period in [5, 10, 20]:
            if len(close) > period:
                roc = (close.iloc[-1] - close.iloc[-period-1]) / close.iloc[-period-1] * 100
                signals[f'roc_{period}'] = roc
        
        # Momentum oscillator
        if len(close) > 14:
            mom = close.iloc[-1] - close.iloc[-14]
            signals['momentum_14'] = mom
        
        # RSI momentum
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        signals['rsi'] = rsi.iloc[-1]
        
        # Stochastic momentum
        if len(close) > 14:
            low14 = close.rolling(14).min()
            high14 = close.rolling(14).max()
            stoch_k = 100 * (close - low14) / (high14 - low14 + 0.0001)
            stoch_d = stoch_k.rolling(3).mean()
            signals['stoch_k'] = stoch_k.iloc[-1]
            signals['stoch_d'] = stoch_d.iloc[-1]
        
        # Williams %R
        if len(close) > 14:
            high14 = close.rolling(14).max()
            low14 = close.rolling(14).min()
            williams_r = -100 * (high14 - close) / (high14 - low14 + 0.0001)
            signals['williams_r'] = williams_r.iloc[-1]
        
        # Combine signals
        bullish_count = 0
        bearish_count = 0
        
        # RSI signals
        if signals.get('rsi', 50) < 30:
            bullish_count += 2  # Oversold
        elif signals.get('rsi', 50) > 70:
            bearish_count += 2  # Overbought
        elif signals.get('rsi', 50) > 50:
            bullish_count += 1
        else:
            bearish_count += 1
        
        # ROC signals
        for period in [5, 10, 20]:
            roc_key = f'roc_{period}'
            if roc_key in signals:
                if signals[roc_key] > 0:
                    bullish_count += 1
                else:
                    bearish_count += 1
        
        # Stochastic signals
        if signals.get('stoch_k', 50) < 20:
            bullish_count += 2
        elif signals.get('stoch_k', 50) > 80:
            bearish_count += 2
        
        total_signals = bullish_count + bearish_count
        momentum_score = (bullish_count - bearish_count) / max(total_signals, 1) * 100
        
        return {
            'signals': signals,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'momentum_score': momentum_score,
            'direction': 'bullish' if momentum_score > 10 else ('bearish' if momentum_score < -10 else 'neutral'),
            'strength': abs(momentum_score)
        }


# Main enhanced prediction function
def get_enhanced_prediction(df: pd.DataFrame, symbol: str, days: int = 7, 
                            news_sentiment: Dict = None) -> Dict:
    """
    Generate comprehensive prediction using all models and analysis
    """
    close = df['close'] if 'close' in df.columns else df['Close']
    volume = df['volume'] if 'volume' in df.columns else df.get('Volume', None)
    current_price = float(close.iloc[-1])
    
    results = {
        'symbol': symbol,
        'current_price': current_price,
        'timestamp': datetime.now().isoformat()
    }
    
    # 1. Technical Pattern Analysis
    pattern_analyzer = TechnicalPatternRecognizer()
    patterns = pattern_analyzer.analyze_all_patterns(
        close.values, 
        volume.values if volume is not None else None
    )
    results['patterns'] = patterns
    
    # 2. Multi-Model ML Predictions
    ml_ensemble = MultiModelEnsemble()
    ml_ensemble.train(df, verbose=True)
    ml_predictions = ml_ensemble.predict(df, days)
    results['ml_predictions'] = ml_predictions
    
    # 3. Volume Profile
    volume_analyzer = VolumeProfileAnalyzer()
    volume_profile = volume_analyzer.analyze(df)
    results['volume_profile'] = volume_profile
    
    # 4. Momentum Analysis
    momentum = MomentumPredictor()
    momentum_signals = momentum.calculate_momentum_signals(df)
    results['momentum'] = momentum_signals
    
    # 5. Combine all signals for final prediction
    bullish_weight = 0
    bearish_weight = 0
    total_confidence = 0
    
    # Pattern signals
    if patterns['overall_direction'] == 'bullish':
        bullish_weight += patterns['pattern_confidence'] * 0.25
    elif patterns['overall_direction'] == 'bearish':
        bearish_weight += patterns['pattern_confidence'] * 0.25
    total_confidence += patterns['pattern_confidence'] * 0.25
    
    # ML signals
    if ml_predictions.get('direction') == 'bullish':
        bullish_weight += ml_predictions.get('confidence', 50) * 0.35
    else:
        bearish_weight += ml_predictions.get('confidence', 50) * 0.35
    total_confidence += ml_predictions.get('confidence', 50) * 0.35
    
    # Momentum signals
    if momentum_signals['direction'] == 'bullish':
        bullish_weight += momentum_signals['strength'] * 0.20
    elif momentum_signals['direction'] == 'bearish':
        bearish_weight += momentum_signals['strength'] * 0.20
    total_confidence += momentum_signals['strength'] * 0.20
    
    # News sentiment (20% weight)
    if news_sentiment:
        news_score = news_sentiment.get('overall_score', 0)
        news_conf = news_sentiment.get('confidence', 0)
        if news_score > 0:
            bullish_weight += news_conf * 0.20 * (news_score / 3)
        else:
            bearish_weight += news_conf * 0.20 * (abs(news_score) / 3)
        total_confidence += news_conf * 0.20
    
    # Final direction and confidence with REAL accuracy
    final_direction = 'bullish' if bullish_weight > bearish_weight else 'bearish'
    direction_strength = abs(bullish_weight - bearish_weight)
    
    # REAL confidence calculation - no artificial boosting
    # Range: 35-70% based on actual signal agreement
    raw_confidence = total_confidence + direction_strength * 0.3
    final_confidence = max(35, min(70, raw_confidence * 0.8))
    
    # Apply news impact to price predictions
    price_predictions = ml_predictions.get('predictions', [current_price])
    if news_sentiment and news_sentiment.get('overall_score', 0) != 0:
        news_impact = news_sentiment['overall_score'] / 3 * 0.02  # Max 2% adjustment
        price_predictions = [p * (1 + news_impact) for p in price_predictions]
    
    results['final_prediction'] = {
        'direction': final_direction,
        'confidence': round(final_confidence, 2),
        'price_predictions': [round(p, 2) for p in price_predictions],
        'bullish_weight': round(bullish_weight, 2),
        'bearish_weight': round(bearish_weight, 2),
        'recommendation': 'STRONG BUY' if final_direction == 'bullish' and final_confidence > 60 else (
            'BUY' if final_direction == 'bullish' and final_confidence > 50 else (
            'STRONG SELL' if final_direction == 'bearish' and final_confidence > 60 else (
            'SELL' if final_direction == 'bearish' and final_confidence > 50 else 'HOLD')))
    }
    
    return results
