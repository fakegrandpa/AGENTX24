from typing import Any, Callable
from app.tools.news import news_search, NEWS_SEARCH_SCHEMA
from app.tools.research import research_search, RESEARCH_SEARCH_SCHEMA
from app.tools.web import web_search, WEB_SEARCH_SCHEMA
from app.tools.patents import patent_search, PATENT_SEARCH_SCHEMA, is_patent_tool_available

# Tool registration contract: (schema, callable)
TOOL_REGISTRY: dict[str, tuple[dict[str, Any], Callable[..., dict[str, Any]]]] = {
    "news_search": (NEWS_SEARCH_SCHEMA, news_search),
    "research_search": (RESEARCH_SEARCH_SCHEMA, research_search),
    "web_search": (WEB_SEARCH_SCHEMA, web_search),
    "patent_search": (PATENT_SEARCH_SCHEMA, patent_search),
}


def get_advertised_tools() -> list[dict[str, Any]]:
    """Returns the list of tool schemas advertised to Gemini.
    Note: Patent search is only advertised if credentials exist, avoiding broken tool traps.
    """
    advertised = [
        NEWS_SEARCH_SCHEMA,
        RESEARCH_SEARCH_SCHEMA,
        WEB_SEARCH_SCHEMA,
    ]
    if is_patent_tool_available():
        advertised.append(PATENT_SEARCH_SCHEMA)
    return advertised


def execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Validates and executes a tool call, returning structured error data on failure."""
    if name not in TOOL_REGISTRY:
        return {
            "error": "unknown_tool",
            "message": f"Tool '{name}' does not exist.",
            "available": [t["name"] for t in get_advertised_tools()],
        }

    schema, func = TOOL_REGISTRY[name]

    # Validate argument presence
    query = args.get("query")
    if not query or not isinstance(query, str) or not query.strip():
        return {
            "error": "invalid_arguments",
            "message": "Missing or empty required argument 'query'.",
            "expected": {"query": "string (non-empty search phrase)"},
        }

    limit = args.get("limit", 8)
    if isinstance(limit, str) and limit.isdigit():
        limit = int(limit)
    elif not isinstance(limit, int):
        limit = 8

    limit = max(1, min(limit, 15))

    try:
        return func(query=query.strip(), limit=limit)
    except Exception as e:
        return {
            "error": "tool_execution_failed",
            "tool": name,
            "detail": str(e),
            "results": [],
        }
