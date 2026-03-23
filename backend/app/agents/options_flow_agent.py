"""
NexusTrader — Options Flow Scanner Agent
==========================================
Analyses options market microstructure to detect smart-money positioning.

Source: yfinance option_chain (free, no API key, US stocks only)

Signals computed:
  1. Put/Call OI Ratio    — high ratio (>1.3) = bearish hedging; low (<0.7) = bullish
  2. Gamma Exposure (GEX) — net dealer gamma; negative GEX = volatility accelerator
  3. Max Pain             — OI-weighted strike where total option premium is minimised;
                            price gravitates toward max pain near expiry
  4. IV Skew             — (put ATM IV - call ATM IV); positive = fear premium / bearish
  5. Unusual OI          — strikes where OI > mean + 2σ (potential price targets)

Graceful degradation:
  - Returns neutral score (0) for crypto or if yfinance options unavailable
  - Never crashes the parent scanner

Score range: −100 to +100 (negative = bearish, positive = bullish)
Confidence: 50−80% (options data is powerful but US stock only)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Helper math
# ─────────────────────────────────────────────────────────────────────────────

def _black_scholes_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Approximate BSM gamma for a single option (simplified, T in years)."""
    try:
        from math import log, sqrt, exp, pi
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0.0
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        nd1 = exp(-0.5 * d1 ** 2) / sqrt(2 * pi)  # standard normal pdf
        return nd1 / (S * sigma * sqrt(T))
    except Exception:
        return 0.0


def _max_pain(chain: pd.DataFrame, current_price: float) -> float:
    """
    Compute the max pain strike.
    For each strike, compute total dollar value of all options expiring worthless
    assuming that strike is the settlement price. Return strike that minimises total.
    """
    try:
        strikes = sorted(chain["strike"].dropna().unique())
        if len(strikes) < 5:
            return current_price

        min_pain = float("inf")
        max_pain_strike = current_price

        for settlement in strikes:
            # Call pain: call writers profit from calls expiring below settlement
            call_pain = float(
                chain[chain["strike"] > settlement]["callOpenInterest"].fillna(0).sum()
                * (chain[chain["strike"] > settlement]["strike"] - settlement).clip(lower=0).sum()
            )
            # Put pain
            put_pain = float(
                chain[chain["strike"] < settlement]["putOpenInterest"].fillna(0).sum()
                * (settlement - chain[chain["strike"] < settlement]["strike"]).clip(lower=0).sum()
            )
            total_pain = call_pain + put_pain
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = settlement

        return float(max_pain_strike)
    except Exception:
        return current_price


# ─────────────────────────────────────────────────────────────────────────────
# OptionsFlowAgent
# ─────────────────────────────────────────────────────────────────────────────

class OptionsFlowAgent:
    """
    8th scanner agent: options market microstructure analysis.
    Conforms to the same interface as all other scanner agents.
    """

    name = "OptionsFlowAgent"

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        """
        Full options flow analysis.
        Returns standardised agent dict:
          {agent, signal, score, confidence, reasoning}
        """
        # Options only available for US equities
        if self._is_crypto(symbol):
            return self._neutral(symbol, "Options data not available for crypto")

        try:
            return self._run(symbol, df)
        except Exception as e:
            return self._neutral(symbol, f"Options fetch error: {str(e)[:80]}")

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _is_crypto(symbol: str) -> bool:
        return "/" in symbol or any(
            tok in symbol.upper()
            for tok in ["BTC", "ETH", "BNB", "XRP", "SOL", "ADA",
                        "USDT", "DOGE", "AVAX", "MATIC", "DOT"]
        )

    def _neutral(self, symbol: str, reason: str) -> Dict:
        return {
            "agent": self.name,
            "signal": "HOLD",
            "score": 0.0,
            "confidence": 50.0,
            "reasoning": [reason],
        }

    def _run(self, symbol: str, df: pd.DataFrame) -> Dict:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        exps = ticker.options
        if not exps:
            return self._neutral(symbol, "No options expiries found")

        # Use the nearest two expiries for most liquid data
        near_exps = exps[:min(2, len(exps))]
        current_price = float(df["close"].iloc[-1]) if "close" in df.columns else float(df["Close"].iloc[-1])

        all_calls: List[pd.DataFrame] = []
        all_puts:  List[pd.DataFrame] = []

        for exp in near_exps:
            try:
                chain = ticker.option_chain(exp)
                calls = chain.calls.copy()
                puts  = chain.puts.copy()
                calls["expiry"] = exp
                puts["expiry"]  = exp
                all_calls.append(calls)
                all_puts.append(puts)
            except Exception:
                continue

        if not all_calls or not all_puts:
            return self._neutral(symbol, "Option chain data unavailable")

        calls_df = pd.concat(all_calls, ignore_index=True)
        puts_df  = pd.concat(all_puts,  ignore_index=True)

        # ── Signal 1: Put/Call OI Ratio ────────────────────────────────────
        call_oi = float(calls_df["openInterest"].fillna(0).sum())
        put_oi  = float(puts_df["openInterest"].fillna(0).sum())
        pc_ratio = put_oi / (call_oi + 1e-6)
        # Contrarian: extreme put buying is bullish (fear capitulation)
        # pc_ratio > 1.5 → very fearful → slight contrarian BUY
        # pc_ratio < 0.5 → complacent → slight contrarian SELL
        if pc_ratio > 1.5:
            pc_score = 15.0   # contrarian bullish
        elif pc_ratio > 1.2:
            pc_score = 5.0
        elif pc_ratio < 0.5:
            pc_score = -15.0  # complacent / bearish divergence
        elif pc_ratio < 0.7:
            pc_score = -5.0
        else:
            pc_score = 0.0

        # ── Signal 2: Gamma Exposure (GEX) ────────────────────────────────
        # GEX = Σ(gamma × OI × 100 × S) for calls − puts
        # Simplified: use strike proximity as gamma proxy (ATM = highest gamma)
        def _gex_row(row: pd.Series, is_call: bool) -> float:
            try:
                K = float(row["strike"])
                oi = float(row.get("openInterest") or 0)
                iv = float(row.get("impliedVolatility") or 0.3)
                T = 30 / 365  # assume 30-day avg
                g = _black_scholes_gamma(current_price, K, T, 0.05, iv)
                sign = 1.0 if is_call else -1.0
                return sign * g * oi * 100 * current_price
            except Exception:
                return 0.0

        call_gex = calls_df.apply(lambda r: _gex_row(r, True), axis=1).sum()
        put_gex  = puts_df.apply(lambda r: _gex_row(r, False), axis=1).sum()
        net_gex  = float(call_gex + put_gex)
        # Positive GEX: dealers long gamma → dampen moves (mean reversion)
        # Negative GEX: dealers short gamma → amplify moves (breakout)
        # For direction signal: positive GEX + uptrend = bullish stabiliser
        close_prices = df["close"].values if "close" in df.columns else df["Close"].values
        recent_return = float(close_prices[-1] / close_prices[-5] - 1) if len(close_prices) >= 5 else 0.0
        if net_gex > 0 and recent_return > 0:
            gex_score = 10.0    # stabilising uptrend
        elif net_gex < 0 and recent_return > 0:
            gex_score = 20.0    # amplified uptrend
        elif net_gex < 0 and recent_return < 0:
            gex_score = -20.0   # amplified downtrend
        elif net_gex > 0 and recent_return < 0:
            gex_score = -10.0   # stabilising downtrend
        else:
            gex_score = 0.0

        # ── Signal 3: Max Pain ────────────────────────────────────────────
        # Build combined OI table
        combined_strikes = []
        for _, row in calls_df.iterrows():
            combined_strikes.append({
                "strike": row.get("strike", 0),
                "callOpenInterest": row.get("openInterest", 0),
                "putOpenInterest": 0,
            })
        for _, row in puts_df.iterrows():
            combined_strikes.append({
                "strike": row.get("strike", 0),
                "callOpenInterest": 0,
                "putOpenInterest": row.get("openInterest", 0),
            })
        combined_df = pd.DataFrame(combined_strikes).groupby("strike").sum().reset_index()
        mp_strike = _max_pain(combined_df, current_price)

        mp_pct = (mp_strike - current_price) / (current_price + 1e-9) * 100
        # Price above max pain → gravitational pull down; below → pull up
        mp_score = float(np.clip(-mp_pct * 5, -20, 20))

        # ── Signal 4: IV Skew ─────────────────────────────────────────────
        # ATM = strikes within 5% of current price
        atm_low  = current_price * 0.95
        atm_high = current_price * 1.05

        atm_calls = calls_df[
            (calls_df["strike"] >= atm_low) & (calls_df["strike"] <= atm_high)
        ]["impliedVolatility"].dropna()
        atm_puts = puts_df[
            (puts_df["strike"] >= atm_low) & (puts_df["strike"] <= atm_high)
        ]["impliedVolatility"].dropna()

        avg_call_iv = float(atm_calls.mean()) if len(atm_calls) > 0 else 0.3
        avg_put_iv  = float(atm_puts.mean())  if len(atm_puts)  > 0 else 0.3
        iv_skew = avg_put_iv - avg_call_iv  # positive = bearish fear premium

        # Extreme positive skew (>0.10) = high fear → contrarian bullish
        if iv_skew > 0.15:
            skew_score = 10.0
        elif iv_skew > 0.08:
            skew_score = 5.0
        elif iv_skew < -0.05:
            skew_score = -10.0
        else:
            skew_score = 0.0

        # ── Signal 5: Unusual OI ─────────────────────────────────────────
        combined_oi = pd.concat([
            calls_df[["strike", "openInterest"]],
            puts_df[["strike", "openInterest"]]
        ]).groupby("strike")["openInterest"].sum()

        if len(combined_oi) > 5:
            mean_oi = float(combined_oi.mean())
            std_oi  = float(combined_oi.std())
            unusual = combined_oi[combined_oi > mean_oi + 2 * std_oi]

            # If unusual OI clusters above current price → call wall (resistance)
            above = unusual.index[unusual.index > current_price * 1.02]
            below = unusual.index[unusual.index < current_price * 0.98]
            unusual_score = 0.0
            if len(above) > 0 and len(below) == 0:
                unusual_score = -10.0  # strong call wall above = resistance
            elif len(below) > 0 and len(above) == 0:
                unusual_score = 10.0   # put wall below = strong support
        else:
            unusual_score = 0.0

        # ── Composite score ───────────────────────────────────────────────
        total_score = float(np.clip(
            pc_score * 0.20
            + gex_score * 0.30
            + mp_score * 0.20
            + skew_score * 0.20
            + unusual_score * 0.10,
            -100, 100
        ))
        signal = "BUY" if total_score > 10 else ("SELL" if total_score < -10 else "HOLD")

        reasoning = [
            f"P/C OI ratio: {pc_ratio:.2f} ({'bearish hedge' if pc_ratio > 1.2 else 'bullish' if pc_ratio < 0.7 else 'neutral'})",
            f"Net GEX: {net_gex:+.0f} ({'positive' if net_gex > 0 else 'negative'}; {'momentum dampener' if net_gex > 0 else 'momentum amplifier'})",
            f"Max Pain: ${mp_strike:.2f} (price {mp_pct:+.1f}% away → pull {'down' if mp_pct > 0 else 'up'})",
            f"IV Skew (put-call): {iv_skew:+.3f} ({'fear premium' if iv_skew > 0.05 else 'normal'})",
            f"Unusual OI clusters: {len(unusual) if 'unusual' in dir() else 0} strikes",
        ]

        # Confidence: 55-78% — options work well but only for liquid US names
        confidence = min(78.0, 55.0 + abs(total_score) * 0.3)

        return {
            "agent": self.name,
            "signal": signal,
            "score": round(total_score, 1),
            "confidence": round(confidence, 1),
            "reasoning": reasoning,
            "details": {
                "pc_ratio": round(pc_ratio, 3),
                "net_gex": round(net_gex, 0),
                "max_pain": round(mp_strike, 2),
                "iv_skew": round(iv_skew, 4),
                "avg_call_iv": round(avg_call_iv, 4),
                "avg_put_iv": round(avg_put_iv, 4),
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────
options_flow_agent = OptionsFlowAgent()
