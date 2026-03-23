"""
NexusTrader - Multi-Domain Financial Web Search
Searches verified financial domains in parallel and synthesises results.

Verified source domains:
  finance.yahoo.com     - quotes, news, fundamentals
  reuters.com           - global financial news
  cnbc.com              - breaking market news
  marketwatch.com       - market data, analysis
  investing.com         - live data, news
  finviz.com            - screener, news aggregator
  macrotrends.net       - long-term charts / ratios
  tradingeconomics.com  - macro indicators
  sec.gov               - official SEC filings
  wsj.com               - Wall Street Journal
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime

# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_TIMEOUT = 8  # seconds per source


def _safe_get(url: str, timeout: int = _TIMEOUT) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception:
        return None


def _text_from_soup(soup: BeautifulSoup, selector: str) -> str:
    """Extract clean text from first CSS-selector match."""
    el = soup.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def _all_text(soup: BeautifulSoup, selector: str, limit: int = 5) -> List[str]:
    return [el.get_text(" ", strip=True) for el in soup.select(selector)[:limit]]


# ---------------------------------------------------------------------------
# Per-source scrapers
# ---------------------------------------------------------------------------

def _scrape_yahoo_finance(query: str) -> Dict:
    """Yahoo Finance news search."""
    url = f"https://finance.yahoo.com/quote/{query.upper()}/news/"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    headlines = _all_text(soup, "h3.clamp", 8)
    if not headlines:
        headlines = _all_text(soup, "[data-test-locator='headline']", 8)
    if not headlines:
        headlines = _all_text(soup, "li.js-stream-content h3", 8)
    return {"source": "Yahoo Finance", "headlines": headlines, "url": url}


def _scrape_yahoo_search(query: str) -> Dict:
    """Yahoo Finance general search for non-ticker queries."""
    url = f"https://finance.yahoo.com/search/?q={requests.utils.quote(query)}"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    headlines = _all_text(soup, "h3", 6)
    return {"source": "Yahoo Finance Search", "headlines": headlines, "url": url}


def _scrape_reuters(query: str) -> Dict:
    """Reuters search."""
    url = f"https://www.reuters.com/search/news/?blob={requests.utils.quote(query)}"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    headlines = _all_text(soup, "h3.search-result-title", 6)
    if not headlines:
        headlines = _all_text(soup, "a.search-result-title", 6)
    snippets = _all_text(soup, "p.search-result-excerpt", 4)
    return {"source": "Reuters", "headlines": headlines, "snippets": snippets, "url": url}


def _scrape_cnbc(query: str) -> Dict:
    """CNBC search."""
    url = f"https://www.cnbc.com/search/?query={requests.utils.quote(query)}&qsearchterm={requests.utils.quote(query)}"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    headlines = _all_text(soup, "div.SearchResult-searchResultTitle", 6)
    if not headlines:
        headlines = _all_text(soup, "a.resultlink", 6)
    return {"source": "CNBC", "headlines": headlines, "url": url}


def _scrape_marketwatch(query: str) -> Dict:
    """MarketWatch search."""
    url = f"https://www.marketwatch.com/search?q={requests.utils.quote(query)}&ts=0&tab=All%20News"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    headlines = _all_text(soup, "div.article__headline", 6)
    if not headlines:
        headlines = _all_text(soup, "h3.article__headline", 6)
    return {"source": "MarketWatch", "headlines": headlines, "url": url}


def _scrape_finviz(query: str) -> Dict:
    """Finviz news for a ticker symbol."""
    url = f"https://finviz.com/quote.ashx?t={query.upper()}"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    # Finviz news table
    rows = soup.select("table.fullview-news-outer tr")
    headlines = []
    for row in rows[:8]:
        a = row.find("a", class_="tab-link-news")
        if a:
            headlines.append(a.get_text(strip=True))
    # also try fundamental stats
    stats = {}
    cells = soup.select("table.snapshot-table2 td.snapshot-td2")
    labels = soup.select("table.snapshot-table2 td.snapshot-td2-cp")
    for label, cell in zip(labels, cells):
        key = label.get_text(strip=True)
        val = cell.get_text(strip=True)
        if key and val:
            stats[key] = val
    return {"source": "Finviz", "headlines": headlines, "stats": stats, "url": url}


def _scrape_investing(query: str) -> Dict:
    """Investing.com news search (basic)."""
    url = f"https://www.investing.com/search/?q={requests.utils.quote(query)}"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    headlines = _all_text(soup, "article.js-article-item h2", 6)
    if not headlines:
        headlines = _all_text(soup, "li.js-category-item a", 6)
    return {"source": "Investing.com", "headlines": headlines, "url": url}


def _scrape_macrotrends(query: str) -> Dict:
    """Macrotrends - fundamental ratios."""
    url = f"https://www.macrotrends.net/stocks/charts/{query.upper()}/stock/pe-ratio"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    title = soup.title.string if soup.title else ""
    # Get first paragraph of content
    blurb = _text_from_soup(soup, "div.jqplot-description")
    return {"source": "Macrotrends", "title": title, "blurb": blurb, "url": url}


def _scrape_tradingeconomics(query: str) -> Dict:
    """Trading Economics macro indicator search."""
    url = f"https://tradingeconomics.com/search?q={requests.utils.quote(query)}"
    r = _safe_get(url)
    if not r:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    results = _all_text(soup, "table td a", 8)
    return {"source": "Trading Economics", "results": results, "url": url}


def _scrape_sec_edgar(query: str) -> Dict:
    """SEC EDGAR full-text search for filings."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{requests.utils.quote(query)}%22&dateRange=custom&startdt=2024-01-01&forms=8-K,10-K"
    r = _safe_get(url)
    if not r:
        return {}
    try:
        data = r.json()
        hits = data.get("hits", {}).get("hits", [])
        filings = [
            {
                "title": h.get("_source", {}).get("display_names", [query])[0],
                "form": h.get("_source", {}).get("form_type", ""),
                "date": h.get("_source", {}).get("period_of_report", ""),
            }
            for h in hits[:4]
        ]
        return {"source": "SEC EDGAR", "filings": filings, "url": url}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------
_TICKER_SOURCES = [
    _scrape_yahoo_finance,
    _scrape_finviz,
    _scrape_reuters,
    _scrape_cnbc,
    _scrape_marketwatch,
    _scrape_investing,
]

_GENERAL_SOURCES = [
    _scrape_yahoo_search,
    _scrape_reuters,
    _scrape_cnbc,
    _scrape_marketwatch,
    _scrape_tradingeconomics,
    _scrape_investing,
]

_ALL_SOURCES = {
    "yahoo": _scrape_yahoo_finance,
    "yahoo_search": _scrape_yahoo_search,
    "reuters": _scrape_reuters,
    "cnbc": _scrape_cnbc,
    "marketwatch": _scrape_marketwatch,
    "finviz": _scrape_finviz,
    "investing": _scrape_investing,
    "macrotrends": _scrape_macrotrends,
    "tradingeconomics": _scrape_tradingeconomics,
    "sec": _scrape_sec_edgar,
}


# ---------------------------------------------------------------------------
# Simple sentiment scorer
# ---------------------------------------------------------------------------
_POSITIVE_WORDS = {
    "surge", "soar", "rally", "gain", "rise", "profit", "beat", "strong",
    "bullish", "upgrade", "buy", "growth", "record", "high", "outperform",
    "positive", "boost", "expand", "increase", "up", "win", "success",
}
_NEGATIVE_WORDS = {
    "fall", "drop", "decline", "loss", "miss", "weak", "bearish", "downgrade",
    "sell", "concern", "risk", "low", "underperform", "negative", "cut",
    "crash", "fear", "slump", "decrease", "warning", "investigation", "lawsuit",
}


def _score_headline(text: str) -> float:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


# ---------------------------------------------------------------------------
# Main WebSearcher class
# ---------------------------------------------------------------------------
class WebSearcher:
    """
    Parallel multi-source financial web searcher.
    All I/O happens in a thread pool so it doesn't block FastAPI.
    """

    def __init__(self, max_workers: int = 6, per_source_timeout: int = 8):
        self.max_workers = max_workers
        self.per_source_timeout = per_source_timeout
        # Simple in-memory cache {query: (timestamp, result)}
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5 minutes

    # ── Internal ────────────────────────────────────────────────────────────

    def _from_cache(self, key: str) -> Optional[Dict]:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
        return None

    def _to_cache(self, key: str, data: Dict):
        self._cache[key] = (time.time(), data)

    def _run_sources(self, fns: list, query: str) -> List[Dict]:
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(fn, query): fn.__name__ for fn in fns}
            for fut in as_completed(futures, timeout=self.per_source_timeout + 2):
                try:
                    r = fut.result(timeout=self.per_source_timeout)
                    if r and (r.get("headlines") or r.get("results") or r.get("filings")):
                        results.append(r)
                except Exception:
                    pass
        return results

    # ── Public API ───────────────────────────────────────────────────────────

    def search_symbol_news(self, symbol: str, max_sources: int = 6) -> Dict:
        """
        Fetch and synthesise news for a ticker symbol from multiple sources.
        Returns merged headlines, aggregate sentiment, and per-source data.
        """
        key = f"news:{symbol.upper()}"
        cached = self._from_cache(key)
        if cached:
            return cached

        fns = _TICKER_SOURCES[:max_sources]
        raw = self._run_sources(fns, symbol)

        # Merge headlines, deduplicate
        all_headlines: List[Dict] = []
        seen = set()
        for r in raw:
            for h in r.get("headlines", []):
                norm = h.lower()[:80]
                if norm not in seen and len(h) > 10:
                    seen.add(norm)
                    all_headlines.append({
                        "headline": h,
                        "source": r["source"],
                        "sentiment": _score_headline(h),
                    })

        # Stats from finviz if available
        stats = {}
        for r in raw:
            if r.get("source") == "Finviz":
                stats = r.get("stats", {})
                break

        # Aggregate sentiment
        scores = [h["sentiment"] for h in all_headlines if h["sentiment"] != 0.0]
        avg_sentiment = round(sum(scores) / len(scores), 3) if scores else 0.0
        sentiment_label = (
            "Bullish" if avg_sentiment > 0.1
            else "Bearish" if avg_sentiment < -0.1
            else "Neutral"
        )

        result = {
            "symbol": symbol.upper(),
            "headlines": all_headlines[:15],
            "total_articles": len(all_headlines),
            "sources_searched": len(raw),
            "overall_sentiment": sentiment_label,
            "sentiment_score": avg_sentiment,
            "finviz_stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
        self._to_cache(key, result)
        return result

    def search_question(self, question: str, max_sources: int = 5) -> Dict:
        """
        Answer a free-form financial question by searching multiple sources.
        Extracts the most relevant snippets from each source.
        """
        key = f"q:{question[:60]}"
        cached = self._from_cache(key)
        if cached:
            return cached

        # Extract potential ticker from question
        tickers = re.findall(r'\b([A-Z]{2,5})\b', question.upper())
        common = {"I", "A", "IS", "IT", "THE", "FOR", "AND", "OR", "OF", "TO",
                  "IN", "ON", "AT", "BY", "BE", "DO", "HOW", "WHY", "WHAT",
                  "WHEN", "WHERE", "WILL", "CAN", "DO", "BUY", "SELL", "HOLD"}
        tickers = [t for t in tickers if t not in common]

        fns = _GENERAL_SOURCES[:max_sources]
        raw = self._run_sources(fns, question)

        # Also search ticker-specific if found
        if tickers:
            ticker_raw = self._run_sources(_TICKER_SOURCES[:3], tickers[0])
            raw.extend(ticker_raw)

        snippets: List[Dict] = []
        seen = set()
        for r in raw:
            for h in r.get("headlines", []) + r.get("results", []):
                norm = h.lower()[:80]
                if norm not in seen and len(h) > 10:
                    seen.add(norm)
                    snippets.append({"text": h, "source": r["source"]})

        # Also include any filings
        for r in raw:
            for f in r.get("filings", []):
                snippets.append({
                    "text": f"{f.get('form','')} — {f.get('title','')} ({f.get('date','')})",
                    "source": "SEC EDGAR"
                })

        result = {
            "question": question,
            "snippets": snippets[:20],
            "sources_searched": [r["source"] for r in raw],
            "tickers_detected": tickers,
            "timestamp": datetime.now().isoformat(),
        }
        self._to_cache(key, result)
        return result

    def get_macro_context(self) -> Dict:
        """Fetch macro / economic context (VIX, yields, DXY via yfinance + TE)."""
        key = "macro"
        cached = self._from_cache(key)
        if cached:
            return cached

        macro = {}
        try:
            import yfinance as yf
            tickers = {"VIX": "^VIX", "DXY": "DX-Y.NYB", "10Y": "^TNX", "2Y": "^IRX"}
            for name, sym in tickers.items():
                try:
                    t = yf.Ticker(sym)
                    price = t.fast_info.last_price
                    macro[name] = round(float(price), 2) if price else None
                except Exception:
                    macro[name] = None
        except ImportError:
            pass

        result = {
            "macro": macro,
            "timestamp": datetime.now().isoformat(),
        }
        self._to_cache(key, result)
        return result


# Singleton
web_searcher = WebSearcher()
