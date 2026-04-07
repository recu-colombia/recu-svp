from app.application.ports.ai import (
    ActuacionSpanSpec,
    DocumentClassificationResult,
    SelectionResult,
    SpanTripleClassification,
)
from app.application.ports.documents import ExtractedDocument
from app.application.services.antecedent_resolver import AntecedentResolver
from app.application.services.concatenation_engine import ConcatenationEngine
from app.application.services.rule_resolver import RuleResolver
from app.application.use_cases.analyze_auto_use_case import AnalyzeAutoUseCase
from app.domain.models import AllowedTriple, ComplementoDirectoCiFlags, RuleMatch, SubjectDocumentPair
from app.interfaces.http.v2.schemas import AnalyzeAutoV2Request


class FailingExtractor:
    async def extract_from_url(self, url: str) -> ExtractedDocument:  # noqa: ARG002
        raise ValueError("fallo descarga")


class OkExtractor:
    async def extract_from_url(self, url: str) -> ExtractedDocument:  # noqa: ARG002
        return ExtractedDocument(text="texto del auto", pages=1, section_used="full_text")


class EmptyRuleRepository:
    def find_applicable_rules(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return []


class OkRuleRepository:
    def find_applicable_rules(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return [
            RuleMatch(
                rule_id=1,
                pattern_code="DEFAULT",
                conector_text="CONTRA",
                cierra_ciclo=False,
                prioridad=1,
            )
        ]


class EmptyActRepo:
    def find_antecedent_candidates(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return [], False


class EmptyCatalogRepository:
    def list_subject_document_pairs(self) -> list[SubjectDocumentPair]:
        return []

    def list_allowed_triples(
        self, *, id_tipo_documento: int
    ) -> list[AllowedTriple]:  # noqa: ARG002
        return []

    def get_complemento_directo_ci_flags(
        self, id_complemento_directo: int
    ) -> ComplementoDirectoCiFlags:
        _ = id_complemento_directo
        return ComplementoDirectoCiFlags(
            permite_texto_abierto_complemento_indirecto=False,
            conector_id=None,
        )


class StubCatalogRepository:
    def list_subject_document_pairs(self) -> list[SubjectDocumentPair]:
        return [
            SubjectDocumentPair(
                pair_index=0,
                id_sujeto=10,
                id_tipo_documento=20,
                sujeto_nombre="Juzgado",
                tipo_documento_nombre="Auto",
            )
        ]

    def list_allowed_triples(
        self, *, id_tipo_documento: int
    ) -> list[AllowedTriple]:  # noqa: ARG002
        return [
            AllowedTriple(
                triple_index=0,
                id_verbo=30,
                id_complemento_directo=40,
                verbo_nombre="ORDENA",
                complemento_nombre="notificar",
            )
        ]

    def get_complemento_directo_ci_flags(
        self, id_complemento_directo: int
    ) -> ComplementoDirectoCiFlags:
        _ = id_complemento_directo
        return ComplementoDirectoCiFlags(
            permite_texto_abierto_complemento_indirecto=False,
            conector_id=None,
        )


class InvalidP1LanguageModel:
    async def classify_document_and_spans(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return DocumentClassificationResult(
            pair_index=0,
            actuacion_spans=(),
            confidence=0.0,
            rationale="failed_all_models",
        )

    async def classify_spans_closed_world(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return ()

    async def select_antecedent(self, text, candidates):  # noqa: ANN001, ANN002
        _ = (text, candidates)
        return SelectionResult(
            selected_index=None,
            confidence=0.0,
            model_path="cheap",
            reason="none",
        )


class OkPipelineLanguageModel:
    async def classify_document_and_spans(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return DocumentClassificationResult(
            pair_index=0,
            actuacion_spans=(
                ActuacionSpanSpec(
                    span_index=0,
                    texto_literal="ORDENA notificar la demanda.",
                    ordinal_resuelve="1",
                ),
            ),
            confidence=0.9,
            rationale="clear",
        )

    async def classify_spans_closed_world(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return (
            SpanTripleClassification(
                span_index=0,
                triple_index=0,
                confidence=0.88,
                rationale="ordena",
            ),
        )

    async def select_antecedent(self, text, candidates):  # noqa: ANN001, ANN002
        _ = (text, candidates)
        return SelectionResult(
            selected_index=None,
            confidence=0.8,
            model_path="cheap",
            reason="no_match",
        )


def _build_request() -> AnalyzeAutoV2Request:
    return AnalyzeAutoV2Request(
        proceso_id=1,
        actuacion_fuente_id=123,
        url_auto="https://example.com/auto.pdf",
        modo="preview",
    )


async def test_use_case_returns_error_when_extraction_fails() -> None:
    use_case = AnalyzeAutoUseCase(
        document_extractor=FailingExtractor(),
        language_model=InvalidP1LanguageModel(),
        catalog_repository=StubCatalogRepository(),
        rule_resolver=RuleResolver(EmptyRuleRepository()),
        antecedent_resolver=AntecedentResolver(EmptyActRepo()),
        concatenation_engine=ConcatenationEngine(),
    )
    result = await use_case.execute(_build_request())
    assert result.estado == "error"
    assert "Error extrayendo PDF" in result.errores[0]


async def test_use_case_partial_when_catalog_empty() -> None:
    use_case = AnalyzeAutoUseCase(
        document_extractor=OkExtractor(),
        language_model=InvalidP1LanguageModel(),
        catalog_repository=EmptyCatalogRepository(),
        rule_resolver=RuleResolver(EmptyRuleRepository()),
        antecedent_resolver=AntecedentResolver(EmptyActRepo()),
        concatenation_engine=ConcatenationEngine(),
    )
    result = await use_case.execute(_build_request())
    assert result.estado == "partial"
    assert result.sin_clasificar[0]["motivo"] == "catalogo_pares_vacio"


async def test_use_case_returns_partial_when_ai_identification_invalid() -> None:
    use_case = AnalyzeAutoUseCase(
        document_extractor=OkExtractor(),
        language_model=InvalidP1LanguageModel(),
        catalog_repository=StubCatalogRepository(),
        rule_resolver=RuleResolver(EmptyRuleRepository()),
        antecedent_resolver=AntecedentResolver(EmptyActRepo()),
        concatenation_engine=ConcatenationEngine(),
    )
    result = await use_case.execute(_build_request())
    assert result.estado == "partial"
    assert result.sin_clasificar[0]["motivo"] == "identificacion_ia_invalida"


async def test_use_case_ok_pipeline_single_span() -> None:
    use_case = AnalyzeAutoUseCase(
        document_extractor=OkExtractor(),
        language_model=OkPipelineLanguageModel(),
        catalog_repository=StubCatalogRepository(),
        rule_resolver=RuleResolver(OkRuleRepository()),
        antecedent_resolver=AntecedentResolver(EmptyActRepo()),
        concatenation_engine=ConcatenationEngine(),
    )
    result = await use_case.execute(_build_request())
    assert result.estado == "ok"
    assert len(result.actuaciones_generadas) == 1
    row = result.actuaciones_generadas[0]
    assert row.id_sujeto == 10
    assert row.id_tipo_documento == 20
    assert row.id_verbo == 30
    assert row.id_complemento_directo == 40
    assert "Juzgado mediante Auto" in row.texto_final
    assert "ORDENA: notificar" in row.texto_final


async def test_use_case_fallback_when_rule_missing_still_generates() -> None:
    use_case = AnalyzeAutoUseCase(
        document_extractor=OkExtractor(),
        language_model=OkPipelineLanguageModel(),
        catalog_repository=StubCatalogRepository(),
        rule_resolver=RuleResolver(EmptyRuleRepository()),
        antecedent_resolver=AntecedentResolver(EmptyActRepo()),
        concatenation_engine=ConcatenationEngine(),
    )
    result = await use_case.execute(_build_request())
    assert result.estado == "ok"
    assert len(result.actuaciones_generadas) == 1
    row = result.actuaciones_generadas[0]
    assert row.id_regla is None
    assert row.antecedente_id is None
    assert row.complemento_indirecto_text == ""
    assert row.estado == "clasificada_sin_regla"
    assert row.trace["rule_fallback"] is True
