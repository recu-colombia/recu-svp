import io
import importlib
import logging
import re

import httpx

from app.application.ports.documents import DocumentExtractor, ExtractedDocument
from app.config import get_settings

logger = logging.getLogger(__name__)


class PDFDocumentExtractor(DocumentExtractor):
    def __init__(self) -> None:
        self._settings = get_settings()

    async def extract_from_url(self, url: str) -> ExtractedDocument:
        if not url or not url.strip():
            raise ValueError("La URL del auto es obligatoria.")

        logger.info("Iniciando extraccion PDF desde URL=%s", url)
        pdf_bytes, content_type = await self._download_pdf(url.strip())
        logger.info(
            "PDF descargado correctamente. bytes=%s content_type=%s",
            len(pdf_bytes),
            content_type,
        )
        text, pages = self._extract_text_with_fallback(pdf_bytes)
        if not text.strip():
            raise ValueError("No se pudo extraer texto util del PDF.")

        section = self._extract_resuelve_section(text)
        section_used = "resuelve_only" if section != text else "full_text"
        logger.info(
            "Extraccion PDF finalizada. pages=%s section_used=%s text_len=%s",
            pages,
            section_used,
            len(section),
        )
        return ExtractedDocument(text=section, pages=pages, section_used=section_used)

    async def _download_pdf(self, url: str) -> tuple[bytes, str]:
        timeout = httpx.Timeout(float(self._settings.ai_timeout))
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
        if response.status_code >= 400:
            logger.error("Descarga PDF fallo. status=%s url=%s", response.status_code, url)
            raise ValueError(f"No se pudo descargar el PDF. HTTP {response.status_code}.")

        content_type = response.headers.get("content-type", "").lower()
        content = response.content or b""
        if len(content) < 16:
            raise ValueError("El archivo descargado es demasiado pequeno para ser PDF.")

        looks_like_pdf = content.startswith(b"%PDF")
        if "pdf" not in content_type and not looks_like_pdf:
            logger.error("Contenido descargado no parece PDF. content_type=%s", content_type)
            raise ValueError("La URL no devolvio un PDF valido.")
        return content, content_type

    def _extract_text_with_fallback(self, pdf_bytes: bytes) -> tuple[str, int]:
        try:
            pypdf_module = importlib.import_module("pypdf")
            pdf_reader_cls = pypdf_module.PdfReader
        except Exception as exc:
            logger.exception("No se pudo cargar pypdf.")
            raise ValueError(f"No está disponible el parser PDF (pypdf): {exc}") from exc

        reader = pdf_reader_cls(io.BytesIO(pdf_bytes))
        pages = len(reader.pages)
        chunks: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                chunks.append(page_text)
        return "\n".join(chunks).strip(), pages

    def _extract_resuelve_section(self, full_text: str) -> str:
        patterns = [
            r"RESUELVE:(.*?)(?=\n\s*\n|\n[A-Z][A-Z\s]{3,}:|$)",
            r"RESUELVE\s*:(.*?)(?=\n\s*\n|\n[A-Z][A-Z\s]{3,}:|$)",
            r"RESUELVE\s+(.*?)(?=\n\s*\n|\n[A-Z][A-Z\s]{3,}:|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            section = self._clean_text(match.group(1))
            if len(section) > 80:
                return section
        return self._clean_text(full_text)

    @staticmethod
    def _clean_text(text: str) -> str:
        text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\n\t")
        text = re.sub(r"\s+", " ", text).strip()
        return text
