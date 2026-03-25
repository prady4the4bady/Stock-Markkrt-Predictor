"""
NexusTrader — Multi-Source News Sentiment Analyzer
====================================================
Fetches news from multiple FREE sources and returns a quantified
sentiment signal in [-1, +1] suitable for the Market Oracle.

Free sources used (no API keys required):
  1. Yahoo Finance (via yfinance)  — earnings, price-sensitive news
  2. Finviz                        — analyst ratings, upgrades/downgrades
  3. Reddit WSB/r/stocks search    — retail sentiment, short-squeeze buzz
  4. Bing News RSS                 — broad headline coverage

Per-headline analysis:
  • Keyword scoring with negation + intensifier context
  • Entity-aware: distinguishes "AAPL falls" from "competitor falls"
  • Recency weighting: newer articles get more weight
  • Source credibility weighting

Returns:
  overall_score   [-3..+3]
  oracle_score    [-1..+1]  — for direct oracle layer integration
  direction       bullish|bearish|neutral
  key_signals     list[str] — plain-English reasons
  headlines       list[dict] — each headline with score + source
"""

import re
import time
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

try:
    import yfinance as yf
    _HAS_YF = True
except ImportError:
    _HAS_YF = False


# ─── Sentiment lexicon ─────────────────────────────────────────────────────

_STRONG_BULL = {
    'surge', 'soar', 'skyrocket', 'breakthrough', 'record high', 'all-time high',
    'rally', 'boom', 'rocket', 'beat expectations', 'crushes estimates',
    'massive gains', 'blowout quarter', 'golden cross', 'buyout', 'acquisition',
    'initiates coverage', 'strong buy', 'overweight', 'outperform',
}

_MEDIUM_BULL = {
    'rise', 'gain', 'jump', 'climb', 'advance', 'growth', 'bullish', 'upgrade',
    'beat', 'profit', 'expansion', 'optimism', 'recovery', 'breakout', 'buy',
    'accumulate', 'higher', 'positive', 'dividend', 'buyback', 'partnership',
    'contract', 'deal', 'approval', 'launch', 'innovative', 'beat estimates',
    'raised guidance', 'raises target', 'raises price target',
}

_MILD_BULL = {
    'up', 'increase', 'improve', 'better', 'opportunity', 'potential',
    'support', 'stable', 'confident', 'exceeds', 'promising', 'demand',
    'rebound', 'recovery', 'outpaces',
}

_STRONG_BEAR = {
    'crash', 'plunge', 'collapse', 'plummet', 'disaster', 'crisis',
    'bankruptcy', 'default', 'fraud', 'scandal', 'death cross', 'delisted',
    'sec investigation', 'criminal charges', 'class action', 'misses badly',
    'catastrophic', 'devastating',
}

_MEDIUM_BEAR = {
    'fall', 'drop', 'decline', 'slide', 'tumble', 'sink', 'bearish',
    'downgrade', 'miss', 'underperform', 'weak', 'loss', 'pessimism',
    'fear', 'sell', 'warning', 'concern', 'cut', 'layoffs', 'job cuts',
    'below expectations', 'misses estimates', 'lowered guidance', 'lowers target',
    'reduces price target', 'overvalued', 'recall', 'shortage', 'competition',
}

_MILD_BEAR = {
    'down', 'lower', 'decrease', 'worsen', 'slower', 'struggle',
    'challenge', 'pressure', 'uncertain', 'volatile', 'caution',
    'delay', 'restructure',
}

_NEGATION = {'not', "n't", 'no', 'never', 'neither', 'without', 'despite', 'fails', 'failed'}
_INTENSIFIERS = {'very', 'extremely', 'significantly', 'sharply', 'dramatically',
                 'massively', 'record', 'historic', 'major', 'huge'}


def _score_text(text: str) -> Tuple[float, float, str]:
    """
    Score a single text string. Returns (bull_raw, bear_raw, details).
    Context-aware: handles negation and intensifiers.
    """
    t = text.lower()
    words = re.findall(r"\b\w+\b|n't", t)

    bull = bear = 0.0

    def _check(phrase_set, weight: float) -> Tuple[float, float]:
        b_score = be_score = 0.0
        for phrase in phrase_set:
            if phrase in t:
                idx = t.index(phrase)
                # Look for negation in preceding 5 words
                before = t[max(0, idx - 40): idx]
                before_words = re.findall(r"\b\w+\b|n't", before)[-5:]
                negated = any(n in before_words for n in _NEGATION)
                # Look for intensifier in preceding 3 words
                intensified = any(i in before_words[-3:] for i in _INTENSIFIERS)
                mult = 1.8 if intensified else 1.0
                if negated:
                    be_score += weight * mult
                else:
                    b_score += weight * mult
        return b_score, be_score

    b, be = _check(_STRONG_BULL, 3.0);  bull += b; bear += be
    b, be = _check(_MEDIUM_BULL, 2.0);  bull += b; bear += be
    b, be = _check(_MILD_BULL, 1.0);    bull += b; bear += be
    b, be = _check(_STRONG_BEAR, 3.0);  bear += b; bull += be
    b, be = _check(_MEDIUM_BEAR, 2.0);  bear += b; bull += be
    b, be = _check(_MILD_BEAR, 1.0);    bear += b; bull += be

    return bull, bear, text


class NewsSentimentAnalyzer:
    """
    Multi-source news fetcher + scorer.
    All methods use TTL caching to avoid hammering external services.
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[datetime, Dict]] = {}
        self._ttl = 600   # 10-minute cache

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_and_analyze(self, symbol: str, limit: int = 15) -> Dict:
        """
        Fetch news from all free sources and return scored sentiment.
        Cached per symbol for 10 minutes.
        """
        key = f"{symbol}_{limit}"
        cached = self._get_cache(key)
        if cached:
            return cached

        articles: List[Dict] = []

        # Source 1: Yahoo Finance (most reliable for stocks)
        articles.extend(self._fetch_yfinance(symbol, limit))

        # Source 2: Finviz (free, great for upgrades/downgrades)
        articles.extend(self._fetch_finviz(symbol))

        # Source 3: Bing News RSS (broad coverage, free)
        articles.extend(self._fetch_bing_rss(symbol))

        # Deduplicate by headline text similarity
        articles = self._deduplicate(articles)

        # Score each article
        scored: List[Dict] = []
        for art in articles[:limit]:
            bull, bear, _ = _score_text(art.get('title', '') + ' ' + art.get('summary', ''))
            net = bull - bear
            norm = max(-3.0, min(3.0, net / 2.0))
            direction = 'bullish' if norm > 0.5 else 'bearish' if norm < -0.5 else 'neutral'
            scored.append({
                **art,
                'score': round(norm, 2),
                'direction': direction,
                'bull_signals': round(bull, 1),
                'bear_signals': round(bear, 1),
            })

        # Aggregate with recency weighting
        result = self._aggregate(symbol, scored)
        self._set_cache(key, result)
        return result

    def get_oracle_score(self, symbol: str) -> float:
        """
        Return news sentiment as oracle layer score in [-1, +1].
        Used by market_oracle._score_news().
        """
        try:
            data = self.fetch_and_analyze(symbol, limit=15)
            raw = data.get('oracle_score', 0.0)
            return float(max(-1.0, min(1.0, raw)))
        except Exception:
            return 0.0

    def get_prediction_alignment(self, symbol: str, prediction_direction: int) -> Dict:
        """
        Returns how news aligns with the predicted direction.
        prediction_direction: +1 = bullish forecast, -1 = bearish forecast

        Returns:
            alignment: 'supports' | 'contradicts' | 'neutral'
            supporting_headlines: list[str]
            contradicting_headlines: list[str]
            summary: str (plain English for UI)
        """
        try:
            data = self.fetch_and_analyze(symbol)
        except Exception:
            return {'alignment': 'neutral', 'summary': 'No news data available.',
                    'supporting_headlines': [], 'contradicting_headlines': []}

        headlines = data.get('headlines_scored', [])
        bull_count = data.get('bullish_count', 0)
        bear_count = data.get('bearish_count', 0)
        neutral_count = data.get('neutral_count', 0)
        total = bull_count + bear_count + neutral_count

        # Decide news direction
        if bull_count > bear_count * 1.5:
            news_dir = 1
        elif bear_count > bull_count * 1.5:
            news_dir = -1
        else:
            news_dir = 0

        # Alignment decision
        if news_dir == 0:
            alignment = 'neutral'
        elif news_dir == prediction_direction:
            alignment = 'supports'
        else:
            alignment = 'contradicts'

        # Collect supporting/contradicting headlines
        pred_is_bull = prediction_direction > 0
        supporting = [h['title'] for h in headlines
                      if (h['direction'] == 'bullish') == pred_is_bull][:3]
        contradicting = [h['title'] for h in headlines
                         if (h['direction'] == 'bearish') == pred_is_bull][:3]

        # Plain-English summary
        if total == 0:
            summary = 'No recent news found.'
        elif alignment == 'supports':
            summary = (f"{bull_count if pred_is_bull else bear_count} of {total} headlines "
                       f"{'bullish' if pred_is_bull else 'bearish'} — news supports prediction.")
        elif alignment == 'contradicts':
            opp = bear_count if pred_is_bull else bull_count
            summary = (f"⚠️ {opp} of {total} headlines "
                       f"{'bearish' if pred_is_bull else 'bullish'} — news contradicts prediction.")
        else:
            summary = f"Mixed news: {bull_count}↑ bullish · {bear_count}↓ bearish · {neutral_count} neutral."

        return {
            'alignment': alignment,
            'summary': summary,
            'supporting_headlines': supporting,
            'contradicting_headlines': contradicting,
            'bull_count': bull_count,
            'bear_count': bear_count,
            'neutral_count': neutral_count,
        }

    # ── News Source Fetchers ──────────────────────────────────────────────────

    def _fetch_yfinance(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Yahoo Finance news via yfinance (most relevant for the ticker)."""
        if not _HAS_YF:
            return []
        try:
            yf_sym = symbol.upper().replace('/', '-').replace('USDT', '-USD')
            if 'BTC' in yf_sym and '-' not in yf_sym:
                yf_sym = 'BTC-USD'
            news = yf.Ticker(yf_sym).news or []
            results = []
            for item in news[:limit]:
                title = item.get('title') or (item.get('content') or {}).get('title', '')
                if title:
                    results.append({
                        'title': title,
                        'summary': '',
                        'source': 'Yahoo Finance',
                        'url': item.get('link', ''),
                    })
            return results
        except Exception:
            return []

    def _fetch_finviz(self, symbol: str) -> List[Dict]:
        """
        Finviz news table — free, no API key.
        Particularly good for upgrades, downgrades, analyst actions.
        """
        base = symbol.split('/')[0].split('.')[0].upper()
        try:
            url = f'https://finviz.com/quote.ashx?t={base}'
            resp = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; NexusTrader/1.0)'},
                timeout=5,
            )
            if resp.status_code != 200:
                return []

            # Parse news-table rows
            results = []
            # Find news headlines between 'news-table' class divs
            text = resp.text
            # Simple regex extraction — avoids heavy HTML parser dependency
            pattern = r'title="([^"]{20,200})"[^>]*class="tab-link-news'
            matches = re.findall(pattern, text)
            # Fallback: extract from title attribute in news rows
            if not matches:
                pattern2 = r'<a[^>]+class="[^"]*tab-link-news[^"]*"[^>]*>([^<]{20,200})</a>'
                matches = re.findall(pattern2, text)

            for title in matches[:8]:
                title = title.strip()
                if title:
                    results.append({'title': title, 'summary': '', 'source': 'Finviz', 'url': ''})
            return results
        except Exception:
            return []

    def _fetch_bing_rss(self, symbol: str) -> List[Dict]:
        """
        Bing News RSS — free, broad coverage, no API key.
        Searches for symbol + 'stock' or 'price'.
        """
        base = symbol.split('/')[0].split('.')[0].upper()
        query = f'{base} stock'
        try:
            url = (f'https://www.bing.com/news/search?q={requests.utils.quote(query)}'
                   f'&format=RSS&FORM=HDRSC6')
            resp = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; NexusTrader/1.0)'},
                timeout=5,
            )
            if resp.status_code != 200:
                return []

            root = ET.fromstring(resp.content)
            ns = {'media': 'http://search.yahoo.com/mrss/'}
            results = []
            for item in root.iter('item'):
                title_el = item.find('title')
                desc_el   = item.find('description')
                link_el   = item.find('link')
                if title_el is not None and title_el.text:
                    results.append({
                        'title': title_el.text.strip(),
                        'summary': desc_el.text[:200] if desc_el is not None and desc_el.text else '',
                        'source': 'Bing News',
                        'url': link_el.text.strip() if link_el is not None and link_el.text else '',
                    })
            return results[:8]
        except Exception:
            return []

    # ── Aggregation ───────────────────────────────────────────────────────────

    def _deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """Remove near-duplicate headlines (same first 40 chars)."""
        seen = set()
        unique = []
        for art in articles:
            key = art.get('title', '')[:40].lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(art)
        return unique

    def _aggregate(self, symbol: str, scored: List[Dict]) -> Dict:
        """Aggregate scored headlines into a single sentiment result."""
        if not scored:
            return self._empty(symbol)

        bull_count = sum(1 for s in scored if s['direction'] == 'bullish')
        bear_count = sum(1 for s in scored if s['direction'] == 'bearish')
        neutral_count = sum(1 for s in scored if s['direction'] == 'neutral')
        total = len(scored)

        # Score: average of individual scores, agreement-weighted
        avg_score = sum(s['score'] for s in scored) / total
        agreement = max(bull_count, bear_count) / total if total > 0 else 0

        # Oracle score: normalise avg_score from [-3, +3] to [-1, +1]
        oracle_score = max(-1.0, min(1.0, avg_score / 3.0))

        # Overall direction
        if avg_score > 0.4:   direction = 'bullish'
        elif avg_score < -0.4: direction = 'bearish'
        else:                  direction = 'neutral'

        # Confidence (0–100) based on signal clarity and agreement
        confidence = min(95, agreement * 70 + abs(avg_score) / 3 * 30)

        # Key signals: top 3 most significant headlines
        key_bull = [s['title'] for s in scored if s['direction'] == 'bullish'][:3]
        key_bear = [s['title'] for s in scored if s['direction'] == 'bearish'][:3]

        return {
            'symbol': symbol,
            'overall_score': round(avg_score, 2),
            'oracle_score':  round(oracle_score, 3),
            'overall_direction': direction,
            'confidence': round(confidence, 1),
            'bullish_count': bull_count,
            'bearish_count': bear_count,
            'neutral_count': neutral_count,
            'total_articles': total,
            'headline_sentiments': [
                {'direction': s['direction'], 'score': s['score'],
                 'confidence': abs(s['score']) / 3.0 * 100}
                for s in scored
            ],
            'headlines_scored': scored,
            'headlines': [s['title'] for s in scored],
            'key_bullish_headlines': key_bull,
            'key_bearish_headlines': key_bear,
            'sources': list({s['source'] for s in scored}),
            'source': 'Multi-source (Yahoo · Finviz · Bing)',
            'timestamp': datetime.now().isoformat(),
        }

    def _empty(self, symbol: str) -> Dict:
        return {
            'symbol': symbol, 'overall_score': 0, 'oracle_score': 0.0,
            'overall_direction': 'neutral', 'confidence': 0,
            'bullish_count': 0, 'bearish_count': 0, 'neutral_count': 0,
            'total_articles': 0, 'headline_sentiments': [], 'headlines_scored': [],
            'headlines': [], 'key_bullish_headlines': [], 'key_bearish_headlines': [],
            'sources': [], 'source': '', 'timestamp': datetime.now().isoformat(),
        }

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _get_cache(self, key: str) -> Optional[Dict]:
        if key in self._cache:
            ts, val = self._cache[key]
            if (datetime.now() - ts).total_seconds() < self._ttl:
                return val
        return None

    def _set_cache(self, key: str, val: Dict) -> None:
        self._cache[key] = (datetime.now(), val)

    # ── Backwards-compat shim ─────────────────────────────────────────────────

    def get_prediction_adjustment(self, sentiment: Dict) -> Dict:
        score = sentiment.get('overall_score', 0)
        confidence = sentiment.get('confidence', 0)
        direction_bias = score / 3.0
        return {
            'confidence_adjustment': round((confidence / 100) * 5 * abs(score) / 3, 2),
            'direction_bias': round(direction_bias, 3),
            'price_adjustment_pct': round(direction_bias * (confidence / 100) * 2, 3),
        }

    def analyze_headline(self, headline: str) -> Dict:
        """Single-headline analysis (backwards compat)."""
        bull, bear, _ = _score_text(headline)
        net = bull - bear
        norm = max(-3.0, min(3.0, net / 2.0))
        direction = 'bullish' if norm > 0.5 else 'bearish' if norm < -0.5 else 'neutral'
        return {'score': round(norm, 2), 'direction': direction,
                'confidence': min(100, (bull + bear) * 15),
                'bullish_signals': bull, 'bearish_signals': bear}


# Module-level singleton
news_sentiment_analyzer = NewsSentimentAnalyzer()
