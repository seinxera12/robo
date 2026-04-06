import logging

from PyQt6.QtCore import QThread

from workers.base_signals import WorkerSignals
from services.ai_service import AIService

logger = logging.getLogger(__name__)


class AIWorker(QThread):

    def __init__(self, message, history, user_info, language):
        super().__init__()
        self.signals = WorkerSignals()
        self.service = AIService()

        self.message = message
        self.history = history
        self.user_info = user_info
        self.language = language

    def run(self):
        logger.info(
            "ai_worker | thread_start | language=%s | msg_chars=%s | history_turns=%s",
            self.language,
            len(self.message or ""),
            len(self.history or []),
        )

        try:
            result = self.service.generate(
                self.message,
                self.history,
                self.user_info,
                self.language,
            )
            logger.info(
                "ai_worker | success | response_chars=%s",
                len(result or ""),
            )
            self.signals.result.emit(result)

        except Exception as e:
            logger.error("ai_worker | error | %s", e, exc_info=True)
            self.signals.error.emit(str(e))

        finally:
            logger.debug("ai_worker | thread_finish")
            self.signals.finished.emit()
