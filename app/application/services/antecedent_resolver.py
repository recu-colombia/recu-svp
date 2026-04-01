from datetime import date

from app.application.ports.repositories import ActuacionRepository
from app.domain.models import AntecedentOption, RuleMatch


class AntecedentResolver:
    def __init__(self, actuacion_repository: ActuacionRepository) -> None:
        self._actuacion_repository = actuacion_repository

    def resolve(
        self,
        *,
        proceso_id: int,
        actuacion_fuente_id: int,
        rule: RuleMatch,
        reference_date: date | None,
    ) -> tuple[list[AntecedentOption], bool]:
        return self._actuacion_repository.find_antecedent_candidates(
            proceso_id=proceso_id,
            actuacion_fuente_id=actuacion_fuente_id,
            rule=rule,
            reference_date=reference_date,
        )
