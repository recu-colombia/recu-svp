from dataclasses import dataclass, field
from datetime import date


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
    id_buscar_antecedente_verbo: int | None = None
    id_buscar_antecedente_tipo_documento: int | None = None
    id_buscar_antecedente_complemento_directo: int | None = None
    buscar_antecedente_por_complemento_texto: str | None = None


@dataclass(frozen=True)
class AntecedentOption:
    """Candidato a antecedente con snapshot de `public.actuacion` para patrones de concatenación."""

    antecedente_id: int | None
    source_regla_id: int
    id_tipo_documento: int | None = None
    tipo_documento: str | None = None
    id_verbo: int | None = None
    verbo: str | None = None
    id_complemento_directo: int | None = None
    complemento_directo: str | None = None
    id_conector: int | None = None
    conector: str | None = None
    complemento_indirecto: str | None = None
    fecha_ocurrencia: date | None = None
    score: float = 0.0
    texto: str | None = None


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
