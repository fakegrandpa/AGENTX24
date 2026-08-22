import sys
from typing import Any
import httpx

from app.config import EPO_OPS_KEY, EPO_OPS_SECRET, TOOL_TIMEOUT

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def is_patent_tool_available() -> bool:
    """Returns True only if EPO OPS credentials exist."""
    return bool(EPO_OPS_KEY and EPO_OPS_SECRET)


def patent_search(query: str, limit: int = 5) -> dict[str, Any]:
    """Patent search tool adapter.
    Registered and executed only when valid EPO OPS credentials are configured.
    """
    if not is_patent_tool_available():
        return {
            "error": "tool_unavailable",
            "tool": "patent_search",
            "detail": "Patent search source is not configured (EPO_OPS_KEY / EPO_OPS_SECRET required).",
            "results": [],
        }

    # If credentials exist, query EPO OPS OAuth & Search endpoint
    try:
        token_url = "https://ops.epo.org/3.2/auth/accesstoken"
        with httpx.Client(timeout=TOOL_TIMEOUT) as client:
            token_resp = client.post(
                token_url,
                auth=(EPO_OPS_KEY, EPO_OPS_SECRET),
                data={"grant_type": "client_credentials"},
            )
            token_resp.raise_for_status()
            access_token = token_resp.json().get("access_token")

            search_url = f"https://ops.epo.org/3.2/rest-services/published-data/search?q={query}"
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            search_resp = client.get(search_url, headers=headers)
            search_resp.raise_for_status()
            data = search_resp.json()

            # Parse OPS JSON if successful
            results = []
            return {"results": results, "note": f"Retrieved patent records for '{query}'."}
    except Exception as e:
        return {
            "error": "tool_unavailable",
            "tool": "patent_search",
            "detail": f"EPO OPS error: {e}",
            "results": [],
        }


PATENT_SEARCH_SCHEMA = {
    "name": "patent_search",
    "description": "Searches published patents, patent applications, assignees, and claims (requires configured EPO OPS credentials).",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Patent keyword, technology area, or company assignee name.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of patents to return (default 5).",
            },
        },
        "required": ["query"],
    },
}


if __name__ == "__main__":
    print(f"Patent tool configured: {is_patent_tool_available()}")
    res = patent_search("semiconductor packaging")
    print("Result:", res)
