from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubjectDocumentPair:
    """Par permitido (sujeto, tipo_documento) desde relacion_sujeto_documento."""

    pair_index: int
    id_sujeto: int
    id_tipo_documento: int
    sujeto_nombre: str
    tipo_documento_nombre: str


@dataclass(frozen=True)
class AllowedTriple:
    """Combinación cerrada (verbo, complemento_directo) válida para un tipo de documento."""

    triple_index: int
    id_verbo: int
    id_complemento_directo: int
    verbo_nombre: str
    complemento_nombre: str


@dataclass(frozen=True)
class RuleMatch:
    rule_id: int
    pattern_code: str
    conector_text: str | None
    cierra_ciclo: bool
    prioridad: int


@dataclass(frozen=True)
class AntecedentOption:
    antecedente_id: int | None
    texto: str
    source_regla_id: int
    score: float = 0.0


@dataclass(frozen=True)
class GeneratedActuation:
    actuacion_fuente_id: int
    id_sujeto: int | None
    id_tipo_documento: int | None
    id_verbo: int | None
    id_complemento_directo: int | None
    regla_id: int | None
    antecedente_id: int | None
    complemento_indirecto_text: str
    texto_final: str
    estado: str
    confianza_ia: float
    trace: dict[str, str | int | float | bool | None] = field(default_factory=dict)
