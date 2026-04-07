import logging

from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError

from app.interfaces.http.v2.dependencies import build_analyze_auto_use_case
from app.interfaces.http.v2.schemas import AnalyzeAutoV2Request, AnalyzeAutoV2Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["analyze_v2"])


@router.post("/analyze-auto", response_model=AnalyzeAutoV2Response)
async def analyze_auto(payload: AnalyzeAutoV2Request) -> AnalyzeAutoV2Response:
    use_case = build_analyze_auto_use_case()
    try:
        return await use_case.execute(payload)
    except SQLAlchemyError as exc:
        # Evita 500 opacos a recu-judicial; el contrato ya contempla estado=error.
        logger.exception(
            "Fallo de base de datos en analyze-auto (proceso_id=%s actuacion_fuente_id=%s)",
            payload.proceso_id,
            payload.actuacion_fuente_id,
        )
        detail = (str(exc) or exc.__class__.__name__).strip().split("\n", 1)[0][:800]
        return AnalyzeAutoV2Response(
            estado="error",
            errores=[f"Error de base de datos (SVP/catalogo/antecedentes): {detail}"],
        )
