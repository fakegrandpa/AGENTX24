import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
import httpx

from app.config import NEWSDATA_API_KEY, TOOL_RETRIES, TOOL_TIMEOUT
from app.models import Evidence

# In-process cache to make repeated/rehearsed queries instant (5-min TTL)
_NEWS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _calculate_days_old(pub_date_str: str | None) -> int | None:
    if not pub_date_str:
        return None
    try:
        if len(pub_date_str) >= 10 and pub_date_str[4] == "-" and pub_date_str[7] == "-":
            dt = datetime.strptime(pub_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return max(0, (now - dt).days)
    except Exception:
        pass
    try:
        dt = parsedate_to_datetime(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)
    except Exception:
        pass
    return None


def search_google_news_rss(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Searches Google News RSS and returns parsed items."""
    clean_query = query.strip()
    url = "https://news.google.com/rss/search"
    # Passed as params so targets containing '&' (e.g. "AT&T", "P&G") are encoded correctly
    params = {"q": clean_query, "hl": "en-US", "gl": "US", "ceid": "US:en"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    last_exc = None
    for attempt in range(TOOL_RETRIES + 1):
        try:
            with httpx.Client(timeout=TOOL_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(url, params=params, headers=headers)
                resp.raise_for_status()

            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            results = []

            for item in items[:limit]:
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                source_el = item.find("source")
                desc_el = item.find("description")

                title = title_el.text.strip() if title_el is not None and title_el.text else "Untitled"
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else None
                source = source_el.text.strip() if source_el is not None and source_el.text else "Google News"
                
                snippet = ""
                if desc_el is not None and desc_el.text:
                    clean_desc = re.sub(r"<[^>]+>", " ", desc_el.text).strip()
                    snippet = clean_desc[:250]

                # Convert date to standard ISO format if possible
                iso_date = None
                days_old = _calculate_days_old(pub_date)
                if pub_date:
                    try:
                        iso_date = parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
                    except Exception:
                        iso_date = pub_date[:10]

                results.append({
                    "title": title,
                    "url": link,
                    "source": source,
                    "published": iso_date,
                    "days_old": days_old,
                    "snippet": snippet or title,
                    "provider": "google_news_rss",
                    "provider_kind": "news",
                })

            return results
        except Exception as e:
            last_exc = e

    raise RuntimeError(f"Google News RSS request failed after retries: {last_exc}")


def search_newsdata_io(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Optional search via NewsData.io if API key is provided."""
    if not NEWSDATA_API_KEY:
        return []
    url = "https://newsdata.io/api/1/news"
    params = {"apikey": NEWSDATA_API_KEY, "q": query, "language": "en"}
    with httpx.Client(timeout=TOOL_TIMEOUT) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("results", [])
        results = []
        for a in articles[:limit]:
            pub_date = a.get("pubDate")
            results.append({
                "title": a.get("title", "Untitled"),
                "url": a.get("link", ""),
                "source": a.get("source_id", "NewsData"),
                "published": pub_date[:10] if pub_date else None,
                "days_old": _calculate_days_old(pub_date),
                "snippet": a.get("description", "") or a.get("title", ""),
                "provider": "newsdata_io",
                "provider_kind": "news",
            })
        return results


def news_search(query: str, limit: int = 8) -> dict[str, Any]:
    """Main entry point for news_search tool."""
    query = query.strip()
    if not query:
        return {"results": [], "note": "Empty search query provided."}

    # Check cache
    cache_key = f"news:{query.lower()}:{limit}"
    now_ts = datetime.now().timestamp()
    if cache_key in _NEWS_CACHE:
        ts, cached_res = _NEWS_CACHE[cache_key]
        if now_ts - ts < 300:  # 5 min TTL
            return {"results": cached_res, "note": f"Retrieved {len(cached_res)} items from cache."}

    errors = []
    results = []

    # 1. Primary: Google News RSS
    try:
        results = search_google_news_rss(query, limit=limit)
    except Exception as e:
        errors.append(f"Google News RSS error: {e}")

    # 2. Secondary (if configured): NewsData.io
    if not results and NEWSDATA_API_KEY:
        try:
            results = search_newsdata_io(query, limit=limit)
        except Exception as e:
            errors.append(f"NewsData.io error: {e}")

    if not results and errors:
        return {
            "error": "tool_unavailable",
            "tool": "news_search",
            "detail": "; ".join(errors),
            "results": [],
        }

    _NEWS_CACHE[cache_key] = (now_ts, results)
    return {
        "results": results,
        "note": f"Found {len(results)} news articles for '{query}'." if results else f"No news articles found for '{query}'.",
    }


# Tool schema declaration for Gemini
NEWS_SEARCH_SCHEMA = {
    "name": "news_search",
    "description": "Searches recent news headlines, articles, press releases, and market updates for a given company, competitor, product, or industry topic.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query, company name, competitor, or market topic (e.g. 'NVIDIA data center earnings' or 'OpenAI models').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of articles to return (default 8, max 15).",
            },
            "reason": {
                "type": "string",
                "description": "One short sentence stating why this tool is needed right now, given the investigation objective and the evidence already gathered.",
            },
        },
        "required": ["query", "reason"],
    },
}


if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "NVIDIA"
    print(f"=== Testing news_search tool with query: '{test_query}' ===")
    res = news_search(test_query, limit=5)
    articles = res.get("results", [])
    print(f"Status: {res.get('note', '')}")
    print(f"Total articles returned: {len(articles)}")
    for i, a in enumerate(articles[:5], 1):
        print(f"\n[{i}] {a.get('title')}")
        print(f"    Source   : {a.get('source')}")
        print(f"    Published: {a.get('published')} ({a.get('days_old')} days old)")
        print(f"    URL      : {a.get('url')}")
    print("\n========================================================")
