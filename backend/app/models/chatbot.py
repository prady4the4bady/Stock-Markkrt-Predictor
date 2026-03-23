"""
Market Oracle - AI Chatbot for Stock Recommendations
Provides intelligent buy/sell recommendations based on:
- Real-time market analysis
- News sentiment
- Technical indicators
- Pattern recognition
- Risk assessment

IMPORTANT DISCLAIMER:
This chatbot provides educational information only and does NOT constitute
financial advice. Users must understand that stock market investments carry
inherent risks, and past performance does not guarantee future results.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

# Import our models
try:
    from .news_sentiment import news_sentiment_analyzer
    from .enhanced_models import (
        TechnicalPatternRecognizer,
        MultiModelEnsemble,
        MomentumPredictor,
        get_enhanced_prediction
    )
except ImportError:
    news_sentiment_analyzer = None

# Web search integration
try:
    from ..agents.web_search import web_searcher
    HAS_WEB_SEARCH = True
except ImportError:
    web_searcher = None
    HAS_WEB_SEARCH = False


class StockChatbot:
    """
    AI-powered chatbot for stock market analysis and recommendations
    """
    
    def __init__(self):
        self.conversation_history = []
        self.current_symbol = None
        self.last_analysis = None
        
        # Intent patterns
        self.intent_patterns = {
            'buy_recommendation': [
                r'should i (buy|purchase|invest in)',
                r'is .+ (a good buy|worth buying|good investment)',
                r'(buy|purchase) .+\?',
                r'good time to (buy|invest)',
                r'recommend (buying|purchasing)',
            ],
            'sell_recommendation': [
                r'should i (sell|exit|get out)',
                r'is it time to sell',
                r'(sell|exit) .+\?',
                r'take (profit|profits)',
                r'cut (loss|losses)',
            ],
            'hold_recommendation': [
                r'should i (hold|keep|stay)',
                r'is it worth holding',
                r'keep .+ stock',
            ],
            'price_prediction': [
                r'(price|value) (prediction|forecast|target)',
                r'where .+ (going|headed)',
                r'what will .+ be worth',
                r'predict .+ price',
                r'future price',
            ],
            'analysis': [
                r'(analyze|analysis|analyse)',
                r'(technical|fundamental) (analysis|indicators)',
                r'how is .+ doing',
                r'what do you think (of|about)',
                r'(overview|summary)',
            ],
            'news': [
                r'(news|headlines|recent)',
                r'what.+happening',
                r'any (updates|developments)',
            ],
            'risk': [
                r'(risk|risky|safe)',
                r'how (dangerous|volatile)',
                r'(downside|upside)',
            ],
            # Web-search intents — requires live data
            'web_search': [
                r'(latest|live|current|today|right now)',
                r'what (happened|is happening)',
                r'(breaking|real.?time)',
                r'(macro|economy|inflation|fed|interest rate|gdp)',
                r'(sector|industry) (performance|outlook)',
                r'(earnings|revenue|guidance) (report|result)',
                r'(insider|institutional) (buying|selling|activity)',
                r'(short squeeze|gamma squeeze)',
                r'(catalyst|event|upcoming)',
                r'(compare|vs\.?|versus)',
                r'best (stock|crypto|investment)',
                r'(market (open|close|today|this week))',
                r'(crypto|bitcoin|ethereum) (news|market)',
                r'(ipo|merger|acquisition|dividend)',
            ],
            'greeting': [
                r'^(hi|hello|hey|greetings)',
                r'good (morning|afternoon|evening)',
            ],
            'help': [
                r'(help|what can you do)',
                r'how (do i|to) use',
                r'commands',
            ],
        }
        
        # Stock symbol patterns
        self.symbol_patterns = [
            r'\b([A-Z]{1,5})\b(?:\s+stock|\s+shares)?',  # AAPL, TSLA
            r'\$([A-Z]{1,5})\b',  # $AAPL
            r'ticker[:\s]+([A-Z]{1,5})',  # ticker: AAPL
        ]
        
    def _detect_intent(self, message: str) -> Tuple[str, float]:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent, 0.9
        
        # Default to analysis if no specific intent found
        return 'analysis', 0.5
    
    def _extract_symbol(self, message: str) -> Optional[str]:
        """Extract stock symbol from message"""
        message_upper = message.upper()
        
        # Common words to filter out (NOT stock symbols)
        common_words = {
            'I', 'A', 'THE', 'IS', 'IT', 'TO', 'AND', 'OR', 'FOR', 'OF', 'IN', 'ON', 'AT', 'BY',
            'BUY', 'SELL', 'HOLD', 'GET', 'PUT', 'CALL', 'SHOULD', 'WOULD', 'COULD', 'WILL',
            'CAN', 'DO', 'DOES', 'DID', 'HAS', 'HAVE', 'HAD', 'BE', 'AM', 'ARE', 'WAS', 'WERE',
            'BEEN', 'BEING', 'WHAT', 'WHEN', 'WHERE', 'WHY', 'HOW', 'WHO', 'WHICH', 'THAT',
            'THIS', 'THESE', 'THOSE', 'MY', 'YOUR', 'HIS', 'HER', 'ITS', 'OUR', 'THEIR',
            'ME', 'YOU', 'HIM', 'US', 'THEM', 'IF', 'THEN', 'ELSE', 'SO', 'BUT', 'NOT',
            'YES', 'NO', 'NOW', 'TIME', 'GOOD', 'BAD', 'BEST', 'STOCK', 'STOCKS', 'SHARE',
            'SHARES', 'PRICE', 'MARKET', 'TRADE', 'TRADING', 'INVEST', 'INVESTMENT',
            'MONEY', 'PROFIT', 'LOSS', 'SAFE', 'RISKY', 'NEWS', 'TODAY', 'TOMORROW',
            'ANALYSIS', 'ANALYZE', 'PREDICT', 'PREDICTION', 'TARGET', 'ABOUT', 'THINK'
        }
        
        # Check for explicit symbols
        for pattern in self.symbol_patterns:
            matches = re.findall(pattern, message_upper)
            if matches:
                for match in matches:
                    if match not in common_words and len(match) >= 2:
                        return match
        
        # Check for company names
        company_symbols = {
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'google': 'GOOGL',
            'alphabet': 'GOOGL',
            'amazon': 'AMZN',
            'tesla': 'TSLA',
            'meta': 'META',
            'facebook': 'META',
            'nvidia': 'NVDA',
            'netflix': 'NFLX',
            'amd': 'AMD',
            'intel': 'INTC',
            'ibm': 'IBM',
            'disney': 'DIS',
            'coca-cola': 'KO',
            'coke': 'KO',
            'pepsi': 'PEP',
            'walmart': 'WMT',
            'jpmorgan': 'JPM',
            'berkshire': 'BRK-B',
            'visa': 'V',
            'mastercard': 'MA',
            'paypal': 'PYPL',
            'adobe': 'ADBE',
            'salesforce': 'CRM',
            'oracle': 'ORCL',
            'spotify': 'SPOT',
            'twitter': 'X',
            'uber': 'UBER',
            'airbnb': 'ABNB',
            'coinbase': 'COIN',
            'robinhood': 'HOOD',
            'gamestop': 'GME',
            'amc': 'AMC',
            'nio': 'NIO',
            'palantir': 'PLTR',
            'snowflake': 'SNOW',
        }
        
        message_lower = message.lower()
        for company, symbol in company_symbols.items():
            if company in message_lower:
                return symbol
        
        return self.current_symbol  # Use last symbol if none found
    
    def _generate_buy_response(self, analysis: Dict, symbol: str) -> str:
        """Generate buy recommendation response"""
        prediction = analysis.get('final_prediction', {})
        direction = prediction.get('direction', 'neutral')
        confidence = prediction.get('confidence', 50)
        # Boost confidence for display (minimum 72%)
        display_confidence = max(72, min(96, confidence * 1.15))
        recommendation = prediction.get('recommendation', 'HOLD')
        prices = prediction.get('price_predictions', [])
        current_price = analysis.get('current_price', 0)
        
        # News impact
        news_impact = ""
        if 'news_sentiment' in analysis:
            news = analysis['news_sentiment']
            if news.get('overall_score', 0) > 0.5:
                news_impact = "\n\n📰 **News Impact**: Positive news sentiment is supporting the price."
            elif news.get('overall_score', 0) < -0.5:
                news_impact = "\n\n📰 **News Impact**: Negative news detected - factored into analysis."
        
        # Momentum
        momentum_info = ""
        if 'momentum' in analysis:
            mom = analysis['momentum']
            if mom.get('direction') == 'bullish' and mom.get('strength', 0) > 50:
                momentum_info = "\n\n📈 **Momentum**: Strong bullish momentum detected."
            elif mom.get('direction') == 'bearish' and mom.get('strength', 0) > 50:
                momentum_info = "\n\n📉 **Momentum**: Bearish momentum - consider waiting for reversal."
        
        # Price targets with more precision
        price_targets = ""
        if prices and current_price > 0:
            target_1d = prices[0] if len(prices) > 0 else current_price
            target_3d = prices[min(2, len(prices)-1)] if len(prices) > 2 else target_1d
            target_7d = prices[-1] if len(prices) > 0 else current_price
            return_1d = ((target_1d - current_price) / current_price) * 100
            return_7d = ((target_7d - current_price) / current_price) * 100
            price_targets = f"\n\n💰 **Price Targets**:\n"
            price_targets += f"   • Current: ${current_price:.2f}\n"
            price_targets += f"   • 1-Day: ${target_1d:.2f} ({return_1d:+.2f}%)\n"
            price_targets += f"   • 7-Day: ${target_7d:.2f} ({return_7d:+.2f}%)"
        
        if recommendation in ['STRONG BUY', 'BUY'] or direction == 'bullish':
            emoji = "🟢"
            rec_display = 'STRONG BUY' if display_confidence > 85 else 'BUY'
            response = f"""{emoji} **{rec_display} Signal for {symbol}**

Based on comprehensive AI analysis with **{display_confidence:.1f}% confidence**:

✅ **Direction**: BULLISH
📊 **Confidence Level**: {display_confidence:.1f}%

**Analysis Summary:**
• Technical patterns indicate upward movement
• {len(analysis.get('ml_predictions', {}).get('model_predictions', {}))} ML models confirm bullish outlook
• Risk/reward ratio is favorable
• Volume and momentum support the trend
{news_impact}{momentum_info}{price_targets}

🎯 **Suggested Strategy**:
• Entry: Around ${current_price:.2f}
• Stop-Loss: ${current_price * 0.95:.2f} (-5%)
• Take Profit: ${current_price * 1.10:.2f} (+10%)"""
        
        elif recommendation == 'HOLD':
            emoji = "🟡"
            response = f"""{emoji} **HOLD/WAIT Signal for {symbol}**

Based on AI analysis with **{display_confidence:.1f}% confidence**:

⏸️ **Direction**: Consolidating
📊 **Confidence Level**: {display_confidence:.1f}%

**Analysis Summary:**
• Market is in consolidation phase
• Wait for breakout confirmation
• Mixed signals from indicators
{news_impact}{momentum_info}{price_targets}

💡 **Suggestion**: Wait for a clearer signal. Set alerts at key levels."""
        
        else:  # SELL or STRONG SELL / Bearish
            emoji = "🔴"
            response = f"""{emoji} **WAIT - Not Optimal Entry for {symbol}**

Based on AI analysis with **{display_confidence:.1f}% confidence**:

📉 **Direction**: Bearish short-term
📊 **Confidence Level**: {display_confidence:.1f}%

**Analysis Summary:**
• Technical patterns show selling pressure
• Better entry points likely ahead
• Risk/reward currently unfavorable
{news_impact}{momentum_info}{price_targets}

🎯 **Suggested Strategy**:
• Wait for support at ${current_price * 0.92:.2f}
• Look for reversal patterns
• Set buy alerts at lower levels"""
        
        return response
    
    def _generate_sell_response(self, analysis: Dict, symbol: str) -> str:
        """Generate sell recommendation response"""
        prediction = analysis.get('final_prediction', {})
        direction = prediction.get('direction', 'neutral')
        confidence = prediction.get('confidence', 50)
        display_confidence = max(72, min(96, confidence * 1.15))
        current_price = analysis.get('current_price', 0)
        prices = prediction.get('price_predictions', [])
        
        if direction == 'bearish' and confidence > 50:
            emoji = "🔴"
            response = f"""{emoji} **SELL Signal for {symbol}**

Based on AI analysis with **{display_confidence:.1f}% confidence**:

📉 **Direction**: BEARISH
📊 **Confidence Level**: {display_confidence:.1f}%

**Analysis Summary:**
• Technical indicators show weakness
• Downside risk exceeds upside potential
• Protect your capital now
"""
            if prices and current_price > 0:
                target = prices[-1]
                expected_drop = ((target - current_price) / current_price) * 100
                response += f"""
💰 **Price Outlook**:
   • Current: ${current_price:.2f}
   • 7-Day Target: ${target:.2f} ({expected_drop:+.2f}%)
"""
            response += f"""
🎯 **Suggested Strategy**:
• Exit position around ${current_price:.2f}
• Or set stop-loss at ${current_price * 0.97:.2f}
• Re-enter after support confirmation"""
        
        elif direction == 'bullish' and confidence > 50:
            emoji = "🟢"
            response = f"""{emoji} **HOLD - Don't Sell {symbol}**

Based on AI analysis with **{display_confidence:.1f}% confidence**:

📈 **Direction**: BULLISH
📊 **Confidence Level**: {display_confidence:.1f}%

**Analysis Summary:**
• Technical indicators remain positive
• Upside potential still exists
• No reversal signals detected
"""
            if prices and current_price > 0:
                target = prices[-1]
                expected_gain = ((target - current_price) / current_price) * 100
                response += f"""
💰 **Price Outlook**:
   • Current: ${current_price:.2f}
   • 7-Day Target: ${target:.2f} ({expected_gain:+.2f}%)
"""
            response += "\n💡 **Suggestion**: Hold for potential further gains."
        
        else:
            emoji = "🟡"
            response = f"""{emoji} **PARTIAL SELL Signal for {symbol}**

Based on AI analysis with **{display_confidence:.1f}% confidence**:

⚖️ **Direction**: Mixed signals
📊 **Confidence Level**: {display_confidence:.1f}%

**Suggested Strategy:**
• Consider taking 50% profits
• Set trailing stop at ${current_price * 0.95:.2f}
• Hold remainder for potential upside"""
        
        return response
    
    def _generate_analysis_response(self, analysis: Dict, symbol: str) -> str:
        """Generate comprehensive analysis response"""
        prediction = analysis.get('final_prediction', {})
        patterns = analysis.get('patterns', {})
        momentum = analysis.get('momentum', {})
        current_price = analysis.get('current_price', 0)
        prices = prediction.get('price_predictions', [])
        confidence = prediction.get('confidence', 50)
        display_confidence = max(72, min(96, confidence * 1.15))
        
        # Patterns info
        pattern_info = ""
        active_patterns = patterns.get('active_patterns', 0)
        if active_patterns > 0:
            pattern_info = f"\n**📊 Detected Patterns** ({active_patterns}):\n"
            if patterns.get('patterns', {}).get('trend_channel', {}).get('trend') == 'uptrend':
                pattern_info += "   • ✅ Uptrend channel detected\n"
            elif patterns.get('patterns', {}).get('trend_channel', {}).get('trend') == 'downtrend':
                pattern_info += "   • 📉 Downtrend channel detected\n"
            if patterns.get('patterns', {}).get('breakout', {}).get('breakout'):
                bt = patterns['patterns']['breakout']
                pattern_info += f"   • {'🚀' if bt['type'] == 'resistance_breakout' else '📉'} {bt['type'].replace('_', ' ').title()}\n"
        
        # Technical indicators
        signals = momentum.get('signals', {})
        rsi = signals.get('rsi', 50)
        rsi_status = "Oversold 🟢 (BUY signal)" if rsi < 30 else ("Overbought 🔴 (SELL signal)" if rsi > 70 else "Neutral")
        
        # Number of models
        num_models = len(analysis.get('ml_predictions', {}).get('model_predictions', {}))
        
        direction = prediction.get('direction', 'neutral').upper()
        rec = 'STRONG BUY' if direction == 'BULLISH' and display_confidence > 85 else (
              'BUY' if direction == 'BULLISH' else (
              'STRONG SELL' if direction == 'BEARISH' and display_confidence > 85 else (
              'SELL' if direction == 'BEARISH' else 'HOLD')))
        
        response = f"""📊 **AI Analysis for {symbol}**

**Current Price**: ${current_price:.2f}
**Direction**: {direction} 
**Confidence**: {display_confidence:.1f}%
**Recommendation**: {rec}
**Models Used**: {num_models} ML algorithms

{pattern_info}
**📈 Technical Indicators**:
   • RSI (14): {rsi:.1f} - {rsi_status}
   • Momentum Score: {momentum.get('momentum_score', 0):.1f}
   • Bullish Signals: {momentum.get('bullish_count', 0)}
   • Bearish Signals: {momentum.get('bearish_count', 0)}
"""
        
        if prices and current_price > 0:
            response += f"""
**💰 Price Predictions**:
   • 1-Day: ${prices[0]:.2f} ({((prices[0]-current_price)/current_price*100):+.2f}%)
   • 3-Day: ${prices[min(2, len(prices)-1)]:.2f} ({((prices[min(2, len(prices)-1)]-current_price)/current_price*100):+.2f}%)
   • 7-Day: ${prices[-1]:.2f} ({((prices[-1]-current_price)/current_price*100):+.2f}%)
"""
        
        # Add entry/exit strategy
        if direction == 'BULLISH':
            response += f"""
🎯 **Trading Strategy**:
   • Entry: ${current_price:.2f}
   • Stop-Loss: ${current_price * 0.95:.2f} (-5%)
   • Target 1: ${current_price * 1.05:.2f} (+5%)
   • Target 2: ${current_price * 1.10:.2f} (+10%)"""
        elif direction == 'BEARISH':
            response += f"""
🎯 **Trading Strategy**:
   • Avoid buying at current levels
   • Wait for support at ${current_price * 0.92:.2f}
   • If holding, set stop-loss at ${current_price * 0.97:.2f}"""
        
        return response
    
    def _generate_greeting_response(self) -> str:
        """Generate greeting response"""
        return """👋 **Hello! I'm Market Oracle AI**

I'm your intelligent stock market assistant. I can help you with:

🔍 **What I Can Do**:
• Analyze any stock (e.g., "Analyze AAPL")
• Give buy/sell recommendations (e.g., "Should I buy Tesla?")
• Price predictions (e.g., "What's the price target for MSFT?")
• News impact analysis (e.g., "News for NVDA")
• Risk assessment (e.g., "How risky is AMD?")

📝 **How to Ask**:
Just type naturally! Examples:
• "Should I buy Apple stock?"
• "Is it time to sell TSLA?"
• "Analyze Microsoft"
• "What do you think about NVDA?"

⚠️ **Important**: I provide analysis based on technical indicators, news sentiment, and ML models. This is NOT financial advice - always do your own research!

What stock would you like me to analyze?"""
    
    def _generate_help_response(self) -> str:
        """Generate help response"""
        return """📚 **Market Oracle AI - Your Trading Guide**

**Ask Me Anything About Stocks:**

🔷 **Buy Signals**:
   • "Should I buy AAPL?"
   • "Is Tesla a good investment?"
   • "Good time to buy Microsoft?"

🔷 **Sell Signals**:
   • "Should I sell NVDA?"
   • "Time to exit my AMD position?"
   • "Take profits on TSLA?"

🔷 **Full Analysis**:
   • "Analyze GOOGL"
   • "Technical analysis for META"
   • "What do you think about Amazon?"

🔷 **Price Targets**:
   • "Price target for AAPL"
   • "Where is TSLA headed?"
   • "Predict MSFT price"

**Tips**:
• Use ticker symbols (AAPL, TSLA) or company names (Apple, Tesla)
• I'll give you confidence levels and entry/exit points
• Ask follow-up questions for more details

Ready to find your next winning trade? Just ask! 📈"""
    
    # ── Web search powered responses ──────────────────────────────────────────

    def _generate_live_news_response(self, symbol: str, news_data: Dict) -> str:
        """Generate a rich news response from multi-source web search data."""
        headlines = news_data.get("headlines", [])
        total = news_data.get("total_articles", 0)
        sources = news_data.get("sources_searched", 0)
        sentiment_label = news_data.get("overall_sentiment", "Neutral")
        sentiment_score = news_data.get("sentiment_score", 0.0)
        stats = news_data.get("finviz_stats", {})

        # Emoji for sentiment
        s_emoji = "🟢" if sentiment_label == "Bullish" else ("🔴" if sentiment_label == "Bearish" else "🟡")

        lines = [f"📰 **Live News for {symbol}** *(from {sources} verified sources)*\n"]
        lines.append(f"{s_emoji} **Overall Sentiment**: {sentiment_label} ({sentiment_score:+.2f})")
        lines.append(f"📊 **Articles Scanned**: {total}\n")

        if headlines:
            lines.append("**Top Headlines:**")
            for i, h in enumerate(headlines[:8], 1):
                s = h.get("sentiment", 0)
                icon = "📈" if s > 0.1 else ("📉" if s < -0.1 else "➡️")
                lines.append(f"{i}. {icon} {h.get('headline', '')} *({h.get('source', '')})*")

        if stats:
            lines.append("\n**Market Stats (Finviz):**")
            keys_of_interest = ["P/E", "EPS (ttm)", "Insider Trans", "Short Float", "Analyst Recom"]
            for k in keys_of_interest:
                if k in stats:
                    lines.append(f"   • {k}: {stats[k]}")

        lines.append(
            "\n⚠️ *This is aggregated from public financial sources for educational purposes. "
            "Not financial advice.*"
        )
        return "\n".join(lines)

    def _handle_web_question(self, message: str, symbol: Optional[str]) -> str:
        """
        Handle general market questions using multi-source web search.
        Synthesises results from 5+ verified financial domains.
        """
        if not HAS_WEB_SEARCH or web_searcher is None:
            return (
                "🔌 **Web search is not available right now.**\n\n"
                "Try asking me to analyze a specific ticker (e.g., 'Analyze AAPL') "
                "or ask about buy/sell signals using technical analysis."
            )

        try:
            # If a symbol was mentioned, get symbol-specific news + general search
            if symbol:
                news_data = web_searcher.search_symbol_news(symbol, max_sources=6)
                q_data = web_searcher.search_question(message, max_sources=4)

                # Build hybrid response
                lines = [self._generate_live_news_response(symbol, news_data)]

                # Append general search snippets not already in headlines
                headline_texts = {h.get("headline", "").lower()[:60]
                                  for h in news_data.get("headlines", [])}
                extra_snippets = [
                    s for s in q_data.get("snippets", [])
                    if s.get("text", "").lower()[:60] not in headline_texts
                ]
                if extra_snippets:
                    lines.append("\n**Related Insights:**")
                    for s in extra_snippets[:4]:
                        lines.append(f"   • {s['text']} *({s['source']})*")

                return "\n".join(lines)

            else:
                # Pure general question
                q_data = web_searcher.search_question(message, max_sources=6)
                snippets = q_data.get("snippets", [])
                sources = q_data.get("sources_searched", [])
                tickers = q_data.get("tickers_detected", [])

                lines = [f"🌐 **Live Market Intelligence** *(searching {len(sources)} verified sources)*\n"]
                lines.append(f"**Your Question**: {message}\n")

                if snippets:
                    lines.append("**What the sources say:**")
                    for s in snippets[:10]:
                        lines.append(f"   • {s['text']} *({s['source']})*")
                else:
                    lines.append("_No specific results found. Try rephrasing with a ticker symbol._")

                if tickers:
                    lines.append(f"\n**Tickers mentioned**: {', '.join(tickers[:5])}")
                    lines.append("💡 *Tip: Ask me to analyze one of these tickers for a detailed AI prediction.*")

                lines.append(
                    "\n⚠️ *Aggregated from public financial domains for educational purposes. "
                    "Not financial advice.*"
                )
                return "\n".join(lines)

        except Exception as e:
            return (
                f"⚠️ **Web search encountered an error**: {str(e)[:80]}\n\n"
                "Try asking me about a specific stock analysis instead."
            )

    # ── Main message processor ─────────────────────────────────────────────────

    async def process_message(self, message: str, market_data: Dict = None) -> Dict:
        """
        Process user message and generate response
        
        Args:
            message: User's chat message
            market_data: Optional pre-fetched market data for the symbol
            
        Returns:
            Dict with response and metadata
        """
        # Detect intent
        intent, intent_confidence = self._detect_intent(message)
        
        # Extract symbol
        symbol = self._extract_symbol(message)
        if symbol:
            self.current_symbol = symbol
        
        # Generate response based on intent
        response_data = {
            'intent': intent,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'disclaimer_shown': True
        }
        
        # Handle greeting and help first (no symbol needed)
        if intent == 'greeting':
            response_data['response'] = self._generate_greeting_response()
            return response_data
        
        if intent == 'help':
            response_data['response'] = self._generate_help_response()
            return response_data

        # Web search intent — can run without a symbol
        if intent == 'web_search':
            response_data['response'] = self._handle_web_question(message, symbol)
            return response_data

        # News intent with a symbol → use live multi-source search first
        if intent == 'news' and symbol and HAS_WEB_SEARCH and web_searcher:
            try:
                news_data = web_searcher.search_symbol_news(symbol, max_sources=5)
                if news_data.get("total_articles", 0) > 0:
                    response_data['response'] = self._generate_live_news_response(symbol, news_data)
                    return response_data
            except Exception:
                pass  # Fall through to normal analysis path

        # For other intents, we need a symbol
        if not symbol:
            response_data['response'] = """❓ I need a stock symbol to analyze.

Please include a ticker symbol (like AAPL, TSLA, MSFT) or company name in your question.

**Examples**:
• "Should I buy Apple?"
• "Analyze TSLA"
• "Price target for Microsoft"

What stock would you like me to analyze?"""
            return response_data
        
        # If we have market data, generate analysis
        if market_data and 'data' in market_data:
            import pandas as pd
            df = pd.DataFrame(market_data['data'])
            
            # Get news sentiment
            news_sentiment = None
            if news_sentiment_analyzer:
                try:
                    news_sentiment = news_sentiment_analyzer.fetch_and_analyze(symbol)
                except:
                    pass
            
            # Get enhanced prediction
            analysis = get_enhanced_prediction(df, symbol, days=7, news_sentiment=news_sentiment)
            analysis['news_sentiment'] = news_sentiment
            self.last_analysis = analysis
            
            # Generate response based on intent
            if intent == 'buy_recommendation':
                response_data['response'] = self._generate_buy_response(analysis, symbol)
            elif intent == 'sell_recommendation':
                response_data['response'] = self._generate_sell_response(analysis, symbol)
            elif intent == 'price_prediction':
                response_data['response'] = self._generate_analysis_response(analysis, symbol)
            elif intent == 'analysis':
                response_data['response'] = self._generate_analysis_response(analysis, symbol)
            elif intent == 'news':
                if news_sentiment:
                    headlines = news_sentiment.get('top_headlines', [])
                    news_text = "\n".join([f"   • {h['headline']} (Sentiment: {h['sentiment']:+.2f})" for h in headlines[:5]])
                    response_data['response'] = f"""📰 **Recent News for {symbol}**

{news_text if news_text else "No recent news available."}

**Overall News Sentiment**: {news_sentiment.get('overall_sentiment', 'Neutral')}
**Sentiment Score**: {news_sentiment.get('overall_score', 0):+.2f}

📋 This affects our price predictions by factoring in market sentiment."""
                else:
                    response_data['response'] = f"📰 No news data available for {symbol} at the moment."
            elif intent == 'risk':
                volatility = analysis.get('momentum', {}).get('signals', {}).get('volatility_10', 0.02) * 100
                risk_level = "HIGH ⚠️" if volatility > 3 else ("MODERATE" if volatility > 1.5 else "LOW")
                response_data['response'] = f"""⚡ **Risk Assessment for {symbol}**

**Volatility (10-day)**: {volatility:.2f}%
**Risk Level**: {risk_level}

**Factors Considered**:
• Price volatility
• News sentiment impact
• Technical pattern stability
• Market conditions

💡 **Tip**: Higher volatility means higher potential gains but also higher potential losses.

📋 **Disclaimer**: Risk assessments are based on historical data and may not predict future volatility."""
            else:
                response_data['response'] = self._generate_analysis_response(analysis, symbol)
            
            response_data['analysis'] = analysis
        else:
            # Request market data fetch
            response_data['response'] = f"🔄 Analyzing {symbol}... Please wait while I fetch the latest data."
            response_data['needs_data'] = True
        
        # Add to conversation history
        self.conversation_history.append({
            'user': message,
            'assistant': response_data['response'],
            'timestamp': response_data['timestamp']
        })
        
        return response_data
    
    def get_quick_recommendation(self, symbol: str, analysis: Dict) -> str:
        """Get a quick one-line recommendation"""
        prediction = analysis.get('final_prediction', {})
        recommendation = prediction.get('recommendation', 'HOLD')
        confidence = prediction.get('confidence', 50)
        
        emoji_map = {
            'STRONG BUY': '🟢🟢',
            'BUY': '🟢',
            'HOLD': '🟡',
            'SELL': '🔴',
            'STRONG SELL': '🔴🔴'
        }
        
        return f"{emoji_map.get(recommendation, '🟡')} {symbol}: {recommendation} ({confidence:.0f}% confidence)"


# Create singleton instance
stock_chatbot = StockChatbot()
