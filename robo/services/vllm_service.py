import logging
from typing import List, Tuple, Dict, Any

import requests

from config.settings import VLLM_URL, VLLM_MODEL

logger = logging.getLogger(__name__)


class VLLMService:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or VLLM_URL).rstrip("/")
        self.model = model or VLLM_MODEL

    def generate(
        self,
        message: str,
        history: List[Tuple[str, str]],
        user_info: Dict[str, Any] | None,
        language: str,
    ) -> str:
        logger.info(
            "vllm.generate | start | model=%s | language=%s | user_chars=%s | history_turns=%s",
            self.model,
            language,
            len(message or ""),
            len(history or []),
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        for u, a in history[-12:]:
            messages.append({"role": "user", "content": u})
            if a:
                messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": message})

        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stream": False,
        }

        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            logger.error("vllm.generate | request_failed | %s", e, exc_info=True)
            raise

        data = resp.json()
        # vLLM returns OpenAI-compatible format:
        # {"choices": [{"message": {"role": "assistant", "content": "..."}}]}
        content = (
            (data.get("choices") or [{}])[0]
            .get("message", {})
            .get("content") or ""
        ).strip()

        logger.info(
            "vllm.generate | complete | model=%s | response_chars=%s",
            self.model,
            len(content),
        )
        return content