import logging

from google import genai
from groq import Groq

from config.settings import GEMINI_API_KEY, GEMINI_MODEL, GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)


class AIService:
    PRIMARY_PROVIDER = "groq"
    FALLBACK_PROVIDER = "gemini"

    def generate(self, message, history, user_info, language):
        logger.info(
            "ai.generate | start | language=%s | user_chars=%s | history_turns=%s",
            language,
            len(message or ""),
            len(history or []),
        )

        try:
            text = self._groq(message, history, user_info, language)
            logger.info(
                "ai.generate | complete | provider=%s | model=%s | response_chars=%s",
                self.PRIMARY_PROVIDER,
                GROQ_MODEL,
                len(text or ""),
            )
            return text
        except Exception as e:
            logger.warning(
                "ai.generate | primary_failed | provider=%s | model=%s | error=%s",
                self.PRIMARY_PROVIDER,
                GROQ_MODEL,
                e,
                exc_info=True,
            )
            text = self._gemini(message, history, user_info, language)
            logger.info(
                "ai.generate | complete | provider=%s | model=%s | response_chars=%s",
                self.FALLBACK_PROVIDER,
                GEMINI_MODEL,
                len(text or ""),
            )
            return text

    def _gemini(self, message, history, user_info, language):
        logger.info(
            "ai.request | provider=%s | model=%s | context_turns=%s",
            self.FALLBACK_PROVIDER,
            GEMINI_MODEL,
            min(len(history or []), 6),
        )

        client = genai.Client(api_key=GEMINI_API_KEY)

        context = ""
        for u, a in history[-6:]:
            context += f"User: {u}\nAssistant: {a}\n"

        prompt = f"""
        You are a helpful assistant.

        {context}

        User: {message}
        Assistant:
        """

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        logger.debug(
            "ai.response | provider=%s | raw_received=yes",
            self.FALLBACK_PROVIDER,
        )
        return response.text.strip()

    def _groq(self, message, history, user_info, language):
        logger.info(
            "ai.request | provider=%s | model=%s | context_turns=%s",
            self.PRIMARY_PROVIDER,
            GROQ_MODEL,
            min(len(history or []), 12),
        )

        messages = [{"role": "system", "content": "You are a helpful assistant."}]

        for u, a in history[-12:]:
            messages.append({"role": "user", "content": u})
            if a:
                messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": message})

        response = groq_client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL,
            temperature=0.7,
        )

        logger.debug(
            "ai.response | provider=%s | raw_received=yes",
            self.PRIMARY_PROVIDER,
        )
        return response.choices[0].message.content.strip()
