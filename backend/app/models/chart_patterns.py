"""
NexusTrader — Chart Pattern Recognizer
=======================================
Detects candlestick and chart patterns directly from OHLCV price data.
No external API needed — pure price analysis.

Candlestick patterns:
  • Doji (indecision)
  • Hammer / Inverted Hammer (bullish reversal at bottom)
  • Shooting Star / Hanging Man (bearish reversal at top)
  • Bullish / Bearish Engulfing
  • Morning Star / Evening Star (3-candle reversal)
  • Three White Soldiers / Three Black Crows
  • Harami (inside bar, indecision / reversal)
  • Dark Cloud Cover / Piercing Pattern

Chart structure patterns:
  • Golden Cross / Death Cross (MA crossovers — high reliability)
  • Price vs VWAP (institutional level)
  • Consecutive higher-highs / lower-lows (trend confirmation)
  • Volume-price confirmation (volume should expand with trend)
  • Bollinger Band squeeze → expansion (volatility breakout signal)

Each pattern returns a score in [-1, +1]:
  +1 = strong bullish signal
  -1 = strong bearish signal
   0 = neutral / no pattern
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


class ChartPatternRecognizer:
    """
    Detects candlestick and chart patterns from OHLCV DataFrames.
    Call score(df) to get a composite signal in [-1, +1].
    """

    # How many candles to look back for pattern context
    LOOKBACK = 5

    def score(self, df: pd.DataFrame) -> Tuple[float, Dict[str, float]]:
        """
        Compute composite pattern score from all detectors.

        Returns:
            (composite_score [-1..+1], detail_dict)
        """
        if df is None or len(df) < 10:
            return 0.0, {}

        # Normalise column names to lowercase
        col_map = {c: c.lower() for c in df.columns}
        df = df.rename(columns=col_map).copy()

        if 'close' not in df.columns:
            return 0.0, {}

        close  = df['close']
        open_  = df.get('open',  close)
        high   = df.get('high',  close)
        low    = df.get('low',   close)
        volume = df.get('volume', pd.Series(np.zeros(len(df)), index=df.index))

        patterns: Dict[str, float] = {}

        # ── Candlestick patterns ──────────────────────────────────────────────
        patterns.update(self._candlestick_patterns(open_, high, low, close))

        # ── Chart structure patterns ──────────────────────────────────────────
        patterns.update(self._chart_structure(close, high, low, volume))

        # ── Composite score: simple weighted average ──────────────────────────
        # Pattern weights — chart structure > candlestick (longer-term reliability)
        weights = {
            # candlestick — short-term
            'engulfing':        0.12,
            'hammer':           0.08,
            'shooting_star':    0.08,
            'morning_star':     0.10,
            'three_soldiers':   0.10,
            'dark_cloud':       0.09,
            'doji':             0.04,
            # chart structure — longer-term
            'ma_cross':         0.15,
            'trend_confirmation':0.10,
            'volume_confirm':   0.08,
            'bb_squeeze':       0.06,
        }

        total_w = 0.0
        weighted_sum = 0.0
        for name, score in patterns.items():
            w = weights.get(name, 0.05)
            weighted_sum += score * w
            total_w += w

        composite = weighted_sum / total_w if total_w > 0 else 0.0
        composite = max(-1.0, min(1.0, composite))

        return round(composite, 4), patterns

    # ── Candlestick Patterns ──────────────────────────────────────────────────

    def _candlestick_patterns(self, open_, high, low, close) -> Dict[str, float]:
        """Detect last-candle and multi-candle candlestick formations."""
        results: Dict[str, float] = {}

        n = len(close)
        if n < 3:
            return results

        # Latest candle values
        o, h, l, c   = float(open_.iloc[-1]), float(high.iloc[-1]), float(low.iloc[-1]), float(close.iloc[-1])
        o2, h2, l2, c2 = float(open_.iloc[-2]), float(high.iloc[-2]), float(low.iloc[-2]), float(close.iloc[-2])
        body          = abs(c - o)
        body2         = abs(c2 - o2)
        candle_range  = h - l
        avg_body      = close.diff().abs().rolling(10).mean().iloc[-1] if n >= 10 else body

        # ── Doji (body < 10% of range → indecision) ──
        if candle_range > 0 and body / candle_range < 0.10:
            # Doji at top of trend = bearish, at bottom = bullish
            recent_trend = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] if n >= 6 else 0
            results['doji'] = -0.3 if recent_trend > 0.02 else (0.3 if recent_trend < -0.02 else 0.0)
        else:
            results['doji'] = 0.0

        # ── Hammer (small body, long lower shadow, at bottom of trend) ──
        lower_shadow = min(o, c) - l
        upper_shadow = h - max(o, c)
        if (body < avg_body * 0.5
                and lower_shadow >= body * 2
                and upper_shadow < body * 0.5):
            # Hammer = bullish reversal if we were in downtrend
            recent_low = close.rolling(5).min().iloc[-1] if n >= 5 else c
            is_at_bottom = c <= recent_low * 1.03
            results['hammer'] = 0.70 if is_at_bottom else 0.30
        elif (body < avg_body * 0.5
              and upper_shadow >= body * 2
              and lower_shadow < body * 0.5):
            # Inverted hammer at bottom = bullish; shooting star at top = bearish
            recent_high = close.rolling(5).max().iloc[-1] if n >= 5 else c
            at_top = c >= recent_high * 0.97
            results['hammer'] = -0.60 if at_top else 0.40
        else:
            results['hammer'] = 0.0

        # ── Shooting Star (bearish reversal at top) ──
        if (upper_shadow >= body * 2
                and lower_shadow < body * 0.3
                and c < o):    # bearish candle preferred
            recent_high = close.rolling(5).max().iloc[-1] if n >= 5 else c
            at_top = c >= recent_high * 0.95
            results['shooting_star'] = -0.65 if at_top else -0.25
        else:
            results['shooting_star'] = 0.0

        # ── Engulfing ──
        # Bullish: prev red candle, current green engulfs previous body
        if c2 < o2 and c > o and c > o2 and o < c2:
            results['engulfing'] = 0.75
        # Bearish: prev green candle, current red engulfs previous body
        elif c2 > o2 and c < o and c < o2 and o > c2:
            results['engulfing'] = -0.75
        else:
            results['engulfing'] = 0.0

        # ── Morning / Evening Star (3-candle reversal) ──
        if n >= 3:
            o3, c3 = float(open_.iloc[-3]), float(close.iloc[-3])
            body3 = abs(c3 - o3)
            # Morning Star: big red → small indecision → big green
            if (c3 < o3 and body3 > avg_body * 0.8
                    and body2 < avg_body * 0.4
                    and c > o and abs(c - o) > avg_body * 0.7
                    and c > (o3 + c3) / 2):
                results['morning_star'] = 0.85
            # Evening Star: big green → small indecision → big red
            elif (c3 > o3 and body3 > avg_body * 0.8
                    and body2 < avg_body * 0.4
                    and c < o and abs(c - o) > avg_body * 0.7
                    and c < (o3 + c3) / 2):
                results['morning_star'] = -0.85
            else:
                results['morning_star'] = 0.0
        else:
            results['morning_star'] = 0.0

        # ── Three White Soldiers / Three Black Crows ──
        if n >= 3:
            c1f, c2f, c3f = float(close.iloc[-3]), float(close.iloc[-2]), float(close.iloc[-1])
            o1f, o2f, o3f = float(open_.iloc[-3]), float(open_.iloc[-2]), float(open_.iloc[-1])
            # Three white soldiers: three consecutive green candles, each closing higher
            if c3f > c2f > c1f and o1f < c1f and o2f < c2f and o3f < c3f:
                results['three_soldiers'] = 0.80
            # Three black crows: three consecutive red candles, each closing lower
            elif c3f < c2f < c1f and o1f > c1f and o2f > c2f and o3f > c3f:
                results['three_soldiers'] = -0.80
            else:
                results['three_soldiers'] = 0.0
        else:
            results['three_soldiers'] = 0.0

        # ── Dark Cloud Cover / Piercing Pattern ──
        if n >= 2:
            # Dark Cloud Cover: green candle then red candle closing below midpoint
            midpoint = (o2 + c2) / 2
            if c2 > o2 and c < o and c < midpoint and o > c2:
                results['dark_cloud'] = -0.65
            # Piercing: red candle then green candle closing above midpoint
            elif c2 < o2 and c > o and c > midpoint and o < c2:
                results['dark_cloud'] = 0.65
            else:
                results['dark_cloud'] = 0.0
        else:
            results['dark_cloud'] = 0.0

        return results

    # ── Chart Structure Patterns ──────────────────────────────────────────────

    def _chart_structure(self, close, high, low, volume) -> Dict[str, float]:
        """Detect trend-level patterns from price and volume structure."""
        results: Dict[str, float] = {}
        n = len(close)

        # ── MA Cross (Golden / Death Cross) ──
        if n >= 50:
            sma20 = close.rolling(20).mean()
            sma50 = close.rolling(50).mean()
            if sma20.iloc[-1] > sma50.iloc[-1] and sma20.iloc[-3] <= sma50.iloc[-3]:
                results['ma_cross'] = 0.90   # Recent Golden Cross
            elif sma20.iloc[-1] < sma50.iloc[-1] and sma20.iloc[-3] >= sma50.iloc[-3]:
                results['ma_cross'] = -0.90  # Recent Death Cross
            elif sma20.iloc[-1] > sma50.iloc[-1]:
                results['ma_cross'] = 0.40   # Still above: bullish structure
            else:
                results['ma_cross'] = -0.40  # Still below: bearish structure
        elif n >= 20:
            sma10 = close.rolling(10).mean()
            sma20 = close.rolling(20).mean()
            if sma10.iloc[-1] > sma20.iloc[-1]:
                results['ma_cross'] = 0.30
            else:
                results['ma_cross'] = -0.30
        else:
            results['ma_cross'] = 0.0

        # ── Trend Confirmation (higher-highs/higher-lows or lower-highs/lower-lows) ──
        if n >= 10:
            highs5 = [float(high.iloc[-i]) for i in range(1, 6)]
            lows5  = [float(low.iloc[-i])  for i in range(1, 6)]
            # Consecutive higher highs
            hh = sum(1 for i in range(len(highs5) - 1) if highs5[i] > highs5[i+1])
            # Consecutive lower lows
            ll = sum(1 for i in range(len(lows5) - 1)  if lows5[i]  < lows5[i+1])
            # Consecutive lower highs
            lh = sum(1 for i in range(len(highs5) - 1) if highs5[i] < highs5[i+1])
            # Consecutive higher lows
            hl = sum(1 for i in range(len(lows5) - 1)  if lows5[i]  > lows5[i+1])

            if hh >= 3 and hl >= 2:    results['trend_confirmation'] = 0.70   # Uptrend confirmed
            elif lh >= 3 and ll >= 2:  results['trend_confirmation'] = -0.70  # Downtrend confirmed
            elif hh >= 2:              results['trend_confirmation'] = 0.30
            elif lh >= 2:              results['trend_confirmation'] = -0.30
            else:                      results['trend_confirmation'] = 0.0
        else:
            results['trend_confirmation'] = 0.0

        # ── Volume–Price Confirmation ──
        if n >= 5:
            vol_np  = volume.values[-5:]
            close_np = close.values[-5:]
            avg_vol = np.mean(vol_np[:-1]) if len(vol_np) > 1 else vol_np[-1]
            last_vol = float(vol_np[-1])
            price_up = float(close_np[-1]) > float(close_np[-2])

            if avg_vol > 0:
                vol_ratio = last_vol / avg_vol
                if vol_ratio > 1.4 and price_up:
                    results['volume_confirm'] = 0.60    # High-volume breakout
                elif vol_ratio > 1.4 and not price_up:
                    results['volume_confirm'] = -0.60   # High-volume breakdown
                elif vol_ratio < 0.6 and price_up:
                    results['volume_confirm'] = 0.10    # Low-vol rise (weak)
                elif vol_ratio < 0.6 and not price_up:
                    results['volume_confirm'] = -0.10   # Low-vol fall (weak)
                else:
                    results['volume_confirm'] = 0.0
            else:
                results['volume_confirm'] = 0.0
        else:
            results['volume_confirm'] = 0.0

        # ── Bollinger Band Squeeze → Expansion (volatility breakout) ──
        if n >= 25:
            sma20  = close.rolling(20).mean()
            std20  = close.rolling(20).std()
            bb_width = (2 * std20 / sma20)   # Normalised band width

            # Compare current width to 10-period average width
            avg_width = bb_width.rolling(10).mean().iloc[-1]
            curr_width = bb_width.iloc[-1]

            if pd.notna(avg_width) and avg_width > 0:
                squeeze_ratio = curr_width / avg_width
                current_price = float(close.iloc[-1])
                upper_band = float(sma20.iloc[-1] + 2 * std20.iloc[-1])
                lower_band = float(sma20.iloc[-1] - 2 * std20.iloc[-1])

                # Band was compressed (squeeze) and is now expanding
                prev_width = bb_width.iloc[-2] if len(bb_width) >= 2 else curr_width
                expanding = curr_width > float(prev_width) * 1.1

                if expanding:
                    if current_price > float(sma20.iloc[-1]):
                        results['bb_squeeze'] = 0.55   # Breakout upward
                    else:
                        results['bb_squeeze'] = -0.55  # Breakdown downward
                else:
                    results['bb_squeeze'] = 0.0
            else:
                results['bb_squeeze'] = 0.0
        else:
            results['bb_squeeze'] = 0.0

        return results

    def get_human_summary(self, patterns: Dict[str, float]) -> List[str]:
        """
        Convert pattern scores to plain-English bullet points for the frontend.
        Returns up to 4 most significant signals.
        """
        LABELS = {
            'engulfing':          ('Bullish Engulfing candle', 'Bearish Engulfing candle'),
            'hammer':             ('Hammer / reversal candle', 'Shooting Star candle'),
            'shooting_star':      ('Bullish reversal candle', 'Shooting Star bearish'),
            'morning_star':       ('Morning Star reversal (bullish)', 'Evening Star reversal (bearish)'),
            'three_soldiers':     ('Three White Soldiers', 'Three Black Crows'),
            'dark_cloud':         ('Piercing bullish reversal', 'Dark Cloud Cover (bearish)'),
            'doji':               ('Doji at support (neutral)', 'Doji at resistance (caution)'),
            'ma_cross':           ('Golden Cross / bullish MA', 'Death Cross / bearish MA'),
            'trend_confirmation': ('Higher-highs trend confirmed', 'Lower-lows downtrend confirmed'),
            'volume_confirm':     ('High-volume breakout', 'High-volume breakdown'),
            'bb_squeeze':         ('Bollinger squeeze breakout ↑', 'Bollinger squeeze breakdown ↓'),
        }

        signals = sorted(
            [(name, score) for name, score in patterns.items() if abs(score) >= 0.25],
            key=lambda x: abs(x[1]),
            reverse=True
        )[:4]

        result = []
        for name, score in signals:
            if name in LABELS:
                label = LABELS[name][0] if score > 0 else LABELS[name][1]
                emoji = '📈' if score > 0 else '📉'
                result.append(f"{emoji} {label}")
        return result


# Module-level singleton
chart_pattern_recognizer = ChartPatternRecognizer()
