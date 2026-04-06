import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    def __init__(self):
        self.history = []

    def add(self, user, assistant):
        self.history.append((user, assistant))
        logger.debug(
            "conversation.add | total_turns=%s | user_chars=%s | assistant_chars=%s",
            len(self.history),
            len(user or ""),
            len(assistant or ""),
        )

    def get_recent(self, limit=12):
        recent = self.history[-limit:]
        logger.debug("conversation.get_recent | limit=%s | returned=%s", limit, len(recent))
        return recent

    def clear(self):
        n = len(self.history)
        self.history.clear()
        logger.info("conversation.clear | removed_turns=%s", n)
