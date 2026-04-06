import logging
import os

logger = logging.getLogger(__name__)

# Piper setup
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

PIPER_VOICES = {}

if PIPER_AVAILABLE:
    try:
        # English
        if os.path.exists("en_US-amy-medium.onnx"):
            PIPER_VOICES["en"] = PiperVoice.load("en_US-amy-medium.onnx")
            logger.info("tts.init | Piper voice loaded | lang=en | path=en_US-amy-medium.onnx")
        elif os.path.exists("en_US/voice.onnx"):
            PIPER_VOICES["en"] = PiperVoice.load("en_US/voice.onnx")
            logger.info("tts.init | Piper voice loaded | lang=en | path=en_US/voice.onnx")

        # Japanese
        if os.path.exists("ja_JP-haruka-medium.onnx"):
            PIPER_VOICES["ja"] = PiperVoice.load("ja_JP-haruka-medium.onnx")
            logger.info("tts.init | Piper voice loaded | lang=ja | path=ja_JP-haruka-medium.onnx")
        elif os.path.exists("ja_JP/voice.onnx"):
            PIPER_VOICES["ja"] = PiperVoice.load("ja_JP/voice.onnx")
            logger.info("tts.init | Piper voice loaded | lang=ja | path=ja_JP/voice.onnx")

    except Exception as e:
        logger.warning("tts.init | Piper load failed | %s", e, exc_info=True)
        PIPER_VOICES = {}


def check_tts_availability():
    available_methods = []

    # Piper
    if PIPER_AVAILABLE and PIPER_VOICES:
        available_methods.append("Piper")

    # gTTS
    try:
        import gtts
        available_methods.append("gTTS")
    except ImportError:
        pass

    # pyttsx3
    try:
        import pyttsx3
        available_methods.append("pyttsx3")
    except ImportError:
        pass

    logger.info(
        "tts.availability | backends=%s",
        ", ".join(available_methods) if available_methods else "None",
    )
