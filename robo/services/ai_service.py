import logging

from google import genai
from groq import Groq

from config.settings import GEMINI_API_KEY, GEMINI_MODEL, GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL,MODEL_PRIORITY
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

ollama_service = OllamaService()

class AIService:
    PROVIDER_GROQ = "groq"
    PROVIDER_GEMINI = "gemini"
    PROVIDER_OLLAMA = "ollama"

    PRIMARY_PROVIDER = "groq"
    FALLBACK_PROVIDER = "gemini"

    def _call_provider(self, provider: str, message, history, user_info, language) -> str:
        if provider == self.PROVIDER_GROQ:
            return self._groq(message, history, user_info, language)
        if provider == self.PROVIDER_GEMINI:
            return self._gemini(message, history, user_info, language)
        if provider == self.PROVIDER_OLLAMA:
            return self._ollama(message, history, user_info, language)
        raise ValueError(f"Unknown provider: {provider}")

    def _ollama(self, message, history, user_info, language):
        logger.info(
            "ai.request | provider=%s | model=%s | context_turns=%s",
            self.PROVIDER_OLLAMA,
            OLLAMA_MODEL,
            min(len(history or []), 12),
        )
        text = ollama_service.generate(message, history, user_info, language)
        logger.debug(
            "ai.response | provider=%s | raw_received=yes",
            self.PROVIDER_OLLAMA,
        )
        return text


    def generate(self, message, history, user_info, language):
        logger.info(
            "ai.generate | start | language=%s | user_chars=%s | history_turns=%s | priority=%s",
            language,
            len(message or ""),
            len(history or []),
            MODEL_PRIORITY,
        )

        last_error: Exception | None = None

        for provider in MODEL_PRIORITY:
            provider = provider.lower()
            try:
                logger.info("ai.generate | try_provider | provider=%s", provider)
                text = self._call_provider(provider, message, history, user_info, language)
                logger.info(
                    "ai.generate | complete | provider=%s | response_chars=%s",
                    provider,
                    len(text or ""),
                )
                return text
            except Exception as e:
                last_error = e
                logger.warning(
                    "ai.generate | provider_failed | provider=%s | error=%s",
                    provider,
                    e,
                    exc_info=True,
                )
                continue

        # If we get here, all providers failed
        logger.error(
            "ai.generate | all_providers_failed | priority=%s | last_error=%s",
            MODEL_PRIORITY,
            last_error,
            exc_info=True,
        )
        if last_error:
            raise last_error
        raise RuntimeError("No providers available")

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
