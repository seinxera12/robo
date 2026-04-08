import os
from dotenv import load_dotenv

load_dotenv()

# LLMS
# Models


MODEL_PRIORITY = os.getenv(
    "MODEL_PRIORITY",
    "groq,gemini,ollama",  # current behavior; you can later use "ollama,groq,gemini"
).split(",")
MODEL_PRIORITY = [p.strip().lower() for p in MODEL_PRIORITY if p.strip()]

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # or your preferred model

GEMINI_MODEL = 'gemini-2.5-flash'
GROQ_MODEL = 'llama-3.1-70b-versatile'
# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY  = os.getenv('GROQ_API_KEY')

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set")


# Web Search

# Brave Web Search (optional; tool/augment code should handle missing key)
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
BRAVE_WEB_SEARCH_API_URL = os.getenv(
    "BRAVE_WEB_SEARCH_API_URL",
    "https://api.search.brave.com/res/v1/web/search",
)

# Serper Web Search
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_SEARCH_API_URL = "https://google.serper.dev/search"
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "brave")  # "brave" | "serper"

# Web search → model context limits (tool loop limits live here too)
MAX_WEB_SEARCH_TOOL_ROUNDS = int(os.getenv("MAX_WEB_SEARCH_TOOL_ROUNDS", "4"))
WEB_SEARCH_TOP_N = int(os.getenv("WEB_SEARCH_TOP_N", "5"))
WEB_SEARCH_SNIPPET_MAX_CHARS = int(os.getenv("WEB_SEARCH_SNIPPET_MAX_CHARS", "320"))
WEB_SEARCH_OUTPUT_MAX_CHARS = int(os.getenv("WEB_SEARCH_OUTPUT_MAX_CHARS", "6000"))

# Audio
SAMPLE_RATE = 16000
RECORD_DURATION = 5

# Languages
SUPPORTED_LANGUAGES = {
                        "en": "English",
                        "jp": "Japanese",
                        }

