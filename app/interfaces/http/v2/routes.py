from fastapi import APIRouter

from app.interfaces.http.v2.dependencies import build_analyze_auto_use_case
from app.interfaces.http.v2.schemas import AnalyzeAutoV2Request, AnalyzeAutoV2Response

router = APIRouter(prefix="/v2", tags=["analyze_v2"])


@router.post("/analyze-auto", response_model=AnalyzeAutoV2Response)
async def analyze_auto(payload: AnalyzeAutoV2Request) -> AnalyzeAutoV2Response:
    use_case = build_analyze_auto_use_case()
    return await use_case.execute(payload)
