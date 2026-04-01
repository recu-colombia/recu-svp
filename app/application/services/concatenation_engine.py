from app.application.services.pattern_fragment_builder import PatternFragmentBuilder
from app.domain.models import AntecedentOption, RuleMatch


class ConcatenationEngine:
    def __init__(self, pattern_builder: PatternFragmentBuilder | None = None) -> None:
        self._pattern_builder = pattern_builder or PatternFragmentBuilder()

    def build(
        self,
        *,
        rule: RuleMatch | None,
        selected_option: AntecedentOption | None,
        complemento_directo_id_actual: int | None = None,
    ) -> tuple[str, int | None]:
        if not rule or not selected_option:
            return "", None

        texto, aid = self._pattern_builder.build_fragment(
            rule=rule,
            candidate=selected_option,
            complemento_directo_id_actual=complemento_directo_id_actual,
        )
        texto = texto.strip()
        if not texto:
            return "", aid
        return texto, aid
