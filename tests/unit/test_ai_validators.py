import json

from app.infrastructure.ai.validators import (
    parse_closed_world_classifications,
    parse_document_classification,
)


def test_parse_document_classification_ok() -> None:
    payload = json.dumps(
        {
            "pair_index": 1,
            "confidence": 0.85,
            "rationale": "ok",
            "actuacion_spans": [{"span_index": 0, "texto_literal": "Inciso uno del fallo."}],
        }
    )
    r = parse_document_classification(payload, confidence_threshold=0.5, pair_count=3)
    assert r is not None
    assert r.pair_index == 1
    assert len(r.actuacion_spans) == 1


def test_parse_document_classification_rejects_bad_pair_index() -> None:
    payload = json.dumps(
        {
            "pair_index": 9,
            "confidence": 0.85,
            "rationale": "ok",
            "actuacion_spans": [{"span_index": 0, "texto_literal": "x" * 10}],
        }
    )
    assert parse_document_classification(payload, confidence_threshold=0.5, pair_count=2) is None


def test_parse_closed_world_requires_all_spans() -> None:
    payload = json.dumps(
        {
            "clasificaciones": [
                {"span_index": 0, "triple_index": 0, "confidence": 0.9, "rationale": "a"},
            ]
        }
    )
    r = parse_closed_world_classifications(
        payload,
        confidence_threshold=0.5,
        span_indices={0, 1},
        triple_count=2,
    )
    assert r is None
