from app.application.ports.repositories import RuleRepository
from app.domain.models import RuleMatch


class RuleResolver:
    def __init__(self, rule_repository: RuleRepository) -> None:
        self._rule_repository = rule_repository

    def resolve(
        self,
        *,
        tipo_documento_id: int | None,
        verbo_id: int | None,
        complemento_directo_id: int | None,
    ) -> list[RuleMatch]:
        return self._rule_repository.find_applicable_rules(
            tipo_documento_id=tipo_documento_id,
            verbo_id=verbo_id,
            complemento_directo_id=complemento_directo_id,
        )
