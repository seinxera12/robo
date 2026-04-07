"""
Serper Web Search API — fetch and format compact snippets for LLM context / tool results.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from config.settings import (
    SERPER_API_KEY,
    SERPER_SEARCH_API_URL,
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
    """
    Serper response uses:
        data["organic"]        — list of web results
        item["link"]           — URL  (Brave uses "url")
        item["snippet"]        — description  (Brave uses "description")

    Optionally prepends a knowledgeGraph block if present.
    """
    lines: list[str] = []

    # --- Knowledge Graph (optional, prepended as result 0) ---
    kg = data.get("knowledgeGraph")
    if kg and isinstance(kg, dict):
        kg_title = _truncate(str(kg.get("title") or ""), 200)
        kg_type = _truncate(str(kg.get("type") or ""), 100)
        kg_desc = _truncate(str(kg.get("description") or ""), WEB_SEARCH_SNIPPET_MAX_CHARS)
        kg_url = str(kg.get("website") or "").strip()
        if kg_title:
            block = f"0. {kg_title} ({kg_type})\n   URL: {kg_url}\n   {kg_desc}".rstrip()
            lines.append(block)

    # --- Organic results ---
    organic = data.get("organic") or []
    if not organic and not lines:
        return ""

    for i, item in enumerate(organic[:WEB_SEARCH_TOP_N], start=1):
        title = _truncate(str(item.get("title") or ""), 200)
        url = str(item.get("link") or "").strip()       # Serper: "link"
        desc = _truncate(
            str(item.get("snippet") or ""),             # Serper: "snippet"
            WEB_SEARCH_SNIPPET_MAX_CHARS,
        )
        if not title and not url:
            continue
        block = f"{i}. {title}\n   URL: {url}\n   {desc}".rstrip()
        lines.append(block)

    if not lines:
        return ""

    out = "\n\n".join(lines)
    if len(out) > WEB_SEARCH_OUTPUT_MAX_CHARS:
        out = out[: WEB_SEARCH_OUTPUT_MAX_CHARS - 1].rstrip() + "…"
    return out


def serper_web_search_raw(query: str, *, timeout: float = 20.0) -> dict[str, Any] | None:
    """
    Call Serper Web Search API. Returns parsed JSON or None on failure.

    Differences from Brave:
        - POST instead of GET
        - Auth via X-API-KEY header (not X-Subscription-Token)
        - Body is JSON payload (not query params)
    """
    q = (query or "").strip()
    if not q:
        return None

    if not SERPER_API_KEY:
        logger.warning("serper_search | skipped | missing SERPER_API_KEY")
        return None

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": q,
        "num": WEB_SEARCH_TOP_N,
    }

    try:
        resp = requests.post(
            SERPER_SEARCH_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            logger.warning("serper_search | unexpected_payload | type=%s", type(data))
            return None
        return data
    except requests.RequestException as e:
        logger.warning("serper_search | request_failed | %s", e, exc_info=True)
        return None


def serper_web_search_compact(query: str) -> str:
    """
    Run a Serper web search and return a compact string for tool results or prompt augmentation.
    On missing key, HTTP errors, or empty hits, returns an empty string
    (caller maps to tool message).

    Drop-in replacement for brave_web_search_compact().
    """
    data = serper_web_search_raw(query)
    if not data:
        return ""

    formatted = _format_web_results(data)
    if not formatted:
        logger.info("serper_search | no_hits | query_chars=%s", len((query or "").strip()))
        return ""

    logger.info(
        "serper_search | ok | query_chars=%s | out_chars=%s",
        len((query or "").strip()),
        len(formatted),
    )
    return formatted