import re
import sys
from datetime import datetime
from typing import Any
import httpx

from app.config import EPO_OPS_KEY, EPO_OPS_SECRET, TOOL_TIMEOUT
from app.tools.web import _get_ddgs_client

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# In-process cache (5-min TTL), consistent with the other tool adapters
_PATENT_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}

_PATENT_NUMBER_RE = re.compile(r"/patent/([A-Z]{2}[A-Z0-9]+)(?:/|$)", re.IGNORECASE)


def has_epo_credentials() -> bool:
    """True only when EPO OPS OAuth credentials are configured."""
    return bool(EPO_OPS_KEY and EPO_OPS_SECRET)


def has_web_patent_provider() -> bool:
    """True when the credential-free Google Patents (web-indexed) provider can run."""
    return _get_ddgs_client() is not None


def is_patent_tool_available() -> bool:
    """Returns True only if at least one real patent provider can actually run.
    The tool is never advertised to the agent otherwise, so the model can never
    select a broken tool, and the report states the gap honestly instead.
    """
    return has_epo_credentials() or has_web_patent_provider()


def active_patent_provider() -> str:
    if has_epo_credentials():
        return "EPO OPS"
    if has_web_patent_provider():
        return "Google Patents (web-indexed)"
    return "none"


def search_google_patents_via_web(query: str, limit: int = 6) -> list[dict[str, Any]]:
    """Credential-free patent discovery: real Google Patents records located via web search.

    This is patent *discovery*, not a patent-office database query: every record
    returned is a real published patent page with a real publication number and URL.
    No patent data is ever synthesised.
    """
    ddgs_cls = _get_ddgs_client()
    if not ddgs_cls:
        return []

    results: list[dict[str, Any]] = []
    try:
        with ddgs_cls() as ddgs:
            raw_items = list(ddgs.text(f"site:patents.google.com {query.strip()}", max_results=limit))
    except Exception:
        return []

    for item in raw_items:
        href = item.get("href") or item.get("url") or ""
        if "patents.google.com" not in href:
            continue

        number_match = _PATENT_NUMBER_RE.search(href)
        patent_number = number_match.group(1).upper() if number_match else ""

        raw_title = (item.get("title") or "").strip()
        title = re.sub(r"\s*-\s*Google Patents\s*$", "", raw_title).strip()
        if patent_number and title.upper().startswith(patent_number):
            title = title[len(patent_number):].lstrip(" -\u2013").strip()
            # Drop a leftover kind code (e.g. "A1 - ...") when the URL omitted it
            title = re.sub(r"^[A-Z]\d?\s*[-\u2013]\s*", "", title).strip()
        if not title:
            title = patent_number or "Patent record"

        snippet = (item.get("body") or item.get("snippet") or "").strip()[:300]

        results.append({
            "title": f"{patent_number} - {title}" if patent_number else title,
            "url": href,
            "source": "Google Patents",
            "published": None,
            "days_old": None,
            "snippet": snippet or title,
            "provider": "google_patents_web",
            "provider_kind": "patent",
            "meta": {
                "patent_number": patent_number,
                "discovery": "web-indexed Google Patents record (not a patent-office API query)",
            },
        })

    return results


def search_epo_ops(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """EPO OPS search. Requires registered OAuth credentials.

    Response parsing is not implemented yet, so this raises rather than reporting
    a false success with zero results.
    """
    token_url = "https://ops.epo.org/3.2/auth/accesstoken"
    with httpx.Client(timeout=TOOL_TIMEOUT) as client:
        token_resp = client.post(
            token_url,
            auth=(EPO_OPS_KEY, EPO_OPS_SECRET),
            data={"grant_type": "client_credentials"},
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")

        search_resp = client.get(
            "https://ops.epo.org/3.2/rest-services/published-data/search",
            params={"q": query},
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        search_resp.raise_for_status()

    raise NotImplementedError(
        "EPO OPS credentials authenticated but response parsing is not implemented; "
        "falling back to the web-indexed Google Patents provider."
    )


def patent_search(query: str, limit: int = 6) -> dict[str, Any]:
    """Main entry point for the patent_search tool."""
    query = query.strip()
    if not query:
        return {"results": [], "note": "Empty patent query provided."}

    if not is_patent_tool_available():
        return {
            "error": "tool_unavailable",
            "tool": "patent_search",
            "detail": "No patent provider is available in this environment.",
            "results": [],
        }

    cache_key = f"patent:{query.lower()}:{limit}"
    now_ts = datetime.now().timestamp()
    if cache_key in _PATENT_CACHE:
        ts, cached_res = _PATENT_CACHE[cache_key]
        if now_ts - ts < 300:
            return {"results": cached_res, "note": f"Retrieved {len(cached_res)} patent records from cache."}

    errors: list[str] = []
    results: list[dict[str, Any]] = []

    # 1. Preferred: EPO OPS, only when credentials exist
    if has_epo_credentials():
        try:
            results = search_epo_ops(query, limit=limit)
        except Exception as e:
            errors.append(f"EPO OPS error: {e}")

    # 2. Credential-free fallback: real Google Patents records located via web search
    if not results:
        try:
            results = search_google_patents_via_web(query, limit=limit)
        except Exception as e:
            errors.append(f"Google Patents (web) error: {e}")

    if not results:
        return {
            "error": "tool_unavailable" if errors else "no_results",
            "tool": "patent_search",
            "detail": "; ".join(errors) or f"No patent records found for '{query}'.",
            "results": [],
        }

    _PATENT_CACHE[cache_key] = (now_ts, results)
    return {
        "results": results,
        "note": (
            f"Found {len(results)} published patent records for '{query}' "
            f"via {active_patent_provider()}."
        ),
    }


PATENT_SEARCH_SCHEMA = {
    "name": "patent_search",
    "description": "Searches published patents and patent applications by technology area, keyword, or assignee company. Returns real published patent records with publication numbers and links. Use this to assess a competitor's or a technology's intellectual-property activity.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Patent keyword, technology area, or company assignee name (e.g. 'solid state battery electrolyte' or 'NVIDIA GPU interconnect').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of patent records to return (default 6, max 15).",
            },
        },
        "required": ["query"],
    },
}


if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "solid state battery electrolyte"
    print(f"=== Testing patent_search tool with query: '{test_query}' ===")
    print(f"EPO credentials    : {has_epo_credentials()}")
    print(f"Web patent provider: {has_web_patent_provider()}")
    print(f"Active provider    : {active_patent_provider()}")
    res = patent_search(test_query, limit=5)
    items = res.get("results", [])
    print(f"Status: {res.get('note') or res.get('detail')}")
    print(f"Total patent records: {len(items)}")
    for i, p in enumerate(items[:5], 1):
        print(f"\n[{i}] {p.get('title')}")
        print(f"    Number : {p.get('meta', {}).get('patent_number')}")
        print(f"    URL    : {p.get('url')}")
    print("\n========================================================")
