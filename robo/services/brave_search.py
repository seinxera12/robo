"""
Brave Web Search API — fetch and format compact snippets for LLM context / tool results.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from config.settings import (
    BRAVE_SEARCH_API_KEY,
    BRAVE_WEB_SEARCH_API_URL,
    WEB_SEARCH_OUTPUT_MAX_CHARS,
    WEB_SEARCH_SNIPPET_MAX_CHARS,
    WEB_SEARCH_TOP_N,
)

logger = logging.getLogger(__name__)


def _truncate(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _format_web_results(data: dict[str, Any]) -> str:
    web = data.get("web") or {}
    results = web.get("results") or []
    if not results:
        return ""

    lines: list[str] = []
    for i, item in enumerate(results[:WEB_SEARCH_TOP_N], start=1):
        title = _truncate(str(item.get("title") or ""), 200)
        url = str(item.get("url") or "").strip()
        desc = _truncate(str(item.get("description") or ""), WEB_SEARCH_SNIPPET_MAX_CHARS)
        if not title and not url:
            continue
        block = f"{i}. {title}\n   URL: {url}\n   {desc}".rstrip()
        lines.append(block)

    out = "\n\n".join(lines)
    if len(out) > WEB_SEARCH_OUTPUT_MAX_CHARS:
        out = out[: WEB_SEARCH_OUTPUT_MAX_CHARS - 1].rstrip() + "…"
    return out


def brave_web_search_raw(query: str, *, timeout: float = 20.0) -> dict[str, Any] | None:
    """
    Call Brave Web Search API. Returns parsed JSON or None on failure.
    """
    q = (query or "").strip()
    if not q:
        return None

    if not BRAVE_SEARCH_API_KEY:
        logger.warning("brave_search | skipped | missing BRAVE_SEARCH_API_KEY")
        return None

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
    }
    params = {"q": q, "count": WEB_SEARCH_TOP_N}

    try:
        resp = requests.get(
            BRAVE_WEB_SEARCH_API_URL,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            logger.warning("brave_search | unexpected_payload | type=%s", type(data))
            return None
        return data
    except requests.RequestException as e:
        logger.warning("brave_search | request_failed | %s", e, exc_info=True)
        return None


def brave_web_search_compact(query: str) -> str:
    """
    Run a web search and return a compact string for tool results or prompt augmentation.
    On missing key, HTTP errors, or empty hits, returns an empty string (caller maps to tool message).
    """
    data = brave_web_search_raw(query)
    if not data:
        return ""

    formatted = _format_web_results(data)
    if not formatted:
        logger.info("brave_search | no_hits | query_chars=%s", len((query or "").strip()))
        return ""
    logger.info(
        "brave_search | ok | query_chars=%s | out_chars=%s",
        len((query or "").strip()),
        len(formatted),
    )
    return formatted
