from app.application.services.rule_resolver import RuleResolver
from app.domain.models import RuleMatch


class FakeRuleRepository:
    def find_applicable_rules(
        self,
        *,
        tipo_documento_id: int | None,
        verbo_id: int | None,
        complemento_directo_id: int | None,
    ) -> list[RuleMatch]:
        _ = (tipo_documento_id, verbo_id, complemento_directo_id)
        return [
            RuleMatch(
                rule_id=1,
                pattern_code="4",
                conector_text="CON",
                cierra_ciclo=False,
                prioridad=1,
            )
        ]


def test_rule_resolver_returns_rules() -> None:
    resolver = RuleResolver(FakeRuleRepository())
    rules = resolver.resolve(tipo_documento_id=4, verbo_id=12, complemento_directo_id=33)
    assert len(rules) == 1
    assert rules[0].rule_id == 1
