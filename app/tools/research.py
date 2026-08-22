import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any
import httpx

from app.config import SEMANTIC_SCHOLAR_API_KEY, TOOL_RETRIES, TOOL_TIMEOUT

# Recency window for the first OpenAlex attempt (emerging research, not classics)
RECENT_WINDOW_DAYS = 1095  # ~3 years

# In-process cache (5-min TTL)
_RESEARCH_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


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
        dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)
    except Exception:
        pass
    try:
        if len(pub_date_str) == 4 and pub_date_str.isdigit():
            dt = datetime(int(pub_date_str), 1, 1, tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return max(0, (now - dt).days)
    except Exception:
        pass
    return None


def _reconstruct_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstructs text abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    words.sort(key=lambda x: x[0])
    full_text = " ".join([w[1] for w in words])
    return full_text[:300] + ("..." if len(full_text) > 300 else "")


def search_openalex(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Primary research search via OpenAlex REST API.

    Biased toward recent work first: a pure relevance sort returns the classic
    highly-cited papers, which is the wrong answer for "what research is emerging".
    Falls back to the unfiltered relevance search when the recent window is empty.
    """
    clean_query = query.strip()
    url = "https://api.openalex.org/works"
    headers = {
        "User-Agent": "AgentX24-ResearchAgent/1.0 (mailto:research@agentx24.internal)",
    }
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS)).strftime("%Y-%m-%d")

    attempts: list[dict[str, Any]] = [
        {"search": clean_query, "per-page": limit, "sort": "relevance_score:desc",
         "filter": f"from_publication_date:{cutoff}"},
        {"search": clean_query, "per-page": limit, "sort": "relevance_score:desc"},
    ]

    raw_results: list[dict[str, Any]] = []
    for params in attempts:
        with httpx.Client(timeout=TOOL_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        raw_results = data.get("results", [])
        if raw_results:
            break

    results: list[dict[str, Any]] = []

    for item in raw_results:
        title = item.get("display_name") or item.get("title") or "Untitled Paper"
        doi = item.get("doi")
        landing_page = (item.get("primary_location") or {}).get("landing_page_url") or doi or item.get("id") or ""
        pub_date = item.get("publication_date") or str(item.get("publication_year", ""))
        
        # Extract authors
        authors = []
        for authorship in item.get("authorships", []):
            author_obj = authorship.get("author", {})
            name = author_obj.get("display_name")
            if name:
                authors.append(name)

        # Extract venue / source
        source_name = "OpenAlex"
        primary_loc = item.get("primary_location") or {}
        source_obj = primary_loc.get("source") or {}
        if source_obj and source_obj.get("display_name"):
            source_name = source_obj.get("display_name")

        abstract = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
        snippet = abstract or f"Paper published in {source_name} with {item.get('cited_by_count', 0)} citations."

        results.append({
            "title": title,
            "url": landing_page,
            "source": source_name,
            "published": pub_date if pub_date else None,
            "days_old": _calculate_days_old(pub_date),
            "authors": authors[:5],
            "snippet": snippet,
            "provider": "openalex",
            "provider_kind": "research",
            "meta": {
                "citations": item.get("cited_by_count", 0),
                "doi": doi,
                "openalex_id": item.get("id"),
            },
        })

    return results


def search_arxiv(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Fallback research search via arXiv Atom API (newest first)."""
    clean_query = query.strip()
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{clean_query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    headers = {
        "User-Agent": "AgentX24-ResearchAgent/1.0",
    }

    with httpx.Client(timeout=TOOL_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    results: list[dict[str, Any]] = []

    for entry in entries:
        title_el = entry.find("{http://www.w3.org/2005/Atom}title")
        summary_el = entry.find("{http://www.w3.org/2005/Atom}summary")
        pub_el = entry.find("{http://www.w3.org/2005/Atom}published")
        id_el = entry.find("{http://www.w3.org/2005/Atom}id")

        title = re.sub(r"\s+", " ", title_el.text.strip()) if title_el is not None and title_el.text else "Untitled"
        summary = re.sub(r"\s+", " ", summary_el.text.strip()) if summary_el is not None and summary_el.text else ""
        pub_date = pub_el.text.strip()[:10] if pub_el is not None and pub_el.text else None
        arxiv_url = id_el.text.strip() if id_el is not None and id_el.text else ""

        authors = []
        for a in entry.findall("{http://www.w3.org/2005/Atom}author"):
            name_el = a.find("{http://www.w3.org/2005/Atom}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        snippet = summary[:300] + ("..." if len(summary) > 300 else "")

        results.append({
            "title": title,
            "url": arxiv_url,
            "source": "arXiv.org",
            "published": pub_date,
            "days_old": _calculate_days_old(pub_date),
            "authors": authors[:5],
            "snippet": snippet,
            "provider": "arxiv",
            "provider_kind": "research",
            "meta": {"arxiv_id": arxiv_url.split("/")[-1] if arxiv_url else ""},
        })

    return results


def search_semantic_scholar(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Optional Semantic Scholar search if API key is provided."""
    if not SEMANTIC_SCHOLAR_API_KEY:
        return []
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,publicationDate,abstract,url,citationCount,venue",
    }
    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY}
    with httpx.Client(timeout=TOOL_TIMEOUT) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for p in data.get("data", []):
            pub_date = p.get("publicationDate") or str(p.get("year", ""))
            authors = [a.get("name") for a in p.get("authors", []) if a.get("name")]
            results.append({
                "title": p.get("title", "Untitled"),
                "url": p.get("url") or f"https://www.semanticscholar.org/paper/{p.get('paperId')}",
                "source": p.get("venue") or "Semantic Scholar",
                "published": pub_date if pub_date else None,
                "days_old": _calculate_days_old(pub_date),
                "authors": authors[:5],
                "snippet": (p.get("abstract") or p.get("title", ""))[:300],
                "provider": "semantic_scholar",
                "provider_kind": "research",
                "meta": {"citations": p.get("citationCount", 0)},
            })
        return results


def research_search(query: str, limit: int = 8) -> dict[str, Any]:
    """Main entry point for research_search tool."""
    query = query.strip()
    if not query:
        return {"results": [], "note": "Empty research query provided."}

    cache_key = f"research:{query.lower()}:{limit}"
    now_ts = datetime.now().timestamp()
    if cache_key in _RESEARCH_CACHE:
        ts, cached_res = _RESEARCH_CACHE[cache_key]
        if now_ts - ts < 300:
            return {"results": cached_res, "note": f"Retrieved {len(cached_res)} items from cache."}

    errors = []
    results = []

    # 1. Primary: OpenAlex
    try:
        results = search_openalex(query, limit=limit)
    except Exception as e:
        errors.append(f"OpenAlex error: {e}")

    # 2. Fallback: arXiv Atom
    if not results:
        try:
            results = search_arxiv(query, limit=limit)
        except Exception as e:
            errors.append(f"arXiv error: {e}")

    # 3. Optional: Semantic Scholar
    if not results and SEMANTIC_SCHOLAR_API_KEY:
        try:
            results = search_semantic_scholar(query, limit=limit)
        except Exception as e:
            errors.append(f"Semantic Scholar error: {e}")

    if not results and errors:
        return {
            "error": "tool_unavailable",
            "tool": "research_search",
            "detail": "; ".join(errors),
            "results": [],
        }

    _RESEARCH_CACHE[cache_key] = (now_ts, results)
    return {
        "results": results,
        "note": f"Found {len(results)} scientific papers for '{query}'." if results else f"No scientific papers found for '{query}'.",
    }


# Tool schema declaration for Gemini
RESEARCH_SEARCH_SCHEMA = {
    "name": "research_search",
    "description": "Searches academic papers, scientific publications, preprints, journal articles, authors, and citation metadata on technical or scientific topics.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Scientific or technical research topic, paper title, or author name (e.g. 'solid state battery degradation' or 'transformer architecture optimizations').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of papers to return (default 8, max 15).",
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
    test_query = sys.argv[1] if len(sys.argv) > 1 else "solid state battery"
    print(f"=== Testing research_search tool with query: '{test_query}' ===")
    res = research_search(test_query, limit=5)
    papers = res.get("results", [])
    print(f"Status: {res.get('note', '')}")
    print(f"Total papers returned: {len(papers)}")
    for i, p in enumerate(papers[:5], 1):
        print(f"\n[{i}] {p.get('title')}")
        print(f"    Source   : {p.get('source')} | Published: {p.get('published')} ({p.get('days_old')} days old)")
        print(f"    Authors  : {', '.join(p.get('authors', []))}")
        print(f"    URL      : {p.get('url')}")
    print("\n===========================================================")
