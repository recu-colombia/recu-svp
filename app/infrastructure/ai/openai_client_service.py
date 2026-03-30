"""Servicio de comunicacion con OpenAI (estilo legacy)."""

import logging
from typing import Any
import importlib

from app.config import get_settings
from app.infrastructure.ai.console_pretty import print_ia_request_block, print_ia_response_block
from app.logging_utils import preview_for_log

logger = logging.getLogger(__name__)


class OpenAIClientService:
    """Cliente OpenAI inicializado con api_key y base_url."""

    def __init__(self) -> None:
        settings = get_settings()
        try:
            openai_module = importlib.import_module("openai")
            self._client = openai_module.OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                timeout=settings.ai_timeout,
            )
            logger.info(
                "OpenAI client inicializado. base_url=%s timeout=%s",
                settings.openai_base_url,
                settings.ai_timeout,
            )
        except Exception:
            self._client = None
            logger.exception("No se pudo inicializar cliente OpenAI.")

    def create_chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str | None:
        try:
            if self._client is None:
                logger.warning("OpenAI client no disponible; no se puede generar completion.")
                return None
            model_clean = (model or "").strip()
            settings = get_settings()
            logger.info(
                "[IA] request model=%s max_tokens=%s temp=%s messages=%s",
                model_clean,
                max_tokens,
                temperature,
                len(messages),
            )
            print_ia_request_block(
                model=model_clean,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
            if settings.ia_console_pretty:
                logger.debug("[IA] request_messages %s", self._build_messages_preview(messages))
            else:
                logger.info("[IA] request_messages %s", self._build_messages_preview(messages))
            response: Any = self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                body = content or ""
                logger.info(
                    "[IA] response_ok model=%s chars=%s",
                    model_clean,
                    len(body),
                )
                print_ia_response_block(model=model_clean, body=body)
                if settings.ia_console_pretty:
                    logger.debug("[IA] response_preview %s", preview_for_log(body, max_len=2800))
                else:
                    logger.info("[IA] response_preview %s", preview_for_log(body, max_len=2800))
                return content
            logger.warning("[IA] response_empty_choices model=%s", model_clean)
            return None
        except Exception:
            logger.exception("[IA] request_error model=%s", (model or "").strip())
            return None

    def _build_messages_preview(self, messages: list[dict[str, str]]) -> str:
        compact_parts: list[str] = []
        for msg in messages:
            role = (msg.get("role") or "?").strip()
            raw = msg.get("content") or ""
            compact_parts.append(
                f"{role}[len={len(raw)}]={preview_for_log(raw, max_len=450)}"
            )
        return " || ".join(compact_parts)
