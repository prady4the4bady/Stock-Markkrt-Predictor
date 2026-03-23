"""
Market Oracle - Advanced Technical Analysis
Support/Resistance, Fibonacci, Volume Analysis, and Signal Generation
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy.signal import argrelextrema


class AdvancedTechnicalAnalysis:
    """
    Advanced technical analysis for enhanced prediction confidence
    and trading signals.
    """
    
    @staticmethod
    def find_support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 5) -> Dict:
        """
        Find key support and resistance levels using local extrema
        """
        prices = df['close'].astype(float).values
        highs = df['high'].astype(float).values
        lows = df['low'].astype(float).values
        
        # Find local maxima (resistance) and minima (support)
        resistance_idx = argrelextrema(highs, np.greater, order=window)[0]
        support_idx = argrelextrema(lows, np.less, order=window)[0]
        
        # Get price levels
        resistance_levels = sorted(highs[resistance_idx], reverse=True)[:num_levels]
        support_levels = sorted(lows[support_idx])[:num_levels]
        
        current_price = prices[-1]
        
        # Find nearest levels
        nearest_resistance = min([r for r in resistance_levels if r > current_price], default=current_price * 1.05)
        nearest_support = max([s for s in support_levels if s < current_price], default=current_price * 0.95)
        
        return {
            "resistance_levels": [float(r) for r in resistance_levels],
            "support_levels": [float(s) for s in support_levels],
            "nearest_resistance": float(nearest_resistance),
            "nearest_support": float(nearest_support),
            "distance_to_resistance": float((nearest_resistance - current_price) / current_price * 100),
            "distance_to_support": float((current_price - nearest_support) / current_price * 100),
            "current_price": float(current_price)
        }
    
    @staticmethod
    def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = 100) -> Dict:
        """
        Calculate Fibonacci retracement and extension levels
        """
        recent_data = df.tail(lookback)
        high = recent_data['high'].max()
        low = recent_data['low'].min()
        current = df['close'].iloc[-1]
        
        diff = high - low
        
        # Fibonacci retracement levels
        fib_levels = {
            "0.0": float(high),
            "0.236": float(high - diff * 0.236),
            "0.382": float(high - diff * 0.382),
            "0.5": float(high - diff * 0.5),
            "0.618": float(high - diff * 0.618),
            "0.786": float(high - diff * 0.786),
            "1.0": float(low),
        }
        
        # Extension levels
        fib_extensions = {
            "1.272": float(low - diff * 0.272),
            "1.618": float(low - diff * 0.618),
            "2.0": float(low - diff * 1.0),
        }
        
        # Determine trend direction
        is_uptrend = current > (high + low) / 2
        
        return {
            "retracement_levels": fib_levels,
            "extension_levels": fib_extensions,
            "trend": "uptrend" if is_uptrend else "downtrend",
            "high": float(high),
            "low": float(low),
            "current": float(current)
        }
    
    @staticmethod
    def volume_analysis(df: pd.DataFrame) -> Dict:
        """
        Analyze volume patterns for confirmation signals
        """
        prices = df['close'].astype(float).values
        volumes = df['volume'].astype(float).values
        
        # VWAP (Volume Weighted Average Price)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        cumulative_tp_vol = (typical_price * df['volume']).cumsum()
        cumulative_vol = df['volume'].cumsum()
        vwap = cumulative_tp_vol / cumulative_vol
        
        current_vwap = float(vwap.iloc[-1])
        current_price = prices[-1]
        
        # Volume trend (is volume increasing?)
        recent_vol = volumes[-20:]
        vol_sma_short = np.mean(volumes[-5:])
        vol_sma_long = np.mean(volumes[-20:])
        volume_trend = "increasing" if vol_sma_short > vol_sma_long else "decreasing"
        
        # Volume spike detection
        vol_std = np.std(volumes[-30:])
        vol_mean = np.mean(volumes[-30:])
        current_vol = volumes[-1]
        is_volume_spike = current_vol > (vol_mean + 2 * vol_std)
        
        # On-Balance Volume trend
        obv = np.zeros(len(prices))
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv[i] = obv[i-1] + volumes[i]
            elif prices[i] < prices[i-1]:
                obv[i] = obv[i-1] - volumes[i]
            else:
                obv[i] = obv[i-1]
        
        obv_trend = "bullish" if obv[-1] > obv[-10] else "bearish"
        
        # Price-Volume relationship
        price_up = prices[-1] > prices[-2]
        vol_up = volumes[-1] > vol_mean
        
        if price_up and vol_up:
            pv_signal = "strong_bullish"
        elif price_up and not vol_up:
            pv_signal = "weak_bullish"
        elif not price_up and vol_up:
            pv_signal = "strong_bearish"
        else:
            pv_signal = "weak_bearish"
        
        return {
            "vwap": current_vwap,
            "price_vs_vwap": "above" if current_price > current_vwap else "below",
            "volume_trend": volume_trend,
            "is_volume_spike": bool(is_volume_spike),
            "obv_trend": obv_trend,
            "price_volume_signal": pv_signal,
            "avg_volume": float(vol_mean),
            "current_volume": float(current_vol),
            "volume_ratio": float(current_vol / vol_mean)
        }
    
    @staticmethod
    def generate_trading_signals(df: pd.DataFrame) -> Dict:
        """
        Generate comprehensive trading signals from multiple indicators
        """
        prices = df['close'].astype(float).values
        
        # Moving average signals
        sma_20 = pd.Series(prices).rolling(20).mean().values
        sma_50 = pd.Series(prices).rolling(50).mean().values
        ema_12 = pd.Series(prices).ewm(span=12).mean().values
        ema_26 = pd.Series(prices).ewm(span=26).mean().values
        
        # RSI
        delta = pd.Series(prices).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1])
        
        # MACD
        macd = ema_12 - ema_26
        macd_signal = pd.Series(macd).ewm(span=9).mean().values
        macd_histogram = macd - macd_signal
        
        # Bollinger Bands
        bb_middle = pd.Series(prices).rolling(20).mean()
        bb_std = pd.Series(prices).rolling(20).std()
        bb_upper = bb_middle + 2 * bb_std
        bb_lower = bb_middle - 2 * bb_std
        
        current_price = prices[-1]
        
        # Generate signals
        signals = []
        signal_strength = 0
        
        # MA Crossover
        if sma_20[-1] > sma_50[-1] and sma_20[-2] <= sma_50[-2]:
            signals.append({"signal": "Golden Cross", "type": "bullish", "strength": 3})
            signal_strength += 3
        elif sma_20[-1] < sma_50[-1] and sma_20[-2] >= sma_50[-2]:
            signals.append({"signal": "Death Cross", "type": "bearish", "strength": -3})
            signal_strength -= 3
        
        # Price vs MAs
        if current_price > sma_20[-1] > sma_50[-1]:
            signals.append({"signal": "Price above MAs (Bullish)", "type": "bullish", "strength": 2})
            signal_strength += 2
        elif current_price < sma_20[-1] < sma_50[-1]:
            signals.append({"signal": "Price below MAs (Bearish)", "type": "bearish", "strength": -2})
            signal_strength -= 2
        
        # RSI signals
        if current_rsi < 30:
            signals.append({"signal": "RSI Oversold", "type": "bullish", "strength": 2})
            signal_strength += 2
        elif current_rsi > 70:
            signals.append({"signal": "RSI Overbought", "type": "bearish", "strength": -2})
            signal_strength -= 2
        
        # MACD signals
        if macd[-1] > macd_signal[-1] and macd[-2] <= macd_signal[-2]:
            signals.append({"signal": "MACD Bullish Crossover", "type": "bullish", "strength": 2})
            signal_strength += 2
        elif macd[-1] < macd_signal[-1] and macd[-2] >= macd_signal[-2]:
            signals.append({"signal": "MACD Bearish Crossover", "type": "bearish", "strength": -2})
            signal_strength -= 2
        
        # Bollinger Band signals
        if current_price <= bb_lower.iloc[-1]:
            signals.append({"signal": "Price at Lower BB (Oversold)", "type": "bullish", "strength": 2})
            signal_strength += 2
        elif current_price >= bb_upper.iloc[-1]:
            signals.append({"signal": "Price at Upper BB (Overbought)", "type": "bearish", "strength": -2})
            signal_strength -= 2
        
        # Determine overall signal
        if signal_strength >= 4:
            overall = "STRONG BUY"
        elif signal_strength >= 2:
            overall = "BUY"
        elif signal_strength <= -4:
            overall = "STRONG SELL"
        elif signal_strength <= -2:
            overall = "SELL"
        else:
            overall = "HOLD"
        
        return {
            "signals": signals,
            "signal_strength": signal_strength,
            "overall_signal": overall,
            "rsi": current_rsi,
            "macd": float(macd[-1]),
            "macd_signal": float(macd_signal[-1]),
            "macd_histogram": float(macd_histogram[-1]),
            "bb_upper": float(bb_upper.iloc[-1]),
            "bb_lower": float(bb_lower.iloc[-1]),
            "bb_middle": float(bb_middle.iloc[-1])
        }
    
    @staticmethod
    def calculate_trend_strength(df: pd.DataFrame) -> Dict:
        """
        Calculate trend strength using ADX and other metrics
        """
        prices = df['close'].astype(float).values
        highs = df['high'].astype(float).values
        lows = df['low'].astype(float).values
        
        # ADX calculation (simplified)
        tr = np.maximum(highs[1:] - lows[1:], 
                        np.maximum(np.abs(highs[1:] - prices[:-1]), 
                                   np.abs(lows[1:] - prices[:-1])))
        
        plus_dm = np.where((highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]),
                           np.maximum(highs[1:] - highs[:-1], 0), 0)
        minus_dm = np.where((lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]),
                            np.maximum(lows[:-1] - lows[1:], 0), 0)
        
        period = 14
        tr_smooth = pd.Series(tr).rolling(period).mean().values
        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean().values / (tr_smooth + 1e-10)
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean().values / (tr_smooth + 1e-10)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = pd.Series(dx).rolling(period).mean().values[-1]
        
        # Trend direction
        if plus_di[-1] > minus_di[-1]:
            trend_direction = "bullish"
        else:
            trend_direction = "bearish"
        
        # Trend strength interpretation
        if adx < 20:
            strength = "weak/no_trend"
        elif adx < 40:
            strength = "moderate"
        elif adx < 60:
            strength = "strong"
        else:
            strength = "very_strong"
        
        return {
            "adx": float(adx),
            "plus_di": float(plus_di[-1]),
            "minus_di": float(minus_di[-1]),
            "trend_direction": trend_direction,
            "trend_strength": strength
        }
    
    @staticmethod
    def get_analysis_summary(df: pd.DataFrame) -> Dict:
        """
        Get complete technical analysis summary
        """
        sr = AdvancedTechnicalAnalysis.find_support_resistance(df)
        fib = AdvancedTechnicalAnalysis.calculate_fibonacci_levels(df)
        vol = AdvancedTechnicalAnalysis.volume_analysis(df)
        signals = AdvancedTechnicalAnalysis.generate_trading_signals(df)
        trend = AdvancedTechnicalAnalysis.calculate_trend_strength(df)
        
        # Calculate confidence boost based on signal agreement
        confidence_factors = []
        
        # Strong signals boost confidence
        if abs(signals['signal_strength']) >= 4:
            confidence_factors.append(8)
        elif abs(signals['signal_strength']) >= 2:
            confidence_factors.append(4)
        
        # Strong trend boosts confidence
        if trend['trend_strength'] in ['strong', 'very_strong']:
            confidence_factors.append(6)
        elif trend['trend_strength'] == 'moderate':
            confidence_factors.append(3)
        
        # Volume confirmation boosts confidence
        if vol['price_volume_signal'] in ['strong_bullish', 'strong_bearish']:
            confidence_factors.append(4)
        
        # Near support/resistance reduces confidence (reversal possible)
        if sr['distance_to_resistance'] < 2 or sr['distance_to_support'] < 2:
            confidence_factors.append(-3)
        
        confidence_boost = sum(confidence_factors)
        
        return {
            "support_resistance": sr,
            "fibonacci": fib,
            "volume_analysis": vol,
            "trading_signals": signals,
            "trend_analysis": trend,
            "confidence_boost": confidence_boost,
            "summary": {
                "overall_signal": signals['overall_signal'],
                "trend": trend['trend_direction'],
                "trend_strength": trend['trend_strength'],
                "volume_confirmation": vol['price_volume_signal']
            }
        }
