import json
import logging

from app.application.ports.ai import (
    ActuacionSpanSpec,
    DocumentClassificationResult,
    LanguageModel,
    SelectionResult,
    SpanTripleClassification,
)
from app.config import get_settings
from app.domain.models import AllowedTriple, AntecedentOption, SubjectDocumentPair
from app.logging_utils import preview_for_log
from app.infrastructure.ai.openai_client_service import OpenAIClientService
from app.infrastructure.ai.prompts import (
    CLOSED_WORLD_SPANS_SYSTEM_PROMPT,
    DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT,
)
from app.infrastructure.ai.validators import (
    parse_closed_world_classifications,
    parse_document_classification,
    parse_selection_result,
)

logger = logging.getLogger(__name__)


def _antecedent_candidate_payload(index: int, c: AntecedentOption) -> dict[str, object]:
    if c.texto and not any(
        [c.verbo, c.tipo_documento, c.complemento_directo, c.complemento_indirecto]
    ):
        summary = c.texto.strip()
    else:
        parts: list[str] = []
        if c.antecedente_id is not None:
            parts.append(f"id={c.antecedente_id}")
        if c.fecha_ocurrencia:
            parts.append(str(c.fecha_ocurrencia))
        if c.tipo_documento:
            parts.append(str(c.tipo_documento))
        if c.verbo:
            parts.append(str(c.verbo))
        if c.complemento_directo:
            parts.append(str(c.complemento_directo)[:400])
        if c.complemento_indirecto:
            parts.append(str(c.complemento_indirecto)[:400])
        summary = " | ".join(parts) if parts else str(c.antecedente_id)
    return {"index": index, "antecedente_id": c.antecedente_id, "resumen": summary}


class OpenAILanguageModelRouter(LanguageModel):
    """P1: modelo fuerte primero, barato como respaldo. P2 y seleccion: barato -> fuerte."""

    def __init__(self, client: OpenAIClientService | None = None) -> None:
        self._client = client or OpenAIClientService()
        self._settings = get_settings()

    async def classify_document_and_spans(
        self,
        *,
        document_text: str,
        allowed_pairs: list[SubjectDocumentPair],
    ) -> DocumentClassificationResult:
        logger.info(
            "P1 classify_document_and_spans. text_len=%s pairs=%s",
            len(document_text),
            len(allowed_pairs),
        )
        if not allowed_pairs:
            return DocumentClassificationResult(
                pair_index=0,
                actuacion_spans=(),
                confidence=0.0,
                rationale="no_allowed_pairs",
            )

        pairs_payload = [
            {
                "pair_index": p.pair_index,
                "sujeto": p.sujeto_nombre,
                "tipo_documento": p.tipo_documento_nombre,
            }
            for p in allowed_pairs
        ]
        pairs_json = json.dumps(
            {"allowed_subject_document_pairs": pairs_payload},
            ensure_ascii=False,
        )
        user_prompt = (
            "Clasifica el siguiente auto usando solo los pair_index permitidos.\n"
            f"{pairs_json}\n\n"
            f"Texto del auto:\n{document_text}"
        )
        messages = [
            {"role": "system", "content": DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        pair_count = len(allowed_pairs)
        thresh = self._settings.selection_confidence_threshold

        for label, model in (
            ("strong", self._settings.ai_model_strong),
            ("cheap", self._settings.ai_model_cheap),
        ):
            raw = self._client.create_chat_completion(
                messages=messages,
                model=model,
                max_tokens=self._settings.ai_max_tokens,
                temperature=self._settings.ai_temperature,
            )
            if raw:
                parsed = parse_document_classification(
                    raw,
                    confidence_threshold=thresh,
                    pair_count=pair_count,
                )
                if parsed:
                    logger.info(
                        "[P1] ok label=%s pair_index=%s spans=%s conf=%.2f",
                        label,
                        parsed.pair_index,
                        len(parsed.actuacion_spans),
                        parsed.confidence,
                    )
                    return parsed
                logger.warning(
                    "[P1] json_invalid label=%s head=%s",
                    label,
                    preview_for_log(raw, max_len=400),
                )
            else:
                logger.warning("[P1] empty_response label=%s", label)

        return DocumentClassificationResult(
            pair_index=0,
            actuacion_spans=(),
            confidence=0.0,
            rationale="failed_all_models",
        )

    async def classify_spans_closed_world(
        self,
        *,
        document_context_line: str,
        spans: tuple[ActuacionSpanSpec, ...],
        allowed_triples: list[AllowedTriple],
    ) -> tuple[SpanTripleClassification, ...]:
        logger.info(
            "P2 classify_spans_closed_world. spans=%s triples=%s",
            len(spans),
            len(allowed_triples),
        )
        if not spans or not allowed_triples:
            return ()

        triples_payload = [
            {
                "triple_index": t.triple_index,
                "verbo": t.verbo_nombre,
                "complemento_directo": t.complemento_nombre,
            }
            for t in allowed_triples
        ]
        spans_payload = [
            {
                "span_index": s.span_index,
                "texto_literal": s.texto_literal,
                "ordinal_resuelve": s.ordinal_resuelve,
            }
            for s in spans
        ]
        user_prompt = json.dumps(
            {
                "document_context": document_context_line,
                "allowed_triples": triples_payload,
                "spans": spans_payload,
            },
            ensure_ascii=False,
        )
        messages = [
            {"role": "system", "content": CLOSED_WORLD_SPANS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        span_indices = {s.span_index for s in spans}
        triple_count = len(allowed_triples)
        thresh = self._settings.selection_confidence_threshold

        for label, model in (
            ("cheap", self._settings.ai_model_cheap),
            ("strong", self._settings.ai_model_strong),
        ):
            raw = self._client.create_chat_completion(
                messages=messages,
                model=model,
                max_tokens=self._settings.ai_max_tokens,
                temperature=self._settings.ai_temperature,
            )
            if raw:
                parsed = parse_closed_world_classifications(
                    raw,
                    confidence_threshold=thresh,
                    span_indices=span_indices,
                    triple_count=triple_count,
                )
                if parsed:
                    logger.info("[P2] ok label=%s clasificaciones=%s", label, len(parsed))
                    return parsed
                logger.warning(
                    "[P2] json_invalid label=%s head=%s",
                    label,
                    preview_for_log(raw, max_len=400),
                )
            else:
                logger.warning("[P2] empty_response label=%s", label)

        return ()

    async def select_antecedent(
        self,
        text: str,
        candidates: list[AntecedentOption],
    ) -> SelectionResult:
        logger.info(
            "[antecedente] candidates=%s texto=%s",
            len(candidates),
            preview_for_log(text, max_len=500),
        )
        if not candidates:
            logger.warning("No hay candidatas para seleccion de antecedente.")
            return SelectionResult(
                selected_index=None,
                confidence=0.0,
                model_path="cheap",
                reason="no_candidates",
            )

        compact_candidates = [
            _antecedent_candidate_payload(i, c) for i, c in enumerate(candidates)
        ]
        messages = [
            {"role": "system", "content": SELECTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Selecciona la mejor opcion por coherencia juridica para este auto y "
                    f"responde SOLO JSON.\nTexto auto:\n{text}\nCandidatas:\n{compact_candidates}"
                ),
            },
        ]
        cheap_response = self._client.create_chat_completion(
            messages=messages,
            model=self._settings.ai_model_cheap,
            max_tokens=self._settings.ai_max_tokens,
            temperature=self._settings.ai_temperature,
        )
        if cheap_response:
            parsed = parse_selection_result(
                cheap_response,
                confidence_threshold=self._settings.selection_confidence_threshold,
                candidates_count=len(candidates),
                model_path="cheap",
            )
            if parsed:
                return parsed
            logger.warning("Seleccion cheap invalida; activando fallback strong.")
        else:
            logger.warning("Modelo cheap no devolvio respuesta para seleccion.")

        strong_response = self._client.create_chat_completion(
            messages=messages,
            model=self._settings.ai_model_strong,
            max_tokens=self._settings.ai_max_tokens,
            temperature=self._settings.ai_temperature,
        )
        if strong_response:
            parsed = parse_selection_result(
                strong_response,
                confidence_threshold=self._settings.selection_confidence_threshold,
                candidates_count=len(candidates),
                model_path="cheap->strong",
            )
            if parsed:
                return parsed
            logger.warning("Seleccion strong invalida.")
        else:
            logger.warning("Modelo strong no devolvio respuesta para seleccion.")

        return SelectionResult(
            selected_index=None,
            confidence=0.0,
            model_path="cheap->strong",
            reason="p3_parse_or_models_failed",
        )
