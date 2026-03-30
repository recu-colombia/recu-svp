import json

from app.application.ports.ai import ActuacionSpanSpec
from app.domain.models import AllowedTriple, AntecedentOption, SubjectDocumentPair
from app.infrastructure.ai.openai_router import OpenAILanguageModelRouter


class FakeOpenAIClientService:
    def __init__(self, responses: list[str | None]) -> None:
        self._responses = responses

    def create_chat_completion(self, **kwargs) -> str | None:  # noqa: ANN003
        _ = kwargs
        if not self._responses:
            return None
        return self._responses.pop(0)


def _p1_valid_json() -> str:
    return json.dumps(
        {
            "pair_index": 0,
            "confidence": 0.92,
            "rationale": "Se identifica juzgado y auto.",
            "actuacion_spans": [
                {"span_index": 0, "texto_literal": "ORDENA notificar.", "ordinal_resuelve": "1"}
            ],
        }
    )


def _p2_valid_json() -> str:
    return json.dumps(
        {
            "clasificaciones": [
                {
                    "span_index": 0,
                    "triple_index": 0,
                    "confidence": 0.9,
                    "rationale": "Coincide con ORDENAR/notificar.",
                }
            ]
        }
    )


async def test_classify_document_fallback_strong_then_cheap() -> None:
    client = FakeOpenAIClientService(
        responses=[
            '{"invalid": true}',
            _p1_valid_json(),
        ]
    )
    router = OpenAILanguageModelRouter(client=client)
    pairs = [
        SubjectDocumentPair(
            pair_index=0,
            id_sujeto=1,
            id_tipo_documento=2,
            sujeto_nombre="S1",
            tipo_documento_nombre="D1",
        )
    ]

    result = await router.classify_document_and_spans(document_text="auto...", allowed_pairs=pairs)
    assert result.pair_index == 0
    assert len(result.actuacion_spans) == 1
    assert result.actuacion_spans[0].texto_literal.startswith("ORDENA")


async def test_classify_spans_cheap_then_strong() -> None:
    client = FakeOpenAIClientService(
        responses=[
            '{"clasificaciones": []}',
            _p2_valid_json(),
        ]
    )
    router = OpenAILanguageModelRouter(client=client)

    spans = (ActuacionSpanSpec(span_index=0, texto_literal="ORDENA notificar.", ordinal_resuelve="1"),)
    triples = [
        AllowedTriple(
            triple_index=0,
            id_verbo=10,
            id_complemento_directo=20,
            verbo_nombre="ORDENA",
            complemento_nombre="notificar",
        )
    ]

    result = await router.classify_spans_closed_world(
        document_context_line="S1 mediante D1.",
        spans=spans,
        allowed_triples=triples,
    )
    assert len(result) == 1
    assert result[0].triple_index == 0


async def test_select_antecedent_fallback_path() -> None:
    client = FakeOpenAIClientService(
        responses=[
            '{"selected_index": 99, "confidence": 0.9, "reason":"bad_index"}',
            '{"selected_index": 0, "confidence": 0.91, "reason":"best"}',
        ]
    )
    router = OpenAILanguageModelRouter(client=client)
    candidates = [AntecedentOption(antecedente_id=1, texto="CI", source_regla_id=10)]

    result = await router.select_antecedent("texto", candidates)
    assert result.selected_index == 0
    assert result.model_path == "cheap->strong"


async def test_select_antecedent_failure_defaults_controlled() -> None:
    client = FakeOpenAIClientService(responses=[None, None])
    router = OpenAILanguageModelRouter(client=client)
    candidates = [AntecedentOption(antecedente_id=1, texto="CI", source_regla_id=10)]

    result = await router.select_antecedent("texto", candidates)
    assert result.selected_index == 0
    assert result.model_path == "cheap->strong"
    assert result.reason == "fallback_default_selection"
