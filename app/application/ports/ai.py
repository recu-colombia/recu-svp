from dataclasses import dataclass
from typing import Protocol

from app.domain.models import AllowedTriple, AntecedentOption, SubjectDocumentPair


@dataclass(frozen=True)
class ActuacionSpanSpec:
    span_index: int
    texto_literal: str
    ordinal_resuelve: str | None = None


@dataclass(frozen=True)
class DocumentClassificationResult:
    """Salida del Prompt 1: par válido por índice + incisos literales del auto."""

    pair_index: int
    actuacion_spans: tuple[ActuacionSpanSpec, ...]
    confidence: float
    rationale: str


@dataclass(frozen=True)
class SpanTripleClassification:
    """Una fila del Prompt 2 (universo cerrado por triple_index)."""

    span_index: int
    triple_index: int
    confidence: float
    rationale: str


@dataclass(frozen=True)
class SelectionResult:
    selected_index: int | None
    confidence: float
    model_path: str
    reason: str


class LanguageModel(Protocol):
    async def classify_document_and_spans(
        self,
        *,
        document_text: str,
        allowed_pairs: list[SubjectDocumentPair],
    ) -> DocumentClassificationResult: ...

    async def classify_spans_closed_world(
        self,
        *,
        document_context_line: str,
        spans: tuple[ActuacionSpanSpec, ...],
        allowed_triples: list[AllowedTriple],
    ) -> tuple[SpanTripleClassification, ...]: ...

    async def select_antecedent(
        self, text: str, candidates: list[AntecedentOption]
    ) -> SelectionResult: ...
