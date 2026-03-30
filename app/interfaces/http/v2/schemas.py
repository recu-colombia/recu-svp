from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeAutoV2Request(BaseModel):
    proceso_id: int
    actuacion_fuente_id: int
    url_auto: str
    modo: Literal["preview", "commit"] = "preview"
    frases_contexto: list[str] = Field(default_factory=list)


class ActuacionGeneradaDTO(BaseModel):
    actuacion_fuente_id: int
    id_sujeto: int | None
    id_tipo_documento: int | None
    id_verbo: int | None
    id_complemento_directo: int | None
    id_regla: int | None
    antecedente_id: int | None
    complemento_indirecto_text: str
    texto_final: str
    estado: str
    confianza_ia: float
    trace: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AnalyzeAutoV2Response(BaseModel):
    estado: Literal["ok", "partial", "error"]
    actuaciones_generadas: list[ActuacionGeneradaDTO] = Field(default_factory=list)
    sin_clasificar: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    errores: list[str] = Field(default_factory=list)
