import logging

from app.application.ports.ai import DocumentClassificationResult, LanguageModel
from app.logging_utils import preview_for_log
from app.application.ports.documents import DocumentExtractor
from app.application.ports.repositories import CatalogRepository
from app.application.services.antecedent_resolver import AntecedentResolver
from app.application.services.concatenation_engine import ConcatenationEngine
from app.application.services.rule_resolver import RuleResolver
from app.domain.models import AllowedTriple, GeneratedActuation, RuleMatch, SubjectDocumentPair
from app.interfaces.http.v2.schemas import ActuacionGeneradaDTO, AnalyzeAutoV2Request, AnalyzeAutoV2Response

logger = logging.getLogger(__name__)


class AnalyzeAutoUseCase:
    def __init__(
        self,
        *,
        document_extractor: DocumentExtractor,
        language_model: LanguageModel,
        catalog_repository: CatalogRepository,
        rule_resolver: RuleResolver,
        antecedent_resolver: AntecedentResolver,
        concatenation_engine: ConcatenationEngine,
    ) -> None:
        self._document_extractor = document_extractor
        self._language_model = language_model
        self._catalog_repository = catalog_repository
        self._rule_resolver = rule_resolver
        self._antecedent_resolver = antecedent_resolver
        self._concatenation_engine = concatenation_engine

    async def execute(self, request: AnalyzeAutoV2Request) -> AnalyzeAutoV2Response:
        logger.info(
            "AnalyzeAuto iniciado. proceso_id=%s actuacion_fuente_id=%s",
            request.proceso_id,
            request.actuacion_fuente_id,
        )
        try:
            extracted = await self._document_extractor.extract_from_url(request.url_auto)
        except Exception as exc:
            logger.exception("Fallo extraccion PDF para actuacion_fuente_id=%s", request.actuacion_fuente_id)
            return AnalyzeAutoV2Response(
                estado="error",
                errores=[f"Error extrayendo PDF: {exc}"],
                sin_clasificar=[
                    {
                        "motivo": "fallo_extraccion_pdf",
                        "actuacion_fuente_id": request.actuacion_fuente_id,
                    }
                ],
            )

        allowed_pairs = self._catalog_repository.list_subject_document_pairs()
        if not allowed_pairs:
            logger.warning("No hay pares sujeto-documento en catalogo.")
            return AnalyzeAutoV2Response(
                estado="partial",
                errores=["No hay pares sujeto-documento configurados en la base SVP."],
                sin_clasificar=[
                    {
                        "motivo": "catalogo_pares_vacio",
                        "actuacion_fuente_id": request.actuacion_fuente_id,
                    }
                ],
            )

        p1 = await self._language_model.classify_document_and_spans(
            document_text=extracted.text,
            allowed_pairs=allowed_pairs,
        )
        logger.info(
            "[use_case] P1 pair_index=%s spans=%s conf=%.3f rationale=%s",
            p1.pair_index,
            len(p1.actuacion_spans),
            p1.confidence,
            preview_for_log(p1.rationale, max_len=400),
        )

        if self._p1_failed(p1, allowed_pairs):
            return AnalyzeAutoV2Response(
                estado="partial",
                errores=["La IA no entrego clasificacion valida del documento y sus incisos."],
                sin_clasificar=[
                    {
                        "motivo": "identificacion_ia_invalida",
                        "actuacion_fuente_id": request.actuacion_fuente_id,
                        "rationale": p1.rationale,
                    }
                ],
            )

        selected_pair = self._pair_by_index(allowed_pairs, p1.pair_index)
        if selected_pair is None:
            return AnalyzeAutoV2Response(
                estado="partial",
                errores=["pair_index de P1 no coincide con el catalogo."],
                sin_clasificar=[
                    {"motivo": "pair_index_invalido", "actuacion_fuente_id": request.actuacion_fuente_id}
                ],
            )

        triples = self._catalog_repository.list_allowed_triples(
            id_tipo_documento=selected_pair.id_tipo_documento,
        )
        if not triples:
            logger.warning(
                "Sin triples verbo-CD para tipo_documento=%s",
                selected_pair.id_tipo_documento,
            )
            return AnalyzeAutoV2Response(
                estado="partial",
                errores=["No hay relaciones verbo/complemento_directo para el tipo de documento elegido."],
                sin_clasificar=[
                    {
                        "motivo": "universo_triples_vacio",
                        "actuacion_fuente_id": request.actuacion_fuente_id,
                    }
                ],
            )

        document_context_line = (
            f"{selected_pair.sujeto_nombre} mediante {selected_pair.tipo_documento_nombre}."
        )
        p2 = await self._language_model.classify_spans_closed_world(
            document_context_line=document_context_line,
            spans=p1.actuacion_spans,
            allowed_triples=triples,
        )
        if not p2:
            return AnalyzeAutoV2Response(
                estado="partial",
                errores=["La IA no clasifico los incisos dentro del universo permitido."],
                sin_clasificar=[
                    {
                        "motivo": "clasificacion_span_ia_invalida",
                        "actuacion_fuente_id": request.actuacion_fuente_id,
                    }
                ],
            )

        choice_by_span = {c.span_index: c for c in p2}
        actuaciones: list[ActuacionGeneradaDTO] = []
        sin_clasificar: list[dict[str, str | int | float]] = []
        errores: list[str] = []

        for span in p1.actuacion_spans:
            choice = choice_by_span.get(span.span_index)
            if choice is None:
                sin_clasificar.append(
                    {
                        "motivo": "span_sin_clasificacion_p2",
                        "actuacion_fuente_id": request.actuacion_fuente_id,
                        "span_index": span.span_index,
                    }
                )
                continue

            triple = self._triple_by_index(triples, choice.triple_index)
            if triple is None:
                sin_clasificar.append(
                    {
                        "motivo": "triple_index_fuera_rango",
                        "span_index": span.span_index,
                        "actuacion_fuente_id": request.actuacion_fuente_id,
                    }
                )
                continue

            rules = self._rule_resolver.resolve(
                tipo_documento_id=selected_pair.id_tipo_documento,
                verbo_id=triple.id_verbo,
                complemento_directo_id=triple.id_complemento_directo,
            )
            top_rule = rules[0] if rules else None
            if not top_rule:
                logger.warning(
                    "Fallback sin encadenamiento para span=%s (verbo=%s, cd=%s): sin regla aplicable.",
                    span.span_index,
                    triple.id_verbo,
                    triple.id_complemento_directo,
                )
                errores.append(
                    f"Sin regla para span {span.span_index} (verbo={triple.id_verbo}, cd={triple.id_complemento_directo}); aplicada actuacion base sin encadenamiento."
                )
                selection_model_path = "rule_fallback"
                selection_reason = "sin_regla_aplicable"
                selection_confidence = choice.confidence
                ci_text = ""
                antecedente_id = None
                candidates_count = 0
                truncated_flag = False
                p3_invocado = False
                antecedente_search_skipped = False
            else:
                antecedente_search_skipped = not self._antecedent_search_defined(top_rule)
                candidates, truncated_flag = self._antecedent_resolver.resolve(
                    proceso_id=request.proceso_id,
                    actuacion_fuente_id=request.actuacion_fuente_id,
                    rule=top_rule,
                    reference_date=request.fecha_ocurrencia_referencia,
                )
                candidates_count = len(candidates)
                selection_text = f"{document_context_line}\n{span.texto_literal}"
                selected = None
                p3_invocado = False
                if candidates_count == 0:
                    selection_model_path = "no_antecedent_candidates"
                    selection_reason = "candidatos_antecedente=0"
                    selection_confidence = choice.confidence
                elif candidates_count == 1:
                    selection_model_path = "p3_skipped_single_candidate"
                    selection_reason = "unico_candidato"
                    selection_confidence = choice.confidence
                    selected = candidates[0]
                else:
                    p3_invocado = True
                    selection = await self._language_model.select_antecedent(selection_text, candidates)
                    selection_model_path = selection.model_path
                    selection_reason = selection.reason
                    selection_confidence = selection.confidence
                    if selection.selected_index is not None and 0 <= selection.selected_index < len(candidates):
                        selected = candidates[selection.selected_index]

                ci_text, antecedente_id = self._concatenation_engine.build(
                    rule=top_rule,
                    selected_option=selected,
                    complemento_directo_id_actual=triple.id_complemento_directo,
                )
            texto_final = self._build_texto_final_svp(
                sujeto_nombre=selected_pair.sujeto_nombre,
                tipo_documento_nombre=selected_pair.tipo_documento_nombre,
                verbo_nombre=triple.verbo_nombre,
                complemento_directo_nombre=triple.complemento_nombre,
                complemento_indirecto_text=ci_text,
            )

            trace: dict[str, str | int | float | bool | None] = {
                "p1_rationale": p1.rationale,
                "p1_confidence": p1.confidence,
                "p2_rationale": choice.rationale,
                "p2_confidence": choice.confidence,
                "p2_model_path": "cheap_or_strong",
                "span_index": span.span_index,
                "triple_index": choice.triple_index,
                "model_path": selection_model_path,
                "selected_candidate_reason": selection_reason,
                "rule_id": top_rule.rule_id if top_rule else None,
                "pattern_code": top_rule.pattern_code if top_rule else None,
                "section_used": extracted.section_used,
                "rule_fallback": top_rule is None,
                "candidatos_antecedente": candidates_count if top_rule else 0,
                "p3_invocado": p3_invocado if top_rule else False,
                "antecedente_search_skipped": antecedente_search_skipped if top_rule else False,
                "filtro_fecha_aplicado": request.fecha_ocurrencia_referencia is not None,
                "candidatos_truncados": truncated_flag if top_rule else False,
            }

            generated = GeneratedActuation(
                actuacion_fuente_id=request.actuacion_fuente_id,
                id_sujeto=selected_pair.id_sujeto,
                id_tipo_documento=selected_pair.id_tipo_documento,
                id_verbo=triple.id_verbo,
                id_complemento_directo=triple.id_complemento_directo,
                regla_id=top_rule.rule_id if top_rule else None,
                antecedente_id=antecedente_id,
                complemento_indirecto_text=ci_text,
                texto_final=texto_final,
                estado="clasificada_con_regla" if top_rule else "clasificada_sin_regla",
                confianza_ia=min(p1.confidence, choice.confidence, selection_confidence),
                trace=trace,
            )
            actuaciones.append(
                ActuacionGeneradaDTO(
                    actuacion_fuente_id=generated.actuacion_fuente_id,
                    id_sujeto=generated.id_sujeto,
                    id_tipo_documento=generated.id_tipo_documento,
                    id_verbo=generated.id_verbo,
                    id_complemento_directo=generated.id_complemento_directo,
                    id_regla=generated.regla_id,
                    antecedente_id=generated.antecedente_id,
                    complemento_indirecto_text=generated.complemento_indirecto_text,
                    texto_final=generated.texto_final,
                    estado=generated.estado,
                    confianza_ia=generated.confianza_ia,
                    trace=generated.trace,
                )
            )

        if not actuaciones:
            return AnalyzeAutoV2Response(
                estado="partial",
                errores=errores or ["Ningun inciso pudo clasificarse con regla aplicable."],
                sin_clasificar=sin_clasificar,
            )

        return AnalyzeAutoV2Response(
            estado="ok",
            actuaciones_generadas=actuaciones,
            errores=errores,
            sin_clasificar=sin_clasificar,
        )

    @staticmethod
    def _antecedent_search_defined(rule: RuleMatch) -> bool:
        return any(
            [
                rule.id_buscar_antecedente_verbo,
                rule.id_buscar_antecedente_tipo_documento,
                rule.id_buscar_antecedente_complemento_directo,
                rule.buscar_antecedente_por_complemento_texto,
            ]
        )

    @staticmethod
    def _p1_failed(
        p1: DocumentClassificationResult,
        allowed_pairs: list[SubjectDocumentPair],
    ) -> bool:
        if p1.confidence <= 0:
            return True
        if not p1.actuacion_spans:
            return True
        if p1.rationale == "failed_all_models":
            return True
        if p1.pair_index < 0 or p1.pair_index >= len(allowed_pairs):
            return True
        return False

    @staticmethod
    def _pair_by_index(
        allowed_pairs: list[SubjectDocumentPair],
        pair_index: int,
    ) -> SubjectDocumentPair | None:
        for p in allowed_pairs:
            if p.pair_index == pair_index:
                return p
        return None

    @staticmethod
    def _triple_by_index(triples: list[AllowedTriple], triple_index: int) -> AllowedTriple | None:
        for t in triples:
            if t.triple_index == triple_index:
                return t
        return None

    @staticmethod
    def _build_texto_final_svp(
        *,
        sujeto_nombre: str,
        tipo_documento_nombre: str,
        verbo_nombre: str,
        complemento_directo_nombre: str,
        complemento_indirecto_text: str,
    ) -> str:
        """Texto legible alineado a SVP: sujeto mediante documento; predicado; CI del motor."""
        head = f"{sujeto_nombre.strip()} mediante {tipo_documento_nombre.strip()}".strip()
        pred = f"{verbo_nombre.strip()}: {complemento_directo_nombre.strip()}".strip()
        parts = [f"{head}.", pred]
        if complemento_indirecto_text.strip():
            parts.append(complemento_indirecto_text.strip())
        return " ".join(parts)
