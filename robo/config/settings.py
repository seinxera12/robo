import os
from dotenv import load_dotenv

load_dotenv()

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # or your preferred model

# Provider priority: tuple from highest to lowest
# Allowed values: "ollama", "groq", "gemini"
MODEL_PRIORITY = os.getenv(
    "MODEL_PRIORITY",
    "groq,gemini,ollama",  # current behavior; you can later use "ollama,groq,gemini"
).split(",")
MODEL_PRIORITY = [p.strip().lower() for p in MODEL_PRIORITY if p.strip()]

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY  = os.getenv('GROQ_API_KEY')

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set")

# Models
GEMINI_MODEL = 'gemini-2.5-flash'
GROQ_MODEL = 'llama-3.1-8b-instant'

# Audio
SAMPLE_RATE = 16000
RECORD_DURATION = 5

# Languages
SUPPORTED_LANGUAGES = {
                        "en": "English",
                        "jp": "Japanese",
                        }

