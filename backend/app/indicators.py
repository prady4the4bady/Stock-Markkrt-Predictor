"""
Market Oracle - Technical Indicators (Enhanced)
Comprehensive technical analysis with advanced indicators for better predictions
"""
import pandas as pd
import numpy as np
from typing import Dict


class TechnicalIndicators:
    """
    Technical analysis indicators for stock/crypto prediction.
    Enhanced with additional indicators for better ML model accuracy.
    """
    
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators and add them to the DataFrame
        
        Args:
            df: DataFrame with OHLCV data (must have 'close', 'high', 'low', 'volume')
        
        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()
        
        # Ensure we have numeric data
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # ===== MOVING AVERAGES (Multiple timeframes) =====
        for period in [5, 7, 10, 14, 21, 50, 100, 200]:
            if len(df) > period:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
        
        # Exponential Moving Averages
        for span in [5, 9, 12, 21, 26, 50]:
            df[f'ema_{span}'] = df['close'].ewm(span=span, adjust=False).mean()
        
        # ===== MACD (Enhanced) =====
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        df['macd_crossover'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
        
        # ===== RSI (Multiple periods) =====
        df['rsi'] = TechnicalIndicators.calculate_rsi(df['close'], period=14)
        df['rsi_7'] = TechnicalIndicators.calculate_rsi(df['close'], period=7)
        df['rsi_21'] = TechnicalIndicators.calculate_rsi(df['close'], period=21)
        
        # RSI divergence signals
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        
        # ===== STOCHASTIC OSCILLATOR =====
        stoch = TechnicalIndicators.calculate_stochastic(df)
        df['stoch_k'] = stoch['k']
        df['stoch_d'] = stoch['d']
        df['stoch_crossover'] = np.where(df['stoch_k'] > df['stoch_d'], 1, -1)
        
        # ===== BOLLINGER BANDS =====
        bb = TechnicalIndicators.calculate_bollinger_bands(df['close'], window=20, std_dev=2)
        df['bb_upper'] = bb['upper']
        df['bb_middle'] = bb['middle']
        df['bb_lower'] = bb['lower']
        df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / (df['bb_middle'] + 1e-10)
        df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)
        
        # ===== MOMENTUM INDICATORS =====
        for period in [1, 3, 5, 7, 10, 14, 21]:
            df[f'return_{period}d'] = df['close'].pct_change(period) * 100
        
        # Rate of Change (ROC)
        df['roc_10'] = ((df['close'] - df['close'].shift(10)) / (df['close'].shift(10) + 1e-10)) * 100
        df['roc_20'] = ((df['close'] - df['close'].shift(20)) / (df['close'].shift(20) + 1e-10)) * 100
        
        # ===== VOLATILITY INDICATORS =====
        df['volatility'] = df['close'].rolling(window=20).std()
        df['volatility_ratio'] = df['volatility'] / df['close'].rolling(window=60).std()
        df['atr'] = TechnicalIndicators.calculate_atr(df, period=14)
        df['atr_percent'] = df['atr'] / df['close'] * 100
        
        # ===== WILLIAMS %R =====
        df['williams_r'] = TechnicalIndicators.calculate_williams_r(df)
        
        # ===== CCI =====
        df['cci'] = TechnicalIndicators.calculate_cci(df, period=20)
        
        # ===== ADX (Trend Strength) =====
        adx_data = TechnicalIndicators.calculate_adx(df)
        df['adx'] = adx_data['adx']
        df['plus_di'] = adx_data['plus_di']
        df['minus_di'] = adx_data['minus_di']
        df['adx_trend'] = np.where(df['adx'] > 25, 1, 0)  # Strong trend indicator
        
        # ===== VOLUME INDICATORS =====
        df['obv'] = TechnicalIndicators.calculate_obv(df)
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_sma'] + 1e-10)
        df['volume_trend'] = df['obv'].diff(5)
        
        # VWAP approximation
        df['vwap'] = (df['close'] * df['volume']).cumsum() / (df['volume'].cumsum() + 1e-10)
        df['price_vs_vwap'] = (df['close'] - df['vwap']) / (df['vwap'] + 1e-10) * 100
        
        # ===== PRICE PATTERNS =====
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        df['body_size'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        df['upper_shadow'] = (df['high'] - df[['close', 'open']].max(axis=1)) / (df['high'] - df['low'] + 1e-10)
        df['lower_shadow'] = (df[['close', 'open']].min(axis=1) - df['low']) / (df['high'] - df['low'] + 1e-10)
        
        # ===== TREND INDICATORS =====
        df['trend_sma'] = np.where(df['sma_7'] > df['sma_21'], 1, -1)
        df['trend_ema'] = np.where(df['ema_12'] > df['ema_26'], 1, -1)
        
        # Price relative to moving averages
        if 'sma_50' in df.columns:
            df['price_vs_sma50'] = (df['close'] - df['sma_50']) / (df['sma_50'] + 1e-10) * 100
        if 'sma_200' in df.columns:
            df['price_vs_sma200'] = (df['close'] - df['sma_200']) / (df['sma_200'] + 1e-10) * 100
        
        # ===== STATISTICAL FEATURES =====
        df['zscore'] = (df['close'] - df['close'].rolling(20).mean()) / (df['close'].rolling(20).std() + 1e-10)
        df['skewness'] = df['close'].rolling(20).apply(lambda x: pd.Series(x).skew(), raw=False)
        df['kurtosis'] = df['close'].rolling(20).apply(lambda x: pd.Series(x).kurt(), raw=False)
        
        # ===== LAGGED FEATURES =====
        for lag in [1, 2, 3, 5, 7, 10]:
            df[f'close_lag_{lag}'] = df['close'].shift(lag)
            df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
            df[f'return_lag_{lag}'] = df['return_1d'].shift(lag)
        
        # ===== SUPPORT/RESISTANCE PROXIMITY =====
        df['dist_to_high_20'] = (df['close'].rolling(20).max() - df['close']) / df['close'] * 100
        df['dist_to_low_20'] = (df['close'] - df['close'].rolling(20).min()) / df['close'] * 100
        
        # Fill NaN values
        df = df.bfill().ffill().fillna(0)
        
        # Replace infinities
        df = df.replace([np.inf, -np.inf], 0)
        
        return df
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        return 100 - (100 / (1 + rs))
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator %K and %D"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        k = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-10)
        d = k.rolling(window=d_period).mean()
        
        return {'k': k, 'd': d}
    
    @staticmethod
    def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        
        wr = -100 * (high_max - df['close']) / (high_max - low_min + 1e-10)
        return wr
    
    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Average Directional Index (ADX)"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_dm = pd.Series(plus_dm, index=df.index)
        minus_dm = pd.Series(minus_dm, index=df.index)
        
        # Smoothed DM
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / (atr + 1e-10))
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / (atr + 1e-10))
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=period).mean()
        
        return {'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di}
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, window: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        
        return {
            'upper': middle + (std * std_dev),
            'middle': middle,
            'lower': middle - (std * std_dev)
        }
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range (ATR)"""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index (CCI)"""
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma = tp.rolling(window=period).mean()
        mad = (tp - sma).abs().rolling(window=period).mean()
        cci = (tp - sma) / (0.015 * mad + 1e-10)
        return cci

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume (OBV)"""
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return obv

    @staticmethod
    def calculate_fibonacci_levels(df: pd.DataFrame, window: int = 50) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        high = df['high'].tail(window).max()
        low = df['low'].tail(window).min()
        diff = high - low
        
        return {
            'level_0': float(high),
            'level_236': float(high - diff * 0.236),
            'level_382': float(high - diff * 0.382),
            'level_500': float(high - diff * 0.5),
            'level_618': float(high - diff * 0.618),
            'level_786': float(high - diff * 0.786),
            'level_100': float(low)
        }
    
    @staticmethod
    def calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
        """Calculate classic pivot points"""
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        close = df['close'].iloc[-1]
        
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        return {
            'pivot': float(pivot),
            'r1': float(r1), 'r2': float(r2), 'r3': float(r3),
            's1': float(s1), 's2': float(s2), 's3': float(s3)
        }
    
    @staticmethod
    def calculate_ichimoku(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate Ichimoku Cloud indicators"""
        high = df['high']
        low = df['low']
        
        # Tenkan-sen (Conversion Line)
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        
        # Kijun-sen (Base Line)
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        
        # Senkou Span B (Leading Span B)
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        
        # Chikou Span (Lagging Span)
        chikou = df['close'].shift(-26)
        
        return {
            'tenkan': tenkan,
            'kijun': kijun,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b,
            'chikou': chikou
        }
    
    @staticmethod
    def calculate_market_momentum(df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive market momentum indicators"""
        close = df['close'].astype(float)
        
        # Short-term momentum (5 days)
        short_momentum = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100
        
        # Medium-term momentum (20 days)
        medium_momentum = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100 if len(close) >= 20 else short_momentum
        
        # Long-term momentum (60 days)
        long_momentum = (close.iloc[-1] - close.iloc[-60]) / close.iloc[-60] * 100 if len(close) >= 60 else medium_momentum
        
        # Acceleration (rate of change of momentum)
        if len(close) >= 10:
            recent_momentum = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100
            prev_momentum = (close.iloc[-5] - close.iloc[-10]) / close.iloc[-10] * 100
            acceleration = recent_momentum - prev_momentum
        else:
            acceleration = 0
        
        # Momentum score (0-100)
        momentum_score = 50 + (short_momentum * 2 + medium_momentum + long_momentum * 0.5) / 4
        momentum_score = max(0, min(100, momentum_score))
        
        return {
            'short_momentum': float(short_momentum),
            'medium_momentum': float(medium_momentum),
            'long_momentum': float(long_momentum),
            'acceleration': float(acceleration),
            'momentum_score': float(momentum_score),
            'direction': 'bullish' if momentum_score > 55 else ('bearish' if momentum_score < 45 else 'neutral')
        }
    
    @staticmethod
    def calculate_trend_strength(df: pd.DataFrame, window: int = 20) -> Dict[str, float]:
        """Calculate trend strength using multiple methods"""
        close = df['close'].astype(float).tail(window).values
        x = np.arange(len(close))
        
        # Linear regression for trend
        slope, intercept = np.polyfit(x, close, 1)
        predicted = slope * x + intercept
        
        # R-squared (coefficient of determination)
        ss_res = np.sum((close - predicted) ** 2)
        ss_tot = np.sum((close - np.mean(close)) ** 2)
        r_squared = 1 - (ss_res / (ss_tot + 1e-10))
        
        # Trend direction and strength
        price_change = (close[-1] - close[0]) / close[0] * 100
        trend_strength = abs(price_change) * r_squared
        
        # ADX-like smoothed directional indicator
        if len(df) >= 14:
            adx_val = TechnicalIndicators.calculate_adx(df)['adx'].iloc[-1]
        else:
            adx_val = 50
        
        return {
            'slope': float(slope),
            'r_squared': float(r_squared),
            'price_change_pct': float(price_change),
            'trend_strength': float(trend_strength),
            'adx': float(adx_val) if not np.isnan(adx_val) else 50.0,
            'direction': 'uptrend' if slope > 0 else 'downtrend',
            'is_strong': bool(r_squared > 0.5 and abs(price_change) > 3)
        }

    @staticmethod
    def get_feature_columns() -> list:
        """Get list of all feature columns for ML models"""
        return [
            # Moving Averages
            'sma_5', 'sma_7', 'sma_10', 'sma_14', 'sma_21', 'sma_50', 'sma_100', 'sma_200',
            'ema_5', 'ema_9', 'ema_12', 'ema_21', 'ema_26', 'ema_50',
            # MACD
            'macd', 'macd_signal', 'macd_histogram', 'macd_crossover',
            # RSI
            'rsi', 'rsi_7', 'rsi_21', 'rsi_oversold', 'rsi_overbought',
            # Stochastic
            'stoch_k', 'stoch_d', 'stoch_crossover',
            # Bollinger Bands
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_bandwidth', 'bb_percent',
            # Momentum
            'return_1d', 'return_3d', 'return_5d', 'return_7d', 'return_10d', 'return_14d', 'return_21d',
            'roc_10', 'roc_20',
            # Volatility
            'volatility', 'volatility_ratio', 'atr', 'atr_percent',
            # Other indicators
            'williams_r', 'cci', 'adx', 'plus_di', 'minus_di', 'adx_trend',
            # Volume
            'obv', 'volume_sma', 'volume_ratio', 'volume_trend', 'vwap', 'price_vs_vwap',
            # Price patterns
            'price_position', 'body_size', 'upper_shadow', 'lower_shadow',
            # Trend
            'trend_sma', 'trend_ema', 'price_vs_sma50', 'price_vs_sma200',
            # Statistical
            'zscore', 'skewness', 'kurtosis',
            # Support/Resistance
            'dist_to_high_20', 'dist_to_low_20'
        ]


# Singleton instance
indicators = TechnicalIndicators()
