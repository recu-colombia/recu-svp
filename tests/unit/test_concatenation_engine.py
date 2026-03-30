from app.application.services.concatenation_engine import ConcatenationEngine
from app.domain.models import AntecedentOption, RuleMatch


def test_concatenation_adds_conector_when_missing() -> None:
    engine = ConcatenationEngine()
    rule = RuleMatch(
        rule_id=80,
        pattern_code="VERB_CD_CONNECTOR_CI",
        conector_text="CONTRA",
        cierra_ciclo=False,
        prioridad=1,
    )
    option = AntecedentOption(
        antecedente_id=12,
        texto="EL AUTO DEL 10 DE MAYO",
        source_regla_id=80,
    )
    texto, antecedente_id = engine.build(rule=rule, selected_option=option)
    assert texto == "CONTRA EL AUTO DEL 10 DE MAYO"
    assert antecedente_id == 12


def test_concatenation_keeps_existing_conector() -> None:
    engine = ConcatenationEngine()
    rule = RuleMatch(
        rule_id=81,
        pattern_code="CD_CONNECTOR_CI",
        conector_text="CONTRA",
        cierra_ciclo=False,
        prioridad=1,
    )
    option = AntecedentOption(
        antecedente_id=13,
        texto="CONTRA EL AUTO DEL 10 DE MAYO",
        source_regla_id=81,
    )
    texto, antecedente_id = engine.build(rule=rule, selected_option=option)
    assert texto == "CONTRA EL AUTO DEL 10 DE MAYO"
    assert antecedente_id == 13
