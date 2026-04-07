import json
import logging
from typing import Any

from google import genai
from google.genai import types as gemini_types
from groq import Groq

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    MODEL_PRIORITY,
    OLLAMA_MODEL,
    WEB_SEARCH_OUTPUT_MAX_CHARS,
    BRAVE_SEARCH_API_KEY,
    SERPER_API_KEY
)
from services.ollama_service import OllamaService
from services.brave_search import brave_web_search_compact
from services.serper_search import serper_web_search_compact


from services.web_search_tools import (
    WEB_SEARCH_TOOL_NAME,
    assistant_system_prompt_with_web_search,
    execute_web_search_tool,
    gemini_web_search_tool,
    groq_web_search_tools,
    max_web_search_tool_rounds,
)
from utils.needs_search import needs_search

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

ollama_service = OllamaService()

GROQ_HISTORY_TURNS = 12
GEMINI_HISTORY_TURNS = 6


class AIService:
    PROVIDER_GROQ = "groq"
    PROVIDER_GEMINI = "gemini"
    PROVIDER_OLLAMA = "ollama"

    PRIMARY_PROVIDER = "groq"
    FALLBACK_PROVIDER = "gemini"

    def _call_provider(self, provider: str, message, history, user_info, language) -> str:
        if provider == self.PROVIDER_GROQ:
            return self._groq_with_tools(message, history, user_info, language)
        if provider == self.PROVIDER_GEMINI:
            return self._gemini_with_tools(message, history, user_info, language)
        if provider == self.PROVIDER_OLLAMA:
            return self._ollama_with_search_augment(message, history, user_info, language)
        raise ValueError(f"Unknown provider: {provider}")

    def _ollama_plain(self, message, history, user_info, language) -> str:
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

    def _ollama_with_search_augment(self, message, history, user_info, language) -> str:
        if not needs_search(message, history, language):
            logger.info("ollama.augment | needs_search=no | path=plain")
            return self._ollama_plain(message, history, user_info, language)

        # if not BRAVE_SEARCH_API_KEY:
        #     logger.warning("ollama.augment | needs_search=yes | skipped | missing BRAVE_SEARCH_API_KEY")
        #     return self._ollama_plain(message, history, user_info, language)

        if not SERPER_API_KEY:
            logger.warning("ollama.augment | needs_search=yes | skipped | missing SERPER_API_KEY")
            return self._ollama_plain(message, history, user_info, language)

        query = (message or "").strip()
        logger.info(
            "ollama.augment | needs_search=yes | brave_query_chars=%s",
            len(query),
        )
        block = serper_web_search_compact(query)
        if not block:
            block = "No web results returned."
        if len(block) > WEB_SEARCH_OUTPUT_MAX_CHARS:
            block = block[:WEB_SEARCH_OUTPUT_MAX_CHARS].rstrip() + "…"

        augmented_message = (
            "Use the web results below if they help answer the question. "
            "Cite URLs when you use them.\n\n"
            f"[Web results]\n{block}\n\n"
            f"[User question]\n{query}"
        )
        return self._ollama_plain(augmented_message, history, user_info, language)

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

        logger.error(
            "ai.generate | all_providers_failed | priority=%s | last_error=%s",
            MODEL_PRIORITY,
            last_error,
            exc_info=True,
        )
        if last_error:
            raise last_error
        raise RuntimeError("No providers available")

    def _groq_tool_result_for_call(self, tool_name: str, arguments_raw: str | None) -> str:
        if tool_name != WEB_SEARCH_TOOL_NAME:
            return f"Unknown tool: {tool_name}. No action taken."

        try:
            parsed: Any = json.loads(arguments_raw or "{}")
        except json.JSONDecodeError:
            return (
                "Invalid tool arguments: expected a JSON object with a string "
                '\"query\" field, e.g. {\"query\": \"your search terms\"}.'
            )

        if not isinstance(parsed, dict):
            return "Invalid tool arguments: expected a JSON object with a \"query\" field."

        q = parsed.get("query", "")
        if q is None:
            q = ""
        if not isinstance(q, str):
            q = str(q)

        result = execute_web_search_tool(q)
        logger.info(
            "ai.tool | provider=%s | tool=%s | query_chars=%s | result_chars=%s",
            self.PROVIDER_GROQ,
            tool_name,
            len(q.strip()),
            len(result or ""),
        )
        return result

    def _groq_with_tools(self, message, history, user_info, language) -> str:
        logger.info(
            "ai.request | provider=%s | model=%s | context_turns=%s | tools=web_search",
            self.PROVIDER_GROQ,
            GROQ_MODEL,
            min(len(history or []), GROQ_HISTORY_TURNS),
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": assistant_system_prompt_with_web_search()},
        ]
        for u, a in history[-GROQ_HISTORY_TURNS:]:
            messages.append({"role": "user", "content": u})
            if a:
                messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": message})

        tools = groq_web_search_tools()
        max_rounds = max_web_search_tool_rounds()

        for round_i in range(max_rounds):
            logger.info("ai.groq | tool_round | round=%s | max=%s", round_i + 1, max_rounds)
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
            )
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []

            if tool_calls:
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content if msg.content else None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tc in tool_calls:
                    name = tc.function.name
                    payload = self._groq_tool_result_for_call(name, tc.function.arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": payload,
                        }
                    )
                continue

            text = (msg.content or "").strip()
            if text:
                logger.debug("ai.response | provider=%s | path=text", self.PROVIDER_GROQ)
                return text
            logger.warning("ai.groq | empty_assistant_message | round=%s", round_i + 1)
            break

        logger.warning("ai.groq | tool_rounds_exhausted | forcing_final_completion=no_tools")
        final = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
        )
        out = (final.choices[0].message.content or "").strip()
        logger.debug("ai.response | provider=%s | path=final_fallback", self.PROVIDER_GROQ)
        return out

    def _gemini_text_part(self, text: str) -> Any:
        if hasattr(gemini_types.Part, "from_text"):
            return gemini_types.Part.from_text(text=text)
        return gemini_types.Part(text=text)

    def _gemini_function_response_part(self, name: str, result_text: str) -> Any:
        if hasattr(gemini_types.Part, "from_function_response"):
            return gemini_types.Part.from_function_response(
                name=name,
                response={"result": result_text},
            )
        fr = gemini_types.FunctionResponse(name=name, response={"result": result_text})
        return gemini_types.Part(function_response=fr)

    def _gemini_tool_result(self, name: str, args: Any) -> str:
        if name != WEB_SEARCH_TOOL_NAME:
            return f"Unknown tool: {name}. No action taken."

        if isinstance(args, dict):
            q = args.get("query", "")
        else:
            q = ""
        if q is None:
            q = ""
        if not isinstance(q, str):
            q = str(q)

        result = execute_web_search_tool(q)
        logger.info(
            "ai.tool | provider=%s | tool=%s | query_chars=%s | result_chars=%s",
            self.PROVIDER_GEMINI,
            name,
            len(q.strip()),
            len(result or ""),
        )
        return result

    def _gemini_with_tools(self, message, history, user_info, language) -> str:
        logger.info(
            "ai.request | provider=%s | model=%s | context_turns=%s | tools=web_search",
            self.FALLBACK_PROVIDER,
            GEMINI_MODEL,
            min(len(history or []), GEMINI_HISTORY_TURNS),
        )

        client = genai.Client(api_key=GEMINI_API_KEY)
        tool = gemini_web_search_tool()

        try:
            config = gemini_types.GenerateContentConfig(
                system_instruction=assistant_system_prompt_with_web_search(),
                tools=[tool],
                automatic_function_calling=gemini_types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            )
        except TypeError:
            config = gemini_types.GenerateContentConfig(
                tools=[tool],
                automatic_function_calling=gemini_types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            )

        contents: list[Any] = []
        sys_text = assistant_system_prompt_with_web_search()
        if not getattr(config, "system_instruction", None):
            contents.append(
                gemini_types.Content(
                    role="user",
                    parts=[self._gemini_text_part(f"[System instructions]\n{sys_text}")],
                )
            )

        for u, a in history[-GEMINI_HISTORY_TURNS:]:
            contents.append(
                gemini_types.Content(role="user", parts=[self._gemini_text_part(u)])
            )
            if a:
                contents.append(
                    gemini_types.Content(role="model", parts=[self._gemini_text_part(a)])
                )

        contents.append(
            gemini_types.Content(
                role="user",
                parts=[self._gemini_text_part(message)],
            )
        )

        max_rounds = max_web_search_tool_rounds()

        for round_i in range(max_rounds):
            logger.info("ai.gemini | tool_round | round=%s | max=%s", round_i + 1, max_rounds)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )

            fcs = list(response.function_calls) if response.function_calls else []

            if not fcs:
                text = (response.text or "").strip()
                if text:
                    logger.debug("ai.response | provider=%s | path=text", self.FALLBACK_PROVIDER)
                    return text
                logger.warning("ai.gemini | empty_response | round=%s", round_i + 1)
                break

            cand = response.candidates[0] if response.candidates else None
            if cand and cand.content:
                contents.append(cand.content)

            resp_parts: list[Any] = []
            for fc in fcs:
                name = fc.name
                args = fc.args if getattr(fc, "args", None) is not None else {}
                if not isinstance(args, dict):
                    try:
                        args = json.loads(str(args)) if args else {}
                    except json.JSONDecodeError:
                        args = {}
                payload = self._gemini_tool_result(name, args)
                resp_parts.append(self._gemini_function_response_part(name, payload))

            contents.append(gemini_types.Content(role="tool", parts=resp_parts))

        logger.warning("ai.gemini | tool_rounds_exhausted | final_pass")
        si = getattr(config, "system_instruction", None)
        if si is not None:
            final_config = gemini_types.GenerateContentConfig(system_instruction=si)
        else:
            final_config = gemini_types.GenerateContentConfig()
        final = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=final_config,
        )
        out = (final.text or "").strip()
        logger.debug("ai.response | provider=%s | path=final_fallback", self.FALLBACK_PROVIDER)
        return out
