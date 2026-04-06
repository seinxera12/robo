import os
from dotenv import load_dotenv

load_dotenv()

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

