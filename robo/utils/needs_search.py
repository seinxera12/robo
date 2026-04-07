"""
Heuristic: whether the latest user turn likely needs live web search (Ollama augment path).
"""

from __future__ import annotations

import re

# --- Positive signals (need search) ---

_RECENT_YEAR = re.compile(r"\b(202[4-9]|203\d)\b")

_STRONG_SEARCH_KEYWORDS = re.compile(
    r"\b("
    r"latest|breaking|just announced|just released|just launched|"
    r"today|right now|as of today|this week|this month|this year|"
    r"news|headline|update|updates|"
    r"stock price|share price|market cap|earnings|ipo|crypto price|"
    r"weather|forecast|temperature|"
    r"score|standings|fixtures|match result|who won|"
    r"election|poll|vote|referendum|"
    r"price of|how much is|how much does|cost of|"
    r"schedule|timetable|opening hours|open now|"
    r"official site|website of|where to buy|"
    r"search for|look up|google|find me|"
    r"released|launched|announced|dropped"
    r")\b",
    re.I,
)

_URL = re.compile(r"https?://\S+", re.I)

# Specific factual who/what/when that imply a real-world lookup
_FACTUAL_WH = re.compile(
    r"\b("
    r"who is the (current|new|latest|president|ceo|prime minister|head|leader|owner|founder)|"
    r"who (won|leads|beat|scored|signed|announced)|"
    r"what is the (current|latest|new|price|cost|rate|status|score|weather)|"
    r"what (happened|is happening|did .+ say|did .+ do|is the latest)|"
    r"when (is|was|will|does|did) .+ (release|launch|happen|start|end|open|close)|"
    r"where (is|can i find|to buy|to watch|to download)"
    r")",
    re.I,
)

# --- Negative signals (do NOT search) ---

_NO_SEARCH_INTENTS = re.compile(
    r"\b("
    # Identity / capability questions
    r"what (are you|is your name|can you do|do you do)|"
    r"who are you|are you (an ai|a bot|human|claude|gpt)|"
    r"your name|your purpose|how do you work|"
    # Conversational / emotional
    r"thank(s| you)|you('re| are) (great|awesome|helpful|good)|"
    r"hello|hi there|hey|good morning|good night|good evening|"
    r"how are you|how('s| is) it going|what('s| is) up|"
    r"i (love|like|hate|miss|need|feel|think|want|am)|"
    r"can you help|could you help|please help|"
    # Creative / reasoning tasks
    r"write (a|me|an)|draft|compose|generate|create|make me|"
    r"explain|summarize|summarise|translate|convert|calculate|"
    r"what (does|do) .+ mean|definition of|define|"
    r"tell me a (joke|story|fact)|"
    r"how (do|does|can|to) .+ work|"
    r"difference between|compare .+ (and|vs|versus)|"
    r"give me (an example|a list|ideas|advice|tips)"
    r")\b",
    re.I,
)

# Very short messages are almost always conversational
_MIN_SEARCH_LENGTH = 8


def _is_conversational(text: str) -> bool:
    """True if the message is clearly chitchat or a task that needs no search."""
    if _NO_SEARCH_INTENTS.search(text):
        return True
    # Single word or very short — greeting, ack, reaction
    if len(text.split()) <= 3:
        return True
    return False


def _has_strong_search_signal(text: str) -> bool:
    """True if the message clearly needs live/factual web data."""
    if _URL.search(text):
        return True
    if _RECENT_YEAR.search(text):
        return True
    if _STRONG_SEARCH_KEYWORDS.search(text):
        return True
    if _FACTUAL_WH.search(text):
        return True
    return False


def needs_search(message: str, history, language: str) -> bool:
    text = (message or "").strip()

    # Too short to meaningfully search
    if len(text) < _MIN_SEARCH_LENGTH:
        return False

    # Conversational / creative / reasoning → never search
    if _is_conversational(text):
        return False

    # Strong explicit signal → always search
    if _has_strong_search_signal(text):
        return True

    return False