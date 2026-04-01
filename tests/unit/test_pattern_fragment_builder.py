from app.application.services.pattern_fragment_builder import (
    PatternFragmentBuilder,
    normalize_pattern_code,
)
from app.domain.models import AntecedentOption, RuleMatch


def test_normalize_numeric_pattern() -> None:
    assert normalize_pattern_code("6") == "CD_CONNECTOR_CI"
    assert normalize_pattern_code("FULL_PHRASE") == "FULL_PHRASE"


def test_verb_cd_pattern() -> None:
    b = PatternFragmentBuilder()
    rule = RuleMatch(
        rule_id=1,
        pattern_code="VERB_CD",
        conector_text="CONTRA",
        cierra_ciclo=False,
        prioridad=1,
    )
    c = AntecedentOption(
        antecedente_id=5,
        source_regla_id=1,
        verbo="DECRETA",
        complemento_directo="MEDIDA CAUTELAR",
    )
    frag, aid = b.build_fragment(rule=rule, candidate=c)
    assert aid == 5
    assert frag == "CONTRA DECRETA MEDIDA CAUTELAR"


def test_full_phrase_no_leading_conector() -> None:
    b = PatternFragmentBuilder()
    rule = RuleMatch(
        rule_id=2,
        pattern_code="FULL_PHRASE",
        conector_text="CONTRA",
        cierra_ciclo=False,
        prioridad=1,
    )
    c = AntecedentOption(
        antecedente_id=1,
        source_regla_id=2,
        tipo_documento="AUTO",
        verbo="NIEGA",
        complemento_directo="RECURSO",
        complemento_indirecto="POR IMPROCEDENTE",
    )
    frag, _aid = b.build_fragment(rule=rule, candidate=c)
    assert "AUTO" in frag and "NIEGA" in frag and "RECURSO" in frag
    assert "POR IMPROCEDENTE" in frag
