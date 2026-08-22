import re
import sys
from datetime import datetime, timezone
from typing import Any
import httpx

from app.config import TOOL_RETRIES, TOOL_TIMEOUT

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# In-process cache (5-min TTL)
_WEB_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _get_ddgs_client() -> Any | None:
    """Dynamically loads DDGS class to avoid static IDE unresolved import errors."""
    import importlib
    for mod_name in ("ddgs", "duckduckgo_search"):
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "DDGS"):
                return getattr(mod, "DDGS")
        except Exception:
            continue
    return None


def search_ddgs(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Primary web search using DuckDuckGo (ddgs or duckduckgo_search package)."""
    ddgs_cls = _get_ddgs_client()
    if not ddgs_cls:
        return []

    results: list[dict[str, Any]] = []
    try:
        with ddgs_cls() as ddgs:
            raw_items = list(ddgs.text(query.strip(), max_results=limit))
            for item in raw_items:
                title = item.get("title", "Untitled")
                href = item.get("href") or item.get("url") or ""
                body = item.get("body") or item.get("snippet") or ""

                # Extract domain as source
                source = "Web"
                if href:
                    try:
                        match = re.search(r"https?://(?:www\.)?([^/]+)", href)
                        if match:
                            source = match.group(1)
                    except Exception:
                        pass

                results.append({
                    "title": title,
                    "url": href,
                    "source": source,
                    "published": None,
                    "days_old": None,
                    "snippet": body[:300],
                    "provider": "ddgs",
                    "provider_kind": "web",
                })
    except Exception:
        return []

    return results


def search_wikipedia_api(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fallback web search using Wikipedia Search API."""
    clean_query = query.strip()
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": clean_query,
        "format": "json",
        "srlimit": limit,
    }
    headers = {
        "User-Agent": "AgentX24App/1.0 (contact@agentx24.internal)",
    }

    with httpx.Client(timeout=TOOL_TIMEOUT) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    search_items = data.get("query", {}).get("search", [])
    results: list[dict[str, Any]] = []

    for item in search_items:
        title = item.get("title", "Wikipedia Article")
        page_id = item.get("pageid")
        clean_title = title.replace(" ", "_")
        page_url = f"https://en.wikipedia.org/wiki/{clean_title}"
        raw_snippet = item.get("snippet", "")
        clean_snippet = re.sub(r"<[^>]+>", " ", raw_snippet).strip()
        timestamp = item.get("timestamp")
        pub_date = timestamp[:10] if timestamp else None

        results.append({
            "title": f"Wikipedia: {title}",
            "url": page_url,
            "source": "Wikipedia.org",
            "published": pub_date,
            "days_old": None,
            "snippet": clean_snippet or title,
            "provider": "wikipedia",
            "provider_kind": "web",
            "meta": {"pageid": page_id},
        })

    return results


def web_search(query: str, limit: int = 8) -> dict[str, Any]:
    """Main entry point for web_search tool."""
    query = query.strip()
    if not query:
        return {"results": [], "note": "Empty web search query provided."}

    cache_key = f"web:{query.lower()}:{limit}"
    now_ts = datetime.now().timestamp()
    if cache_key in _WEB_CACHE:
        ts, cached_res = _WEB_CACHE[cache_key]
        if now_ts - ts < 300:
            return {"results": cached_res, "note": f"Retrieved {len(cached_res)} items from cache."}

    errors = []
    results = []

    # 1. Primary: DDGS
    try:
        results = search_ddgs(query, limit=limit)
    except Exception as e:
        errors.append(f"DuckDuckGo error: {e}")

    # 2. Fallback: Wikipedia API
    if not results:
        try:
            results = search_wikipedia_api(query, limit=limit)
        except Exception as e:
            errors.append(f"Wikipedia error: {e}")

    if not results and errors:
        return {
            "error": "tool_unavailable",
            "tool": "web_search",
            "detail": "; ".join(errors),
            "results": [],
        }

    _WEB_CACHE[cache_key] = (now_ts, results)
    return {
        "results": results,
        "note": f"Found {len(results)} web results for '{query}'." if results else f"No web results found for '{query}'.",
    }


WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": "Performs general web and encyclopedia search for company profiles, technology overviews, market reports, and reference data.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "General web search terms or company/topic name (e.g. 'NVIDIA company overview' or 'quantum computing companies').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default 8, max 15).",
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
    test_query = sys.argv[1] if len(sys.argv) > 1 else "NVIDIA Blackwell architecture"
    print(f"=== Testing web_search tool with query: '{test_query}' ===")
    res = web_search(test_query, limit=5)
    items = res.get("results", [])
    print(f"Status: {res.get('note', '')}")
    print(f"Total results: {len(items)}")
    for i, it in enumerate(items[:5], 1):
        print(f"\n[{i}] {it.get('title')}")
        print(f"    Source: {it.get('source')} | URL: {it.get('url')}")
        print(f"    Snippet: {it.get('snippet')[:100]}...")
    print("\n========================================================")
