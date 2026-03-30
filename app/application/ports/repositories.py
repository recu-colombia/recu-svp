from typing import Protocol

from app.domain.models import AllowedTriple, AntecedentOption, RuleMatch, SubjectDocumentPair


class RuleRepository(Protocol):
    def find_applicable_rules(
        self,
        *,
        tipo_documento_id: int | None,
        verbo_id: int | None,
        complemento_directo_id: int | None,
    ) -> list[RuleMatch]: ...


class ActuacionRepository(Protocol):
    def find_antecedent_candidates(
        self,
        *,
        proceso_id: int,
        rule: RuleMatch,
    ) -> list[AntecedentOption]: ...


class CatalogRepository(Protocol):
    """Catálogo SVP: pares sujeto–documento y triples verbo–CD permitidos."""

    def list_subject_document_pairs(self) -> list[SubjectDocumentPair]: ...

    def list_allowed_triples(self, *, id_tipo_documento: int) -> list[AllowedTriple]: ...
