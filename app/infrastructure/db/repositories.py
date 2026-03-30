import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.application.ports.repositories import ActuacionRepository, CatalogRepository, RuleRepository
from app.config import get_settings
from app.domain.models import AllowedTriple, AntecedentOption, RuleMatch, SubjectDocumentPair

logger = logging.getLogger(__name__)


class PostgresRuleRepository(RuleRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._schema = get_settings().db_schema

    def find_applicable_rules(
        self,
        *,
        tipo_documento_id: int | None,
        verbo_id: int | None,
        complemento_directo_id: int | None,
    ) -> list[RuleMatch]:
        query = text(
            f"""
            SELECT
              rg.id AS id,
              COALESCE(rg.id_patron_concatenacion::text, 'DEFAULT') AS pattern_code,
              tc.nombre AS conector_text,
              rg.cierra_ciclo AS cierra_ciclo,
              rg.prioridad AS prioridad
            FROM {self._schema}.reglas_gramaticales_encadenamiento rg
            LEFT JOIN {self._schema}.tipos_conectores tc
              ON tc.id = rg.id_conector
            WHERE rg.activo = TRUE
              AND (:tipo_documento_id IS NULL OR rg.id_disparador_tipo_documento IS NULL
                   OR rg.id_disparador_tipo_documento = :tipo_documento_id)
              AND (:verbo_id IS NULL OR rg.id_disparador_verbo IS NULL
                   OR rg.id_disparador_verbo = :verbo_id)
              AND (
                 (:complemento_directo_id IS NULL AND rg.id_disparador_complemento_directo IS NULL)
                 OR rg.id_disparador_complemento_directo IS NULL
                 OR rg.id_disparador_complemento_directo = :complemento_directo_id
              )
            ORDER BY rg.prioridad ASC, rg.id ASC
            LIMIT 25
            """
        )
        with self._engine.connect() as conn:
            try:
                rows = list(
                    conn.execute(
                    query,
                    {
                        "tipo_documento_id": tipo_documento_id,
                        "verbo_id": verbo_id,
                        "complemento_directo_id": complemento_directo_id,
                    },
                    ).mappings()
                )
                results: list[RuleMatch] = []
                for row in rows:
                    try:
                        results.append(
                            RuleMatch(
                                rule_id=int(row["id"]),
                                pattern_code=str(row.get("pattern_code") or "DEFAULT"),
                                conector_text=row.get("conector_text"),
                                cierra_ciclo=bool(row.get("cierra_ciclo", False)),
                                # Si prioridad viene NULL, no descartamos la regla.
                                prioridad=int(row.get("prioridad") or 9999),
                            )
                        )
                    except Exception:
                        logger.exception(
                            "Fila de regla invalida y omitida. row=%s tipo_doc=%s verbo=%s cd=%s",
                            dict(row),
                            tipo_documento_id,
                            verbo_id,
                            complemento_directo_id,
                        )
                logger.info(
                    "Reglas aplicables encontradas=%s (tipo_doc=%s verbo=%s cd=%s)",
                    len(results),
                    tipo_documento_id,
                    verbo_id,
                    complemento_directo_id,
                )
                return results
            except Exception:
                logger.exception(
                    "Error consultando reglas aplicables. tipo_doc=%s verbo=%s cd=%s",
                    tipo_documento_id,
                    verbo_id,
                    complemento_directo_id,
                )
                return []


class PostgresActuacionRepository(ActuacionRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._schema = get_settings().db_schema

    def find_antecedent_candidates(self, *, proceso_id: int, rule: RuleMatch) -> list[AntecedentOption]:
        query = text(
            f"""
            SELECT id, COALESCE(complemento_indirecto_text, complemento_directo_text, '') AS texto
            FROM {self._schema}.actuaciones
            WHERE proceso_id = :proceso_id
            ORDER BY id DESC
            LIMIT 10
            """
        )
        with self._engine.connect() as conn:
            try:
                rows = conn.execute(query, {"proceso_id": proceso_id}).mappings()
                return [
                    AntecedentOption(
                        antecedente_id=row["id"],
                        texto=(row["texto"] or "").strip(),
                        source_regla_id=rule.rule_id,
                        score=0.0,
                    )
                    for row in rows
                ]
            except Exception:
                return []


class PostgresCatalogRepository(CatalogRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._schema = get_settings().db_schema

    def list_subject_document_pairs(self) -> list[SubjectDocumentPair]:
        query = text(
            f"""
            SELECT
              ts.id AS id_sujeto,
              td.id AS id_tipo_documento,
              ts.nombre AS sujeto_nombre,
              td.nombre AS tipo_documento_nombre
            FROM {self._schema}.relacion_sujeto_documento rsd
            JOIN {self._schema}.tipos_sujetos ts
              ON ts.id = rsd.id_sujeto AND ts.activo = TRUE
            JOIN {self._schema}.tipos_documentos td
              ON td.id = rsd.id_tipo_documento AND td.activo = TRUE
            ORDER BY ts.id, td.id
            """
        )
        with self._engine.connect() as conn:
            try:
                rows = list(conn.execute(query).mappings())
            except Exception:
                return []
        return [
            SubjectDocumentPair(
                pair_index=i,
                id_sujeto=int(row["id_sujeto"]),
                id_tipo_documento=int(row["id_tipo_documento"]),
                sujeto_nombre=str(row["sujeto_nombre"] or ""),
                tipo_documento_nombre=str(row["tipo_documento_nombre"] or ""),
            )
            for i, row in enumerate(rows)
        ]

    def list_allowed_triples(self, *, id_tipo_documento: int) -> list[AllowedTriple]:
        query = text(
            f"""
            SELECT DISTINCT
              rdv.id_tipo_verbo AS id_verbo,
              rvc.id_complemento AS id_complemento_directo,
              tv.nombre AS verbo_nombre,
              tcd.nombre AS complemento_nombre
            FROM {self._schema}.relacion_documento_verbo rdv
            JOIN {self._schema}.relacion_verbo_complemento_directo rvc
              ON rvc.id_verbo = rdv.id_tipo_verbo
            JOIN {self._schema}.tipos_verbos tv
              ON tv.id = rdv.id_tipo_verbo AND tv.activo = TRUE
            JOIN {self._schema}.tipos_complementos_directos tcd
              ON tcd.id = rvc.id_complemento
            WHERE rdv.id_tipo_documento = :tid
            ORDER BY id_verbo, id_complemento_directo
            """
        )
        with self._engine.connect() as conn:
            try:
                rows = list(conn.execute(query, {"tid": id_tipo_documento}).mappings())
            except Exception:
                return []
        return [
            AllowedTriple(
                triple_index=i,
                id_verbo=int(row["id_verbo"]),
                id_complemento_directo=int(row["id_complemento_directo"]),
                verbo_nombre=str(row["verbo_nombre"] or ""),
                complemento_nombre=str(row["complemento_nombre"] or ""),
            )
            for i, row in enumerate(rows)
        ]
