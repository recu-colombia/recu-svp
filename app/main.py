import logging

from fastapi import FastAPI

from app.config import get_settings
from app.interfaces.http.v2.routes import router as analyze_v2_router

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(title=settings.app_name)
app.include_router(analyze_v2_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
