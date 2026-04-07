"""Construye el fragmento de texto del antecedente según patrones_concatenacion.codigo."""

from __future__ import annotations

from app.domain.models import AntecedentOption, RuleMatch

NUMERIC_PATTERN_TO_CODIGO: dict[str, str] = {
    "1": "CD_ONLY",
    "2": "VERB_CD",
    "3": "SUBJECT_VERB_CD",
    "4": "FULL_PHRASE",
    "5": "VERB_CD_CONNECTOR_CI",
    "6": "CD_CONNECTOR_CI",
    "7": "CONNECTOR_CI",
}


def normalize_pattern_code(pattern_code: str | None) -> str:
    c = (pattern_code or "").strip() or "DEFAULT"
    if c.isdigit():
        return NUMERIC_PATTERN_TO_CODIGO.get(c, "DEFAULT")
    return c


def _strip(s: str | None) -> str:
    return (s or "").strip()


def _cd_display(c: AntecedentOption) -> str:
    if c.texto and not (c.complemento_directo or c.verbo):
        return c.texto.strip()
    return _strip(c.complemento_directo)


def _apply_rule_conector_prefix(conector: str | None, body: str) -> str:
    """Evita duplicar el conector si el cuerpo ya lo incluye.

    Paridad con ConcatenationEngine previo.
    """
    con = _strip(conector)
    b = _strip(body)
    if not con or not b:
        return b
    if b.upper().startswith(con.upper()):
        return b
    return f"{con} {b}"


class PatternFragmentBuilder:
    def build_fragment(
        self,
        *,
        rule: RuleMatch,
        candidate: AntecedentOption,
        complemento_directo_id_actual: int | None = None,
    ) -> tuple[str, int | None]:
        """
        Retorna (fragmento, antecedente_id).
        Si el fragmento es vacío pero hay vínculo lógico, puede retornar ('', id).
        """
        aid = candidate.antecedente_id
        code = normalize_pattern_code(rule.pattern_code)

        if candidate.texto and not any(
            [
                candidate.verbo,
                candidate.tipo_documento,
                candidate.complemento_directo,
                candidate.complemento_indirecto,
            ]
        ):
            raw = candidate.texto.strip()
            if not raw:
                return "", aid
            out = _apply_rule_conector_prefix(rule.conector_text, raw)
            return out, aid

        if code == "CD_ONLY":
            return self._cd_only(rule, candidate, complemento_directo_id_actual)
        if code == "VERB_CD":
            return self._verb_cd(rule, candidate)
        if code == "SUBJECT_VERB_CD":
            return self._subject_verb_cd(rule, candidate)
        if code == "FULL_PHRASE":
            return self._full_phrase(rule, candidate)
        if code == "VERB_CD_CONNECTOR_CI":
            return self._verb_cd_connector_ci(rule, candidate)
        if code == "CD_CONNECTOR_CI":
            return self._cd_connector_ci(rule, candidate)
        if code == "CONNECTOR_CI":
            return self._connector_ci(rule, candidate)
        return self._default_pattern(rule, candidate)

    def _cd_only(
        self,
        rule: RuleMatch,
        c: AntecedentOption,
        complemento_directo_id_actual: int | None,
    ) -> tuple[str, int | None]:
        if (
            complemento_directo_id_actual is not None
            and c.id_complemento_directo == complemento_directo_id_actual
        ):
            return "", c.antecedente_id
        cd = _cd_display(c)
        if not cd:
            return "", c.antecedente_id
        out = _apply_rule_conector_prefix(rule.conector_text, cd)
        return out, c.antecedente_id

    def _verb_cd(self, rule: RuleMatch, c: AntecedentOption) -> tuple[str, int | None]:
        v = _strip(c.verbo)
        cd = _cd_display(c)
        inner = f"{v} {cd}".strip()
        if not inner:
            return "", c.antecedente_id
        out = _apply_rule_conector_prefix(rule.conector_text, inner)
        return out, c.antecedente_id

    def _subject_verb_cd(self, rule: RuleMatch, c: AntecedentOption) -> tuple[str, int | None]:
        td = _strip(c.tipo_documento)
        v = _strip(c.verbo)
        cd = _cd_display(c)
        inner = f"{td} {v} {cd}".strip()
        if not inner:
            return "", c.antecedente_id
        out = _apply_rule_conector_prefix(rule.conector_text, inner)
        return out, c.antecedente_id

    def _full_phrase(
        self, rule: RuleMatch, c: AntecedentOption
    ) -> tuple[str, int | None]:  # noqa: ARG002
        td = _strip(c.tipo_documento)
        v = _strip(c.verbo)
        cd = _cd_display(c)
        con_prev = _strip(c.conector)
        ci_prev = _strip(c.complemento_indirecto)
        partes = [td, v, cd]
        body_list = [x for x in partes if x]
        body = " ".join(body_list).strip()
        if ci_prev:
            body = f"{body} {ci_prev}".strip() if body else ci_prev
        elif con_prev:
            body = f"{body} {con_prev}".strip() if body else con_prev
        return (body, c.antecedente_id)

    def _verb_cd_connector_ci(
        self, rule: RuleMatch, c: AntecedentOption
    ) -> tuple[str, int | None]:  # noqa: ARG002
        partes: list[str] = []
        if c.id_verbo:
            partes.append(_strip(c.verbo))
        cd = _cd_display(c)
        if cd:
            partes.append(cd)
        body = " ".join(partes).strip()
        if not body:
            return "", c.antecedente_id
        con_prev = _strip(c.conector)
        ci_prev = _strip(c.complemento_indirecto)
        if ci_prev:
            body = f"{body} {ci_prev}".strip()
        elif con_prev:
            body = f"{body} {con_prev}".strip()
        return (body.strip(), c.antecedente_id)

    def _cd_connector_ci(self, rule: RuleMatch, c: AntecedentOption) -> tuple[str, int | None]:
        cd = _cd_display(c)
        con = _strip(rule.conector_text)
        ci_prev = _strip(c.complemento_indirecto)
        con_prev = _strip(c.conector)
        partes: list[str] = []
        if cd:
            partes.append(cd)
        if con:
            partes.append(con)
        if ci_prev:
            partes.append(ci_prev)
        elif con_prev:
            partes.append(con_prev)
        return (" ".join(partes).strip(), c.antecedente_id)

    def _connector_ci(self, rule: RuleMatch, c: AntecedentOption) -> tuple[str, int | None]:
        con = _strip(rule.conector_text)
        con_prev = _strip(c.conector)
        ci_prev = _strip(c.complemento_indirecto)
        partes = [con] if con else []
        if ci_prev:
            partes.append(ci_prev)
        elif con_prev:
            partes.append(con_prev)
        return (" ".join(partes).strip(), c.antecedente_id)

    def _default_pattern(self, rule: RuleMatch, c: AntecedentOption) -> tuple[str, int | None]:
        cd = _cd_display(c)
        con_prev = _strip(c.conector)
        ci_prev = _strip(c.complemento_indirecto)
        out = _apply_rule_conector_prefix(rule.conector_text, cd)
        if not out:
            return "", c.antecedente_id
        if ci_prev:
            return f"{out} {ci_prev}".strip(), c.antecedente_id
        if con_prev:
            return f"{out} {con_prev}".strip(), c.antecedente_id
        return out, c.antecedente_id
