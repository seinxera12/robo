import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Conversation state manager.

    - Stores structured messages in-memory
    - Persists every message append to JSONL (Option A)
    - Provides helper views for current AI layer (recent user/assistant pairs)
    """

    def __init__(
        self,
        *,
        max_turns_for_context: int = 12,
        persist: bool = True,
        session_id: str | None = None,
    ):
        import json
        import os
        import uuid
        from datetime import datetime, timezone

        self._json = json
        self._os = os
        self._uuid = uuid
        self._datetime = datetime
        self._timezone = timezone

        self.max_turns_for_context = max_turns_for_context
        self.persist = persist

        self.session_id = session_id or self._uuid.uuid4().hex
        self.messages: list[dict] = []

        self._path = None
        if self.persist:
            base_dir = self._os.path.dirname(self._os.path.dirname(self._os.path.abspath(__file__)))
            conv_dir = self._os.path.join(base_dir, "data", "conversations")
            self._os.makedirs(conv_dir, exist_ok=True)
            self._path = self._os.path.join(conv_dir, f"{self.session_id}.jsonl")

        logger.info(
            "conversation.init | session_id=%s | persist=%s | path=%s | max_turns_for_context=%s",
            self.session_id,
            self.persist,
            self._path,
            self.max_turns_for_context,
        )

    # ---------------- public API ---------------- #

    def add_user(self, content: str, *, language: str | None = None, meta: dict | None = None) -> None:
        self._add_message("user", content, language=language, meta=meta)

    def add_assistant(
        self,
        content: str,
        *,
        language: str | None = None,
        meta: dict | None = None,
    ) -> None:
        self._add_message("assistant", content, language=language, meta=meta)

    def add_system(self, content: str, *, meta: dict | None = None) -> None:
        self._add_message("system", content, meta=meta)

    def clear(self, *, new_session: bool = True) -> None:
        n = len(self.messages)
        self.messages.clear()
        logger.info("conversation.clear | removed_messages=%s | new_session=%s", n, new_session)
        if new_session:
            self._start_new_session()

    def get_recent_pairs(self, limit_turns: int | None = None) -> list[tuple[str, str]]:
        """
        Return [(user_text, assistant_text), ...] for the most recent turns.
        This keeps compatibility with the current AI layer which expects pairs.
        """
        limit_turns = limit_turns or self.max_turns_for_context
        pairs: list[tuple[str, str]] = []

        last_assistant: str | None = None
        # Traverse newest → oldest so we can stop early.
        for msg in reversed(self.messages):
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "assistant" and last_assistant is None:
                last_assistant = content
            elif role == "user" and last_assistant is not None:
                pairs.append((content, last_assistant))
                last_assistant = None
                if len(pairs) >= limit_turns:
                    break

        pairs.reverse()
        logger.debug("conversation.get_recent_pairs | limit_turns=%s | returned=%s", limit_turns, len(pairs))
        return pairs

    # ---------------- internals ---------------- #

    def _start_new_session(self) -> None:
        # Only used when persistence is enabled.
        old = self.session_id
        self.session_id = self._uuid.uuid4().hex
        if self.persist:
            base_dir = self._os.path.dirname(self._os.path.dirname(self._os.path.abspath(__file__)))
            conv_dir = self._os.path.join(base_dir, "data", "conversations")
            self._os.makedirs(conv_dir, exist_ok=True)
            self._path = self._os.path.join(conv_dir, f"{self.session_id}.jsonl")
        logger.info("conversation.new_session | old_session_id=%s | new_session_id=%s | path=%s", old, self.session_id, self._path)

    def _add_message(self, role: str, content: str, *, language: str | None = None, meta: dict | None = None) -> None:
        if content is None:
            content = ""
        msg = {
            "id": self._uuid.uuid4().hex,
            "ts": self._datetime.now(self._timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        if language:
            msg["language"] = language
        if meta:
            msg["meta"] = meta

        self.messages.append(msg)
        logger.debug(
            "conversation.add_message | session_id=%s | role=%s | chars=%s | total_messages=%s",
            self.session_id,
            role,
            len(content),
            len(self.messages),
        )

        if self.persist and self._path:
            self._append_jsonl(msg)

    def _append_jsonl(self, msg: dict) -> None:
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(self._json.dumps(msg, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("conversation.persist_failed | session_id=%s | path=%s | error=%s", self.session_id, self._path, e, exc_info=True)
