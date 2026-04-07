"""
Shared web_search tool contract for Groq (OpenAI-style tools) and Gemini (FunctionDeclaration).

Also: system prompt guidance and tool-round / empty-result helpers for orchestration code.
"""

from __future__ import annotations

from config.settings import BRAVE_SEARCH_API_KEY, MAX_WEB_SEARCH_TOOL_ROUNDS, SERPER_API_KEY, SEARCH_PROVIDER

from services.brave_search import brave_web_search_compact
from services.serper_search import serper_web_search_compact

# --- Tool identity (single function name for all providers) ---

WEB_SEARCH_TOOL_NAME = "web_search"

WEB_SEARCH_TOOL_DESCRIPTION = (
    "Search the public web for current or factual information (news, sports, prices, "
    "dates, people, places) when the user needs fresh data beyond your training. "
    "Do not use for chit-chat, creative writing, or questions you can answer without up-to-date sources."
)

# One JSON Schema object reused by Groq and Gemini `parameters` / `parameters_json_schema`.
WEB_SEARCH_PARAMETERS_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "Focused search query in the user's language (keywords or a short question), "
                "without chat preamble."
            ),
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

# --- System prompt ---

BASE_ASSISTANT_SYSTEM_PROMPT = "You are a helpful assistant."

WEB_SEARCH_POLICY_SYSTEM_ADDENDUM = (
    "You have access to a web_search tool. Call it only when the user needs timely or factual "
    "information that may have changed after your knowledge cutoff or that requires verification "
    "online. If you use web results in your answer, cite the relevant URLs. If search returns "
    "no usable results, say so and answer from general knowledge when appropriate."
)


def assistant_system_prompt_with_web_search() -> str:
    """Full system message for providers that expose web_search as a tool."""
    return f"{BASE_ASSISTANT_SYSTEM_PROMPT}\n\n{WEB_SEARCH_POLICY_SYSTEM_ADDENDUM}"


# --- Groq / OpenAI-compatible tools list ---


def groq_web_search_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": WEB_SEARCH_TOOL_NAME,
                "description": WEB_SEARCH_TOOL_DESCRIPTION,
                "parameters": WEB_SEARCH_PARAMETERS_JSON_SCHEMA,
            },
        }
    ]


# --- Gemini ---


def gemini_web_search_tool():
    """Return google.genai.types.Tool for web_search (lazy import avoids import cost elsewhere)."""
    from google.genai import types

    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=WEB_SEARCH_TOOL_NAME,
                description=WEB_SEARCH_TOOL_DESCRIPTION,
                parameters_json_schema=WEB_SEARCH_PARAMETERS_JSON_SCHEMA,
            )
        ]
    )


# --- Safety / tool execution ---

TOOL_RESULT_EMPTY = "No results."

TOOL_SEARCH_UNCONFIGURED = (
    "Web search is not configured (missing BRAVE_SEARCH_API_KEY). "
    "Answer using your own knowledge and say you could not search the web."
)


def max_web_search_tool_rounds() -> int:
    """Max model↔tool iterations per user turn (orchestration should stop after this many)."""
    return MAX_WEB_SEARCH_TOOL_ROUNDS


def execute_web_search_tool(arguments_query: str) -> str:
    """
    Run Brave search from parsed tool arguments (the `query` field).
    Always returns a short string suitable as tool/content for the model.
    """
    if SEARCH_PROVIDER == "brave":

        if not BRAVE_SEARCH_API_KEY:
            return TOOL_SEARCH_UNCONFIGURED
        compact = brave_web_search_compact(q)
        if not compact:
            return TOOL_RESULT_EMPTY
        return compact
    
    if not SERPER_API_KEY:
        return TOOL_SEARCH_UNCONFIGURED


    q = (arguments_query or "").strip()
    if not q:
        return TOOL_RESULT_EMPTY

    compact = serper_web_search_compact(q)
    if not compact:
        return TOOL_RESULT_EMPTY
    return compact
