from app.application.ports.repositories import ActuacionRepository
from app.domain.models import AntecedentOption, RuleMatch


class AntecedentResolver:
    def __init__(self, actuacion_repository: ActuacionRepository) -> None:
        self._actuacion_repository = actuacion_repository

    def resolve(self, *, proceso_id: int, rule: RuleMatch) -> list[AntecedentOption]:
        return self._actuacion_repository.find_antecedent_candidates(proceso_id=proceso_id, rule=rule)
