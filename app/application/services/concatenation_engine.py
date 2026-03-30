from app.domain.models import AntecedentOption, RuleMatch


class ConcatenationEngine:
    def build(
        self,
        *,
        rule: RuleMatch | None,
        selected_option: AntecedentOption | None,
    ) -> tuple[str, int | None]:
        if not rule or not selected_option:
            return "", None

        texto = selected_option.texto.strip()
        if not texto:
            return "", selected_option.antecedente_id

        if rule.conector_text and not texto.upper().startswith(rule.conector_text.upper()):
            return f"{rule.conector_text} {texto}".strip(), selected_option.antecedente_id
        return texto, selected_option.antecedente_id
