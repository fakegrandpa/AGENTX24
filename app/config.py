import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from workspace root if present
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# Agent Loop Budgets & Limits (P6 / BUILD1.md decisions)
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "8"))
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "12"))
TOOL_TIMEOUT = float(os.getenv("TOOL_TIMEOUT", "15.0"))
WALL_CLOCK = float(os.getenv("WALL_CLOCK", "120.0"))
TOOL_RETRIES = int(os.getenv("TOOL_RETRIES", "1"))
LLM_RETRIES = int(os.getenv("LLM_RETRIES", "2"))

# Optional Provider API Keys
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "").strip()
EPO_OPS_KEY = os.getenv("EPO_OPS_KEY", "").strip()
EPO_OPS_SECRET = os.getenv("EPO_OPS_SECRET", "").strip()


def get_enabled_providers() -> dict[str, list[str]]:
    """Returns mapping of tool name to active/available provider backends."""
    providers: dict[str, list[str]] = {
        "news_search": ["Google News RSS"],
        "research_search": ["OpenAlex", "arXiv Atom"],
        "web_search": ["DuckDuckGo", "Wikipedia API"],
        "patent_search": [],
    }

    if NEWSDATA_API_KEY:
        providers["news_search"].append("NewsData.io")
    if SEMANTIC_SCHOLAR_API_KEY:
        providers["research_search"].append("Semantic Scholar")
    if EPO_OPS_KEY and EPO_OPS_SECRET:
        providers["patent_search"].append("EPO OPS")

    return providers


def print_config_summary() -> None:
    """CLI diagnostic output for config verification."""
    print("=== AGENTX24 Configuration ===")
    print(f"Gemini API Key Configured : {'YES (set)' if GEMINI_API_KEY else 'NO (unconfigured)'}")
    print(f"Resolved Gemini Model     : {GEMINI_MODEL}")
    print(f"Loop Budgets              : Max Iterations={MAX_ITERATIONS}, Max Tool Calls={MAX_TOOL_CALLS}, Wall Clock={WALL_CLOCK}s")
    print(f"Tool Settings             : Timeout={TOOL_TIMEOUT}s, Retries={TOOL_RETRIES}")
    print("Enabled Tool Providers    :")
    for tool, provs in get_enabled_providers().items():
        status = ", ".join(provs) if provs else "INACTIVE (no credentials)"
        print(f"  - {tool:16}: {status}")
    print("==============================")


if __name__ == "__main__":
    print_config_summary()
