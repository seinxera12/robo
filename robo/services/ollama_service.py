import logging
from typing import List, Tuple, Dict, Any

import requests

from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL

    def generate(
        self,
        message: str,
        history: List[Tuple[str, str]],
        user_info: Dict[str, Any] | None,
        language: str,
    ) -> str:
        """
        Simple, non-streaming Ollama chat call.

        Adapts (message, history, user_info, language) into Ollama's /api/chat format.
        """
        logger.info(
            "ollama.generate | start | model=%s | language=%s | user_chars=%s | history_turns=%s",
            self.model,
            language,
            len(message or ""),
            len(history or []),
        )

        # Build Ollama-style messages: conversation as alternating user/assistant
        messages: list[dict[str, str]] = [{"role": "system", "content": "You are a helpful assistant."}]
        for u, a in history[-12:]:
            messages.append({"role": "user", "content": u})
            if a:
                messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": message})

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            logger.error("ollama.generate | request_failed | %s", e, exc_info=True)
            raise

        data = resp.json()
        # Ollama typically returns {"message": {"role": "...", "content": "..."}, ...}
        content = (
            (data.get("message") or {}).get("content")
            or data.get("response")
            or ""
        ).strip()

        logger.info(
            "ollama.generate | complete | model=%s | response_chars=%s",
            self.model,
            len(content),
        )
        return content

    


        


        