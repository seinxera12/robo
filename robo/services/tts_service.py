import logging
import os
import torch

logger = logging.getLogger(__name__)

# ── Device selection ──────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info("tts.init | device=%s", DEVICE)

# ── Kokoro (primary) ──────────────────────────────────────────────────────────
try:
    from kokoro import KPipeline
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False

KOKORO_PIPELINES = {}

if KOKORO_AVAILABLE:
    try:
        # English pipeline — lang_code='a' covers American English
        KOKORO_PIPELINES["en"] = KPipeline(lang_code="a", device=DEVICE)
        logger.info("tts.init | Kokoro pipeline loaded | lang=en | device=%s", DEVICE)
    except TypeError:
        # Older kokoro versions don't accept a device kwarg — fall back gracefully
        try:
            KOKORO_PIPELINES["en"] = KPipeline(lang_code="a")
            logger.warning(
                "tts.init | Kokoro loaded WITHOUT device kwarg (upgrade kokoro for GPU support) | lang=en"
            )
        except Exception as e:
            logger.warning("tts.init | Kokoro English load failed | %s", e, exc_info=True)
    except Exception as e:
        logger.warning("tts.init | Kokoro English load failed | %s", e, exc_info=True)

    try:
        # Japanese pipeline
        KOKORO_PIPELINES["ja"] = KPipeline(lang_code="j", device=DEVICE)
        logger.info("tts.init | Kokoro pipeline loaded | lang=ja | device=%s", DEVICE)
    except TypeError:
        try:
            KOKORO_PIPELINES["ja"] = KPipeline(lang_code="j")
            logger.warning(
                "tts.init | Kokoro loaded WITHOUT device kwarg (upgrade kokoro for GPU support) | lang=ja"
            )
        except Exception as e:
            logger.warning("tts.init | Kokoro Japanese load failed | %s", e, exc_info=True)
    except Exception as e:
        logger.warning("tts.init | Kokoro Japanese load failed | %s", e, exc_info=True)

# ── Piper (secondary fallback) ────────────────────────────────────────────────
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

PIPER_VOICES = {}

if PIPER_AVAILABLE:
    try:
        if os.path.exists("en_US-amy-medium.onnx"):
            PIPER_VOICES["en"] = PiperVoice.load("en_US-amy-medium.onnx")
            logger.info("tts.init | Piper voice loaded | lang=en | path=en_US-amy-medium.onnx")
        elif os.path.exists("en_US/voice.onnx"):
            PIPER_VOICES["en"] = PiperVoice.load("en_US/voice.onnx")
            logger.info("tts.init | Piper voice loaded | lang=en | path=en_US/voice.onnx")

        if os.path.exists("ja_JP-haruka-medium.onnx"):
            PIPER_VOICES["ja"] = PiperVoice.load("ja_JP-haruka-medium.onnx")
            logger.info("tts.init | Piper voice loaded | lang=ja | path=ja_JP-haruka-medium.onnx")
        elif os.path.exists("ja_JP/voice.onnx"):
            PIPER_VOICES["ja"] = PiperVoice.load("ja_JP/voice.onnx")
            logger.info("tts.init | Piper voice loaded | lang=ja | path=ja_JP/voice.onnx")

    except Exception as e:
        logger.warning("tts.init | Piper load failed | %s", e, exc_info=True)
        PIPER_VOICES = {}


# ── Availability check (called from main_window.__init__) ─────────────────────
def check_tts_availability():
    available_methods = []

    if KOKORO_AVAILABLE and KOKORO_PIPELINES:
        langs = ", ".join(KOKORO_PIPELINES.keys())
        available_methods.append(f"Kokoro ({langs}) [{DEVICE.upper()}]")

    if PIPER_AVAILABLE and PIPER_VOICES:
        available_methods.append("Piper")

    try:
        import gtts
        available_methods.append("gTTS")
    except ImportError:
        pass

    try:
        import pyttsx3
        available_methods.append("pyttsx3")
    except ImportError:
        pass

    logger.info(
        "tts.availability | backends=%s",
        ", ".join(available_methods) if available_methods else "None",
    )