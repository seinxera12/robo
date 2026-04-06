import logging

from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        code = "ja" if lang == "ja" else "en"
        logger.info(
            "language.detect | ok | detected_raw=%s | normalized=%s | text_chars=%s",
            lang,
            code,
            len(text or ""),
        )
        return code
    except LangDetectException as e:
        logger.info(
            "language.detect | fallback_en | reason=LangDetectException | %s",
            e,
        )
        return "en"
