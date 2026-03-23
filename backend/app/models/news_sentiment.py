"""
Market Oracle - News Sentiment Analyzer
Analyzes news headlines to extract market sentiment for better predictions
Uses keyword-based and pattern matching for fast, realistic sentiment analysis
"""
import re
from typing import Dict, List, Tuple
from datetime import datetime
import yfinance as yf


class NewsSentimentAnalyzer:
    """
    Analyzes news headlines to determine market sentiment
    Returns sentiment scores that can influence prediction confidence
    """
    
    # Bullish keywords and phrases with weights
    BULLISH_KEYWORDS = {
        # Strong bullish (weight 3)
        'surge': 3, 'soar': 3, 'skyrocket': 3, 'breakthrough': 3, 'record high': 3,
        'all-time high': 3, 'rally': 3, 'boom': 3, 'explode': 3, 'rocket': 3,
        
        # Medium bullish (weight 2)
        'rise': 2, 'gain': 2, 'jump': 2, 'climb': 2, 'advance': 2, 'growth': 2,
        'bullish': 2, 'upgrade': 2, 'beat': 2, 'outperform': 2, 'strong': 2,
        'profit': 2, 'expansion': 2, 'optimism': 2, 'positive': 2, 'recovery': 2,
        'momentum': 2, 'breakout': 2, 'buy': 2, 'accumulate': 2,
        
        # Mild bullish (weight 1)
        'up': 1, 'higher': 1, 'increase': 1, 'improve': 1, 'better': 1,
        'opportunity': 1, 'potential': 1, 'support': 1, 'stable': 1, 'confident': 1,
        'exceed': 1, 'promising': 1, 'innovative': 1, 'leading': 1, 'demand': 1
    }
    
    # Bearish keywords and phrases with weights
    BEARISH_KEYWORDS = {
        # Strong bearish (weight 3)
        'crash': 3, 'plunge': 3, 'collapse': 3, 'plummet': 3, 'disaster': 3,
        'crisis': 3, 'bankruptcy': 3, 'default': 3, 'fraud': 3, 'scandal': 3,
        
        # Medium bearish (weight 2)
        'fall': 2, 'drop': 2, 'decline': 2, 'slide': 2, 'tumble': 2, 'sink': 2,
        'bearish': 2, 'downgrade': 2, 'miss': 2, 'underperform': 2, 'weak': 2,
        'loss': 2, 'contraction': 2, 'pessimism': 2, 'negative': 2, 'fear': 2,
        'sell': 2, 'warning': 2, 'concern': 2, 'risk': 2, 'cut': 2,
        
        # Mild bearish (weight 1)
        'down': 1, 'lower': 1, 'decrease': 1, 'worsen': 1, 'slower': 1,
        'struggle': 1, 'challenge': 1, 'pressure': 1, 'uncertain': 1, 'volatile': 1,
        'caution': 1, 'delay': 1, 'layoff': 1, 'restructure': 1, 'competition': 1
    }
    
    # Context modifiers that flip sentiment
    NEGATION_WORDS = ['not', 'no', 'never', 'neither', 'without', 'despite', 'fails']
    
    # Intensifiers that increase weight
    INTENSIFIERS = ['very', 'extremely', 'significantly', 'sharply', 'dramatically', 'massively']
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
    
    def analyze_headline(self, headline: str) -> Dict:
        """
        Analyze a single headline for sentiment
        Returns: {score: -3 to +3, direction: 'bullish'/'bearish'/'neutral', confidence: 0-100}
        """
        if not headline:
            return {'score': 0, 'direction': 'neutral', 'confidence': 0}
        
        headline_lower = headline.lower()
        words = headline_lower.split()
        
        bullish_score = 0
        bearish_score = 0
        
        # Check for negation context
        has_negation = any(neg in words for neg in self.NEGATION_WORDS)
        
        # Check for intensifiers
        has_intensifier = any(intens in words for intens in self.INTENSIFIERS)
        multiplier = 1.5 if has_intensifier else 1.0
        
        # Score bullish keywords
        for keyword, weight in self.BULLISH_KEYWORDS.items():
            if keyword in headline_lower:
                if has_negation:
                    bearish_score += weight * multiplier
                else:
                    bullish_score += weight * multiplier
        
        # Score bearish keywords
        for keyword, weight in self.BEARISH_KEYWORDS.items():
            if keyword in headline_lower:
                if has_negation:
                    bullish_score += weight * multiplier
                else:
                    bearish_score += weight * multiplier
        
        # Calculate final score (-3 to +3)
        net_score = bullish_score - bearish_score
        normalized_score = max(-3, min(3, net_score / 2))
        
        # Determine direction
        if normalized_score > 0.5:
            direction = 'bullish'
        elif normalized_score < -0.5:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        # Confidence is based on how strong the signals are
        total_signals = bullish_score + bearish_score
        confidence = min(100, total_signals * 15)
        
        return {
            'score': round(normalized_score, 2),
            'direction': direction,
            'confidence': round(confidence, 1),
            'bullish_signals': bullish_score,
            'bearish_signals': bearish_score
        }
    
    def analyze_headlines(self, headlines: List[str]) -> Dict:
        """
        Analyze multiple headlines and return aggregate sentiment
        """
        if not headlines:
            return {
                'overall_score': 0,
                'overall_direction': 'neutral',
                'confidence': 0,
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0,
                'headline_sentiments': []
            }
        
        sentiments = [self.analyze_headline(h) for h in headlines]
        
        # Aggregate scores
        scores = [s['score'] for s in sentiments]
        avg_score = sum(scores) / len(scores)
        
        # Count directions
        bullish_count = sum(1 for s in sentiments if s['direction'] == 'bullish')
        bearish_count = sum(1 for s in sentiments if s['direction'] == 'bearish')
        neutral_count = sum(1 for s in sentiments if s['direction'] == 'neutral')
        
        # Overall direction
        if avg_score > 0.3:
            overall_direction = 'bullish'
        elif avg_score < -0.3:
            overall_direction = 'bearish'
        else:
            overall_direction = 'neutral'
        
        # Confidence based on agreement and signal strength
        avg_confidence = sum(s['confidence'] for s in sentiments) / len(sentiments)
        agreement_factor = max(bullish_count, bearish_count) / len(headlines)
        overall_confidence = avg_confidence * (0.5 + agreement_factor * 0.5)
        
        return {
            'overall_score': round(avg_score, 2),
            'overall_direction': overall_direction,
            'confidence': round(overall_confidence, 1),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'headline_sentiments': sentiments
        }
    
    def fetch_and_analyze(self, symbol: str, limit: int = 10) -> Dict:
        """
        Fetch news for a symbol and analyze sentiment
        Uses caching to avoid excessive API calls
        """
        cache_key = f"{symbol}_{limit}"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        # Fetch news from yfinance
        try:
            # Clean symbol for yfinance
            yf_symbol = symbol.upper().replace("/", "-").replace("USDT", "-USD")
            if "BTC" in yf_symbol and "-" not in yf_symbol:
                yf_symbol = "BTC-USD"
            
            ticker = yf.Ticker(yf_symbol)
            news = ticker.news or []
            
            # Extract headlines
            headlines = []
            for item in news[:limit]:
                title = item.get('title')
                if not title and 'content' in item:
                    title = item['content'].get('title')
                if title:
                    headlines.append(title)
            
            # Analyze
            result = self.analyze_headlines(headlines)
            result['symbol'] = symbol
            result['headlines'] = headlines
            result['source'] = 'Yahoo Finance'
            result['timestamp'] = now.isoformat()
            
            # Cache result
            self.cache[cache_key] = (now, result)
            
            return result
            
        except Exception as e:
            print(f"[News Sentiment Error] {e}")
            return {
                'symbol': symbol,
                'overall_score': 0,
                'overall_direction': 'neutral',
                'confidence': 0,
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0,
                'headline_sentiments': [],
                'headlines': [],
                'error': str(e),
                'timestamp': now.isoformat()
            }
    
    def get_prediction_adjustment(self, sentiment: Dict) -> Dict:
        """
        Calculate how sentiment should adjust predictions
        Returns adjustment factors for confidence and price direction
        """
        score = sentiment.get('overall_score', 0)
        confidence = sentiment.get('confidence', 0)
        
        # Confidence adjustment (-5% to +5% based on news clarity)
        confidence_adj = (confidence / 100) * 5 * abs(score) / 3
        
        # Direction bias (how much to weight predictions toward bullish/bearish)
        # score range is -3 to +3, convert to -1 to +1
        direction_bias = score / 3
        
        # Price adjustment suggestion (percentage)
        # Based on sentiment strength and confidence
        price_adj_pct = direction_bias * (confidence / 100) * 2  # Max ±2% adjustment
        
        return {
            'confidence_adjustment': round(confidence_adj, 2),
            'direction_bias': round(direction_bias, 3),
            'price_adjustment_pct': round(price_adj_pct, 3),
            'should_adjust': confidence > 30 and abs(score) > 0.5,
            'recommendation': 'bullish_bias' if score > 0.5 else ('bearish_bias' if score < -0.5 else 'neutral')
        }


# Singleton instance for reuse
news_sentiment_analyzer = NewsSentimentAnalyzer()
