import json
from typing import Any

from app.application.ports.ai import (
    ActuacionSpanSpec,
    DocumentClassificationResult,
    SelectionResult,
    SpanTripleClassification,
)


def _strip_code_fence(payload: str) -> str:
    content = payload.strip()
    if content.startswith("```"):
        lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
        return "\n".join(lines).strip()
    return content


def parse_document_classification(
    payload: str,
    *,
    confidence_threshold: float,
    pair_count: int,
) -> DocumentClassificationResult | None:
    try:
        data: Any = json.loads(_strip_code_fence(payload))
        required_keys = {"pair_index", "confidence", "rationale", "actuacion_spans"}
        if not required_keys.issubset(set(data.keys())):
            return None
        confidence = float(data["confidence"])
        if confidence < confidence_threshold or confidence > 1:
            return None
        pair_index = int(data["pair_index"])
        if pair_index < 0 or pair_index >= pair_count:
            return None
        rationale = str(data.get("rationale", "")).strip()
        if not rationale:
            return None
        raw_spans = data.get("actuacion_spans")
        if not isinstance(raw_spans, list) or len(raw_spans) == 0:
            return None
        spans: list[ActuacionSpanSpec] = []
        seen_span_idx: set[int] = set()
        for item in raw_spans:
            if not isinstance(item, dict):
                return None
            if "span_index" not in item or "texto_literal" not in item:
                return None
            si = int(item["span_index"])
            if si in seen_span_idx:
                return None
            seen_span_idx.add(si)
            texto = str(item["texto_literal"] or "").strip()
            if len(texto) < 3:
                return None
            ord_r = item.get("ordinal_resuelve")
            ord_str = str(ord_r).strip() if ord_r is not None and str(ord_r).strip() else None
            spans.append(
                ActuacionSpanSpec(
                    span_index=si,
                    texto_literal=texto,
                    ordinal_resuelve=ord_str,
                )
            )
        spans.sort(key=lambda s: s.span_index)
        return DocumentClassificationResult(
            pair_index=pair_index,
            actuacion_spans=tuple(spans),
            confidence=confidence,
            rationale=rationale,
        )
    except Exception:
        return None


def parse_closed_world_classifications(
    payload: str,
    *,
    confidence_threshold: float,
    span_indices: set[int],
    triple_count: int,
) -> tuple[SpanTripleClassification, ...] | None:
    try:
        data: Any = json.loads(_strip_code_fence(payload))
        if "clasificaciones" not in data or not isinstance(data["clasificaciones"], list):
            return None
        raw = data["clasificaciones"]
        if len(raw) != len(span_indices):
            return None
        by_span: dict[int, SpanTripleClassification] = {}
        for item in raw:
            if not isinstance(item, dict):
                return None
            req = {"span_index", "triple_index", "confidence", "rationale"}
            if not req.issubset(set(item.keys())):
                return None
            si = int(item["span_index"])
            ti = int(item["triple_index"])
            conf = float(item["confidence"])
            rat = str(item.get("rationale", "")).strip()
            if si not in span_indices:
                return None
            if ti < 0 or ti >= triple_count:
                return None
            if conf < confidence_threshold or conf > 1:
                return None
            if not rat:
                return None
            if si in by_span:
                return None
            by_span[si] = SpanTripleClassification(
                span_index=si,
                triple_index=ti,
                confidence=conf,
                rationale=rat,
            )
        if set(by_span.keys()) != span_indices:
            return None
        ordered = tuple(by_span[i] for i in sorted(span_indices))
        return ordered
    except Exception:
        return None


def parse_selection_result(
    payload: str,
    *,
    confidence_threshold: float,
    candidates_count: int,
    model_path: str,
) -> SelectionResult | None:
    try:
        data: Any = json.loads(_strip_code_fence(payload))
        required_keys = {"selected_index", "confidence", "reason"}
        if not required_keys.issubset(set(data.keys())):
            return None
        confidence = float(data["confidence"])
        if confidence < confidence_threshold or confidence > 1:
            return None
        selected_index = _to_optional_int(data.get("selected_index"))
        if selected_index is not None and not (0 <= selected_index < candidates_count):
            return None
        reason = str(data.get("reason", "")).strip()
        if not reason:
            return None
        return SelectionResult(
            selected_index=selected_index,
            confidence=confidence,
            model_path=model_path,
            reason=reason,
        )
    except Exception:
        return None


def _to_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return int(value)
