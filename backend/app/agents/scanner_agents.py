"""
NexusTrader - Scanner Sub-Agents
Each agent specialises in one signal category and returns a standardised dict:
    {
        "agent":      str,           # agent name
        "signal":     "BUY"|"SELL"|"HOLD"|"WATCH",
        "score":      float,         # -100 to +100, >0 bullish
        "confidence": float,         # 0-100%
        "reasoning":  List[str],     # bullet-point explanations
    }
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _signal(score: float) -> str:
    if score >= 30:
        return "BUY"
    if score <= -30:
        return "SELL"
    if abs(score) >= 15:
        return "WATCH"
    return "HOLD"


def _safe(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].astype(float) if col in df.columns else pd.Series(dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1 – TechnicalAgent
# Analyses RSI, MACD, Bollinger Bands, trend channels
# ─────────────────────────────────────────────────────────────────────────────

class TechnicalAgent:
    name = "TechnicalAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        reasons = []
        points = 0.0

        if df is None or len(df) < 30:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["Insufficient data"]}

        close = _safe(df, "close") if "close" in df.columns else _safe(df, "Close")
        if close.empty:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["No close price data"]}

        # ── RSI ──────────────────────────────────────────────────────────────
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / (loss + 1e-9)))
        rsi_val = float(rsi.iloc[-1]) if not rsi.empty else 50
        if rsi_val < 30:
            points += 35
            reasons.append(f"RSI {rsi_val:.1f} — oversold, reversal likely")
        elif rsi_val < 45:
            points += 15
            reasons.append(f"RSI {rsi_val:.1f} — approaching oversold zone")
        elif rsi_val > 70:
            points -= 35
            reasons.append(f"RSI {rsi_val:.1f} — overbought, caution")
        elif rsi_val > 55:
            points += 10
            reasons.append(f"RSI {rsi_val:.1f} — bullish momentum building")

        # ── MACD ─────────────────────────────────────────────────────────────
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        if not hist.empty and len(hist) >= 2:
            if float(hist.iloc[-1]) > 0 and float(hist.iloc[-2]) <= 0:
                points += 30
                reasons.append("MACD bullish crossover confirmed")
            elif float(hist.iloc[-1]) < 0 and float(hist.iloc[-2]) >= 0:
                points -= 30
                reasons.append("MACD bearish crossover confirmed")
            elif float(hist.iloc[-1]) > float(hist.iloc[-2]) > 0:
                points += 15
                reasons.append("MACD histogram expanding bullishly")
            elif float(hist.iloc[-1]) < float(hist.iloc[-2]) < 0:
                points -= 15
                reasons.append("MACD histogram expanding bearishly")

        # ── Bollinger Bands ───────────────────────────────────────────────────
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_lower = bb_mid - 2 * bb_std
        bb_upper = bb_mid + 2 * bb_std
        last_close = float(close.iloc[-1])
        bl = float(bb_lower.iloc[-1]) if not bb_lower.empty else last_close
        bu = float(bb_upper.iloc[-1]) if not bb_upper.empty else last_close
        bm = float(bb_mid.iloc[-1]) if not bb_mid.empty else last_close
        bb_pos = (last_close - bl) / (bu - bl + 1e-9)
        if bb_pos < 0.15:
            points += 25
            reasons.append(f"Price near lower BB ({bb_pos:.0%} position) — oversold")
        elif bb_pos > 0.85:
            points -= 20
            reasons.append(f"Price near upper BB ({bb_pos:.0%} position) — overbought")
        elif bb_pos > 0.5:
            points += 8
            reasons.append(f"Price above BB midline — mild bullish bias")

        # ── SMA trend ─────────────────────────────────────────────────────────
        if len(close) >= 50:
            sma20 = float(close.rolling(20).mean().iloc[-1])
            sma50 = float(close.rolling(50).mean().iloc[-1])
            if last_close > sma20 > sma50:
                points += 20
                reasons.append("Price > SMA20 > SMA50 — confirmed uptrend")
            elif last_close < sma20 < sma50:
                points -= 20
                reasons.append("Price < SMA20 < SMA50 — confirmed downtrend")

        score = float(np.clip(points, -100, 100))
        confidence = min(95.0, 60.0 + abs(score) * 0.35)
        return {
            "agent": self.name,
            "signal": _signal(score),
            "score": round(score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasons or ["No strong technical signals"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2 – MomentumAgent
# Rate-of-change, price acceleration, trend strength
# ─────────────────────────────────────────────────────────────────────────────

class MomentumAgent:
    name = "MomentumAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        reasons = []
        points = 0.0

        if df is None or len(df) < 20:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["Insufficient data"]}

        close = _safe(df, "close") if "close" in df.columns else _safe(df, "Close")
        if close.empty:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["No close price data"]}

        # ROC (Rate of Change)
        for period, weight in [(5, 1.0), (10, 0.8), (21, 0.6)]:
            if len(close) > period:
                roc = float((close.iloc[-1] - close.iloc[-period]) / (close.iloc[-period] + 1e-9) * 100)
                if roc > 5:
                    points += 20 * weight
                    reasons.append(f"ROC({period}d): +{roc:.1f}% — strong upward momentum")
                elif roc < -5:
                    points -= 20 * weight
                    reasons.append(f"ROC({period}d): {roc:.1f}% — strong selling pressure")

        # Price acceleration (2nd derivative)
        if len(close) >= 5:
            accel = close.diff().diff()
            recent_accel = float(accel.iloc[-3:].mean())
            if recent_accel > 0:
                points += 15
                reasons.append("Price acceleration positive — momentum increasing")
            elif recent_accel < 0:
                points -= 10
                reasons.append("Price acceleration negative — momentum slowing")

        # Stochastic
        if len(close) >= 14:
            high = _safe(df, "high") if "high" in df.columns else _safe(df, "High")
            low = _safe(df, "low") if "low" in df.columns else _safe(df, "Low")
            if high.empty:
                high = close
            if low.empty:
                low = close
            low14 = low.rolling(14).min()
            high14 = high.rolling(14).max()
            stoch_k = 100 * (close - low14) / (high14 - low14 + 1e-9)
            stoch_d = stoch_k.rolling(3).mean()
            k_val = float(stoch_k.iloc[-1])
            d_val = float(stoch_d.iloc[-1]) if not stoch_d.empty else k_val
            if k_val < 20 and k_val > d_val:
                points += 25
                reasons.append(f"Stochastic %K={k_val:.0f} bullish crossover in oversold zone")
            elif k_val > 80 and k_val < d_val:
                points -= 25
                reasons.append(f"Stochastic %K={k_val:.0f} bearish crossover in overbought zone")

        # Williams %R
        if len(close) >= 14:
            high14_v = high.rolling(14).max() if not high.empty else close.rolling(14).max()
            low14_v = low.rolling(14).min() if not low.empty else close.rolling(14).min()
            wr = -100 * (high14_v - close) / (high14_v - low14_v + 1e-9)
            wr_val = float(wr.iloc[-1]) if not wr.empty else -50
            if wr_val > -20:
                points -= 15
                reasons.append(f"Williams %R={wr_val:.0f} — overbought")
            elif wr_val < -80:
                points += 15
                reasons.append(f"Williams %R={wr_val:.0f} — oversold")

        score = float(np.clip(points, -100, 100))
        confidence = min(95.0, 55.0 + abs(score) * 0.40)
        return {
            "agent": self.name,
            "signal": _signal(score),
            "score": round(score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasons or ["Momentum signals neutral"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 3 – VolumeAgent
# OBV, volume spikes, accumulation/distribution
# ─────────────────────────────────────────────────────────────────────────────

class VolumeAgent:
    name = "VolumeAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        reasons = []
        points = 0.0

        if df is None or len(df) < 20:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["Insufficient data"]}

        close = _safe(df, "close") if "close" in df.columns else _safe(df, "Close")
        volume = _safe(df, "volume") if "volume" in df.columns else _safe(df, "Volume")

        if close.empty or volume.empty or volume.sum() == 0:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["No volume data available"]}

        # Volume spike detection
        vol_avg20 = float(volume.rolling(20).mean().iloc[-1])
        vol_last = float(volume.iloc[-1])
        if vol_avg20 > 0:
            vol_ratio = vol_last / vol_avg20
            price_dir = 1 if float(close.iloc[-1]) > float(close.iloc[-2]) else -1
            if vol_ratio > 2.0:
                points += 30 * price_dir
                reasons.append(f"Volume spike {vol_ratio:.1f}x average — strong {'buying' if price_dir>0 else 'selling'} pressure")
            elif vol_ratio > 1.5:
                points += 15 * price_dir
                reasons.append(f"Above-average volume {vol_ratio:.1f}x — confirms {'upward' if price_dir>0 else 'downward'} move")
            elif vol_ratio < 0.5:
                reasons.append("Very low volume — move lacks conviction")

        # OBV trend
        obv_sign = np.sign(close.diff().fillna(0))
        obv = (obv_sign * volume).cumsum()
        obv_sma = obv.rolling(20).mean()
        if not obv.empty and not obv_sma.empty:
            obv_val = float(obv.iloc[-1])
            obv_avg = float(obv_sma.iloc[-1])
            if obv_val > obv_avg:
                points += 20
                reasons.append("OBV above SMA20 — accumulation phase")
            else:
                points -= 15
                reasons.append("OBV below SMA20 — distribution phase")

        # Chaikin Money Flow (CMF)
        if "high" in df.columns and "low" in df.columns:
            high = _safe(df, "high")
            low = _safe(df, "low")
            clv = ((close - low) - (high - close)) / (high - low + 1e-9)
            cmf = (clv * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-9)
            cmf_val = float(cmf.iloc[-1]) if not cmf.empty else 0
            if cmf_val > 0.1:
                points += 20
                reasons.append(f"CMF={cmf_val:.2f} — buying pressure dominating")
            elif cmf_val < -0.1:
                points -= 20
                reasons.append(f"CMF={cmf_val:.2f} — selling pressure dominating")

        score = float(np.clip(points, -100, 100))
        confidence = min(92.0, 50.0 + abs(score) * 0.42)
        return {
            "agent": self.name,
            "signal": _signal(score),
            "score": round(score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasons or ["Volume signals inconclusive"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 4 – BreakoutAgent
# 52-week high/low proximity, consolidation breakouts
# ─────────────────────────────────────────────────────────────────────────────

class BreakoutAgent:
    name = "BreakoutAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        reasons = []
        points = 0.0

        if df is None or len(df) < 50:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["Need 50+ days for breakout analysis"]}

        close = _safe(df, "close") if "close" in df.columns else _safe(df, "Close")
        if close.empty:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": ["No price data"]}

        last = float(close.iloc[-1])

        # 52-week range
        year_high = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
        year_low = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())
        pct_of_range = (last - year_low) / (year_high - year_low + 1e-9)

        if last >= year_high * 0.98:
            points += 40
            reasons.append(f"Near 52-week high (${year_high:.2f}) — breakout territory")
        elif last <= year_low * 1.02:
            points -= 30
            reasons.append(f"Near 52-week low (${year_low:.2f}) — high risk zone")
        elif pct_of_range > 0.75:
            points += 20
            reasons.append(f"In upper 25% of 52-week range ({pct_of_range:.0%}) — bullish positioning")

        # Volatility squeeze (BB width < average)
        bb_std = close.rolling(20).std()
        bb_mid = close.rolling(20).mean()
        bb_width = 2 * bb_std / (bb_mid + 1e-9)
        if not bb_width.empty and len(bb_width.dropna()) >= 50:
            current_width = float(bb_width.iloc[-1])
            avg_width = float(bb_width.rolling(50).mean().iloc[-1])
            if current_width < avg_width * 0.7:
                points += 25
                reasons.append("Bollinger Band squeeze — high-volatility breakout imminent")

        # Support/resistance proximity
        recent_high = float(close.tail(20).max())
        if last > recent_high * 0.995:
            points += 30
            reasons.append(f"Breaking through 20-day resistance at ${recent_high:.2f}")

        score = float(np.clip(points, -100, 100))
        confidence = min(93.0, 55.0 + abs(score) * 0.38)
        return {
            "agent": self.name,
            "signal": _signal(score),
            "score": round(score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasons or ["No breakout conditions detected"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 5 – SentimentAgent
# News-based sentiment via web search + yfinance news
# ─────────────────────────────────────────────────────────────────────────────

class SentimentAgent:
    name = "SentimentAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        reasons = []
        points = 0.0

        try:
            from .web_search import web_searcher
            news_data = web_searcher.search_symbol_news(symbol, max_sources=4)
            headlines = news_data.get("headlines", [])
            sentiment_score = news_data.get("sentiment_score", 0.0)
            total = news_data.get("total_articles", 0)
            sources = news_data.get("sources_searched", 0)

            if total == 0:
                return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                        "confidence": 40.0, "reasoning": ["No news found"]}

            # Aggregate sentiment
            pos_count = sum(1 for h in headlines if h.get("sentiment", 0) > 0.1)
            neg_count = sum(1 for h in headlines if h.get("sentiment", 0) < -0.1)

            if sentiment_score > 0.2:
                points = min(60, sentiment_score * 200)
                reasons.append(f"Strongly positive news sentiment ({sentiment_score:+.2f}) from {sources} sources")
                if pos_count > 3:
                    reasons.append(f"{pos_count} bullish headlines detected")
            elif sentiment_score < -0.2:
                points = max(-60, sentiment_score * 200)
                reasons.append(f"Strongly negative news sentiment ({sentiment_score:+.2f}) from {sources} sources")
                if neg_count > 3:
                    reasons.append(f"{neg_count} bearish headlines detected")
            elif sentiment_score > 0.05:
                points = 20
                reasons.append(f"Mildly positive news sentiment ({sentiment_score:+.2f})")
            else:
                reasons.append(f"Neutral news environment ({total} articles scanned)")

            # Finviz stats boost
            stats = news_data.get("finviz_stats", {})
            if "Insider Trans" in stats:
                it = stats["Insider Trans"].replace("%", "")
                try:
                    it_pct = float(it)
                    if it_pct > 5:
                        points += 15
                        reasons.append(f"Insider buying detected (+{it_pct:.0f}%)")
                    elif it_pct < -10:
                        points -= 10
                        reasons.append(f"Insider selling ({it_pct:.0f}%)")
                except ValueError:
                    pass

        except Exception as e:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 30.0, "reasoning": [f"Sentiment analysis unavailable: {str(e)[:60]}"]}

        score = float(np.clip(points, -100, 100))
        confidence = min(88.0, 45.0 + abs(score) * 0.43)
        return {
            "agent": self.name,
            "signal": _signal(score),
            "score": round(score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasons or ["Neutral sentiment"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 6 – FundamentalAgent
# P/E, revenue growth, analyst ratings via yfinance.info
# ─────────────────────────────────────────────────────────────────────────────

class FundamentalAgent:
    name = "FundamentalAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        reasons = []
        points = 0.0

        if "/" in symbol:  # Crypto — skip fundamentals
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 40.0, "reasoning": ["Fundamentals N/A for crypto"]}

        try:
            import yfinance as yf
            info = yf.Ticker(symbol).info

            # P/E ratio
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe:
                if pe < 15:
                    points += 20
                    reasons.append(f"P/E={pe:.1f} — undervalued vs market average (~22)")
                elif pe < 25:
                    points += 5
                    reasons.append(f"P/E={pe:.1f} — fairly valued")
                elif pe > 50:
                    points -= 15
                    reasons.append(f"P/E={pe:.1f} — premium valuation, high expectations")

            # Revenue growth
            rev_growth = info.get("revenueGrowth")
            if rev_growth:
                rev_pct = rev_growth * 100
                if rev_pct > 20:
                    points += 25
                    reasons.append(f"Revenue growing {rev_pct:.0f}% YoY — strong business momentum")
                elif rev_pct > 5:
                    points += 10
                    reasons.append(f"Revenue growing {rev_pct:.0f}% YoY")
                elif rev_pct < 0:
                    points -= 15
                    reasons.append(f"Revenue declining {rev_pct:.0f}% YoY — fundamental weakness")

            # Analyst recommendation
            rec = info.get("recommendationMean")  # 1=Strong Buy, 5=Strong Sell
            if rec:
                if rec <= 1.5:
                    points += 30
                    reasons.append(f"Analyst consensus: Strong Buy (mean={rec:.1f})")
                elif rec <= 2.5:
                    points += 15
                    reasons.append(f"Analyst consensus: Buy (mean={rec:.1f})")
                elif rec >= 4:
                    points -= 25
                    reasons.append(f"Analyst consensus: Sell (mean={rec:.1f})")

            # Profit margin
            pm = info.get("profitMargins")
            if pm and pm > 0.2:
                points += 10
                reasons.append(f"Profit margin {pm*100:.0f}% — high-quality business")
            elif pm and pm < 0:
                points -= 10
                reasons.append(f"Negative profit margins — unprofitable")

            # Short interest
            short_float = info.get("shortPercentOfFloat")
            if short_float and short_float > 0.25:
                points -= 10
                reasons.append(f"High short interest ({short_float*100:.0f}%) — elevated bearish bets")

        except Exception as e:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 35.0, "reasoning": [f"Fundamental data unavailable: {str(e)[:50]}"]}

        score = float(np.clip(points, -100, 100))
        confidence = min(90.0, 50.0 + abs(score) * 0.40)
        return {
            "agent": self.name,
            "signal": _signal(score),
            "score": round(score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasons or ["No notable fundamental signals"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 7 – MacroAgent
# VIX, yield curve, DXY, market breadth context
# ─────────────────────────────────────────────────────────────────────────────

class MacroAgent:
    name = "MacroAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        reasons = []
        points = 0.0

        try:
            import yfinance as yf

            # VIX — fear index
            vix = yf.Ticker("^VIX").fast_info.last_price
            if vix:
                vix = float(vix)
                if vix < 15:
                    points += 20
                    reasons.append(f"VIX={vix:.1f} — low fear, risk-on environment")
                elif vix < 20:
                    points += 10
                    reasons.append(f"VIX={vix:.1f} — calm market conditions")
                elif vix > 30:
                    points -= 25
                    reasons.append(f"VIX={vix:.1f} — elevated fear, defensive bias")
                elif vix > 25:
                    points -= 10
                    reasons.append(f"VIX={vix:.1f} — rising volatility, caution warranted")

            # Yield curve (10Y - 2Y)
            tnx = yf.Ticker("^TNX").fast_info.last_price
            irx = yf.Ticker("^IRX").fast_info.last_price
            if tnx and irx:
                spread = float(tnx) - float(irx)
                if spread > 0.5:
                    points += 15
                    reasons.append(f"Yield curve positive (+{spread:.2f}%) — growth expectations healthy")
                elif spread < -0.3:
                    points -= 15
                    reasons.append(f"Yield curve inverted ({spread:.2f}%) — recession signal")

            # SPY trend (market breadth proxy)
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="3mo", interval="1d")
            if not spy_hist.empty:
                spy_close = spy_hist["Close"]
                spy_sma50 = spy_close.rolling(50).mean().iloc[-1]
                spy_last = spy_close.iloc[-1]
                if float(spy_last) > float(spy_sma50):
                    points += 15
                    reasons.append("S&P 500 above 50-day SMA — broad market bullish")
                else:
                    points -= 10
                    reasons.append("S&P 500 below 50-day SMA — broad market weakness")

        except Exception as e:
            return {"agent": self.name, "signal": "HOLD", "score": 0.0,
                    "confidence": 35.0, "reasoning": [f"Macro data unavailable: {str(e)[:50]}"]}

        score = float(np.clip(points, -100, 100))
        confidence = min(88.0, 50.0 + abs(score) * 0.38)
        return {
            "agent": self.name,
            "signal": _signal(score),
            "score": round(score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasons or ["Macro conditions neutral"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Export singletons
# ─────────────────────────────────────────────────────────────────────────────
technical_agent = TechnicalAgent()
momentum_agent = MomentumAgent()
volume_agent = VolumeAgent()
breakout_agent = BreakoutAgent()
sentiment_agent = SentimentAgent()
fundamental_agent = FundamentalAgent()
macro_agent = MacroAgent()

# 8th agent: options flow (gracefully skips crypto)
try:
    from .options_flow_agent import options_flow_agent
    _has_options = True
except Exception:
    options_flow_agent = None  # type: ignore[assignment]
    _has_options = False

ALL_AGENTS = [
    technical_agent,
    momentum_agent,
    volume_agent,
    breakout_agent,
    sentiment_agent,
    fundamental_agent,
    macro_agent,
]

if _has_options and options_flow_agent is not None:
    ALL_AGENTS.append(options_flow_agent)
