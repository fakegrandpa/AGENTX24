import time
import logging
from typing import Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_RETRIES

logger = logging.getLogger(__name__)

# System prompt enforcing autonomous investigation, citation formatting, and safe output
SYSTEM_INSTRUCTION = """You are an autonomous research and competitor intelligence AI agent.
Your objective is to thoroughly investigate the user's target (company, competitor, research topic, technology, or industry) by dynamically selecting information tools, observing evidence, and synthesizing a prioritized intelligence report.

OPERATING PRINCIPLES:
1. DYNAMIC TOOL SELECTION: Select tools step-by-step based on what you need to discover next. Do not execute a pre-scripted sequence. If initial findings point to a specific angle (e.g. breakthroughs, competition, market news), follow that thread.
2. EVIDENCE INTEGRITY: Every factual claim must be backed by evidence returned from your tools.
3. CITATION SYNTAX: Cite every piece of evidence using its exact evidence ID format [E1], [E2], [E3]. Never fabricate evidence IDs.
4. PRIORITIZATION: In your final output, categorize signals by strategic importance:
   - HIGH PRIORITY: Critical breakthroughs, major competitor shifts, decisive developments with strong evidence.
   - IMPORTANT: Notable updates, incremental research advancements, partnership/product updates.
   - EMERGING / WATCH: Early-stage signals, nascent research trends, watch items.
5. HONEST LIMITATIONS: If information on a topic is unavailable or a tool returns no results, explicitly state the limitation. Do NOT fabricate findings.
6. NO RAW REASONING LEAKS: Provide clean, objective findings.
"""


class ToolCall(BaseModel):
    id: str | None = None
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    tool_calls: list[ToolCall] = Field(default_factory=list)
    text: str = ""
    finish_reason: str | None = None
    raw_content: Any = None


def get_client() -> genai.Client | None:
    """Returns an initialized GenAI client or None if no API key is set."""
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def resolve_model() -> tuple[str, bool, str]:
    """Preflight check to resolve model name.
    Returns: (resolved_model_name, is_ready, status_message)
    """
    if not GEMINI_API_KEY:
        return ("unconfigured", False, "GEMINI_API_KEY is not set in environment or .env")

    client = get_client()
    if not client:
        return ("unconfigured", False, "Failed to initialize Gemini client")

    target_model = GEMINI_MODEL
    try:
        # Check available models
        available_models = []
        for m in client.models.list():
            name = getattr(m, "name", "")
            # names often come as models/gemini-...
            clean_name = name.replace("models/", "")
            available_models.append(clean_name)

        if target_model in available_models or f"models/{target_model}" in [getattr(m, "name", "") for m in client.models.list()]:
            return (target_model, True, f"Model '{target_model}' verified and active")

        # If exact match not in list, check for matching flash model
        flash_models = [m for m in available_models if "flash" in m and "preview" not in m]
        if flash_models:
            chosen = flash_models[0]
            logger.info("Target model '%s' not found, falling back to '%s'", target_model, chosen)
            return (chosen, True, f"Substituted available flash model: {chosen}")

        # Fallback to configured target
        return (target_model, True, f"Using configured model: {target_model}")
    except Exception as e:
        logger.warning("Model list preflight failed: %s; proceeding with '%s'", e, target_model)
        return (target_model, True, f"Preflight error: {e}, attempting default {target_model}")


def propose_next_step(
    contents: list[Any],
    tools_schema: list[dict[str, Any]] | None = None,
    system_instruction: str = SYSTEM_INSTRUCTION,
) -> LLMResponse:
    """Proposes the next action (tool calls or final synthesis) given conversation history."""
    client = get_client()
    if not client:
        raise RuntimeError("Cannot execute LLM step: GEMINI_API_KEY is not configured.")

    model_name, is_ready, msg = resolve_model()
    if not is_ready:
        raise RuntimeError(f"Gemini model not ready: {msg}")

    # Build tools config
    config_params: dict[str, Any] = {
        "system_instruction": system_instruction,
        "temperature": 0.2,
    }

    if tools_schema:
        declarations = []
        for s in tools_schema:
            fd = types.FunctionDeclaration(
                name=s["name"],
                description=s.get("description", ""),
                parameters_json_schema=s.get("parameters", {}),
            )
            declarations.append(fd)
        config_params["tools"] = [types.Tool(function_declarations=declarations)]

    config = types.GenerateContentConfig(**config_params)

    # Execute with retries
    last_error: Exception | None = None
    for attempt in range(LLM_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )

            tool_calls: list[ToolCall] = []
            text_parts: list[str] = []

            if response.candidates:
                candidate = response.candidates[0]
                content = candidate.content
                if content and content.parts:
                    for part in content.parts:
                        if part.function_call:
                            fc = part.function_call
                            call_id = getattr(fc, "id", None) or f"call_{len(tool_calls)+1}"
                            args = dict(fc.args) if fc.args else {}
                            tool_calls.append(ToolCall(id=call_id, name=fc.name, args=args))
                        elif part.text:
                            # Verify not internal thought
                            if not getattr(part, "thought", False):
                                text_parts.append(part.text)

                finish_reason = str(candidate.finish_reason) if candidate.finish_reason else None
                return LLMResponse(
                    tool_calls=tool_calls,
                    text="".join(text_parts).strip(),
                    finish_reason=finish_reason,
                    raw_content=content,
                )

            return LLMResponse(text=response.text or "")
        except APIError as e:
            last_error = e
            logger.warning("Gemini API error (attempt %d/%d): %s", attempt + 1, LLM_RETRIES + 1, e)
            if attempt < LLM_RETRIES:
                time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            last_error = e
            logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, LLM_RETRIES + 1, e)
            if attempt < LLM_RETRIES:
                time.sleep(1.0 * (attempt + 1))

    raise RuntimeError(f"All LLM retries exhausted: {last_error}")


if __name__ == "__main__":
    print("=== Testing app.llm ===")
    model, ready, note = resolve_model()
    print(f"Model Status: {model} (Ready: {ready})")
    print(f"Note        : {note}")

    if ready and GEMINI_API_KEY:
        try:
            print("Sending test completion to Gemini...")
            res = propose_next_step(contents=["Respond with: 'AGENTX24 LLM adapter online'"])
            print(f"Response    : {res.text}")
        except Exception as ex:
            print(f"Completion test failed: {ex}")
    else:
        print("Skipping live completion (no GEMINI_API_KEY set).")
    print("========================")
