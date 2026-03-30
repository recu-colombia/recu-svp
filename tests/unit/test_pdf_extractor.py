import asyncio

from app.infrastructure.documents.pdf_extractor import PDFDocumentExtractor


class FakeResponse:
    def __init__(self, status_code: int, content: bytes, headers: dict[str, str]) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = headers


class FakeAsyncClient:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        _ = (exc_type, exc, tb)

    async def get(self, url: str) -> FakeResponse:
        _ = url
        return self._response


def test_download_pdf_rejects_non_pdf(monkeypatch) -> None:  # noqa: ANN001
    extractor = PDFDocumentExtractor()
    fake_response = FakeResponse(200, b"hello world not pdf", {"content-type": "text/plain"})
    monkeypatch.setattr(
        "app.infrastructure.documents.pdf_extractor.httpx.AsyncClient",
        lambda **kwargs: FakeAsyncClient(fake_response),  # noqa: ARG005
    )

    async def _run() -> None:
        try:
            await extractor.extract_from_url("https://example.com/file")
            assert False
        except ValueError as exc:
            assert "no devolvio un PDF valido" in str(exc)

    asyncio.run(_run())
