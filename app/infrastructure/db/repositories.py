import logging
from datetime import date

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
              COALESCE(pc.codigo, 'DEFAULT') AS pattern_code,
              tc.nombre AS conector_text,
              rg.cierra_ciclo AS cierra_ciclo,
              rg.prioridad AS prioridad,
              rg.id_buscar_antecedente_verbo AS id_buscar_antecedente_verbo,
              rg.id_buscar_antecedente_tipo_documento AS id_buscar_antecedente_tipo_documento,
              rg.id_buscar_antecedente_complemento_directo AS id_buscar_antecedente_complemento_directo,
              rg.buscar_antecedente_por_complemento_texto AS buscar_antecedente_por_complemento_texto
            FROM {self._schema}.reglas_gramaticales_encadenamiento rg
            LEFT JOIN {self._schema}.patrones_concatenacion pc
              ON pc.id = rg.id_patron_concatenacion
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
                        pct = row.get("buscar_antecedente_por_complemento_texto")
                        pct_s = str(pct).strip() if pct else None
                        if pct_s == "":
                            pct_s = None
                        results.append(
                            RuleMatch(
                                rule_id=int(row["id"]),
                                pattern_code=str(row.get("pattern_code") or "DEFAULT"),
                                conector_text=row.get("conector_text"),
                                cierra_ciclo=bool(row.get("cierra_ciclo", False)),
                                prioridad=int(row.get("prioridad") or 9999),
                                id_buscar_antecedente_verbo=row.get("id_buscar_antecedente_verbo"),
                                id_buscar_antecedente_tipo_documento=row.get(
                                    "id_buscar_antecedente_tipo_documento"
                                ),
                                id_buscar_antecedente_complemento_directo=row.get(
                                    "id_buscar_antecedente_complemento_directo"
                                ),
                                buscar_antecedente_por_complemento_texto=pct_s,
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
        self._settings = get_settings()
        self._schema = self._settings.db_schema
        self._act_table = self._settings.judicial_actuacion_table.strip()

    def find_antecedent_candidates(
        self,
        *,
        proceso_id: int,
        actuacion_fuente_id: int,
        rule: RuleMatch,
        reference_date: date | None,
    ) -> tuple[list[AntecedentOption], bool]:
        has_criteria = any(
            [
                rule.id_buscar_antecedente_verbo,
                rule.id_buscar_antecedente_tipo_documento,
                rule.id_buscar_antecedente_complemento_directo,
                rule.buscar_antecedente_por_complemento_texto,
            ]
        )
        if not has_criteria:
            return [], False

        lim = max(1, int(self._settings.max_antecedent_candidates))
        fetch_limit = lim + 1

        params: dict[str, object] = {
            "proceso_id": proceso_id,
            "exclude_id": actuacion_fuente_id,
            "fetch_limit": fetch_limit,
        }
        where_parts = [
            "a.id_proceso = :proceso_id",
            "a.id <> :exclude_id",
        ]

        if reference_date is not None:
            where_parts.append(
                "(a.fecha_ocurrencia IS NULL OR a.fecha_ocurrencia <= :ref_date)"
            )
            params["ref_date"] = reference_date

        if rule.id_buscar_antecedente_verbo:
            where_parts.append("a.id_verbo = :buscar_verbo")
            params["buscar_verbo"] = rule.id_buscar_antecedente_verbo

        if rule.id_buscar_antecedente_tipo_documento:
            where_parts.append("a.id_tipo_documento = :buscar_tdoc")
            params["buscar_tdoc"] = rule.id_buscar_antecedente_tipo_documento

        if rule.id_buscar_antecedente_complemento_directo:
            cd_id = rule.id_buscar_antecedente_complemento_directo
            params["cd_buscar_id"] = cd_id
            where_parts.append(
                f"""
                (
                  a.id_complemento_directo = :cd_buscar_id
                  OR EXISTS (
                    SELECT 1 FROM {self._schema}.tipos_complementos_directos tcd_nm
                    WHERE tcd_nm.id = :cd_buscar_id
                      AND tcd_nm.nombre IS NOT NULL
                      AND LENGTH(TRIM(tcd_nm.nombre)) > 0
                      AND (
                        POSITION(LOWER(TRIM(tcd_nm.nombre)) IN LOWER(COALESCE(a.complemento_directo, ''))) > 0
                        OR POSITION(LOWER(TRIM(tcd_nm.nombre)) IN LOWER(COALESCE(a.complemento_indirecto, ''))) > 0
                      )
                  )
                )
                """
            )

        if rule.buscar_antecedente_por_complemento_texto:
            raw = rule.buscar_antecedente_por_complemento_texto.strip()
            params["pct_sub"] = f"%{raw}%"
            where_parts.append(
                """
                (
                  COALESCE(a.complemento_directo, '') ILIKE :pct_sub
                  OR COALESCE(a.complemento_indirecto, '') ILIKE :pct_sub
                )
                """
            )

        where_sql = " AND ".join(where_parts)
        query = text(
            f"""
            SELECT
              a.id,
              a.fecha_ocurrencia,
              a.id_tipo_documento,
              a.tipo_documento,
              a.id_verbo,
              a.verbo,
              a.id_complemento_directo,
              a.complemento_directo,
              a.id_conector,
              a.conector,
              a.complemento_indirecto
            FROM {self._act_table} a
            WHERE {where_sql}
            ORDER BY a.id DESC
            LIMIT :fetch_limit
            """
        )

        with self._engine.connect() as conn:
            try:
                rows = list(conn.execute(query, params).mappings())
            except Exception:
                logger.exception(
                    "Error consultando candidatos antecedente proceso_id=%s exclude=%s",
                    proceso_id,
                    actuacion_fuente_id,
                )
                return [], False

        truncated = len(rows) > lim
        rows = rows[:lim]

        candidates = [
            AntecedentOption(
                antecedente_id=int(row["id"]),
                source_regla_id=rule.rule_id,
                fecha_ocurrencia=row.get("fecha_ocurrencia"),
                id_tipo_documento=row.get("id_tipo_documento"),
                tipo_documento=row.get("tipo_documento"),
                id_verbo=row.get("id_verbo"),
                verbo=row.get("verbo"),
                id_complemento_directo=row.get("id_complemento_directo"),
                complemento_directo=row.get("complemento_directo"),
                id_conector=row.get("id_conector"),
                conector=row.get("conector"),
                complemento_indirecto=row.get("complemento_indirecto"),
            )
            for row in rows
        ]
        return candidates, truncated


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
