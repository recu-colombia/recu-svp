from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    pages: int
    section_used: str


class DocumentExtractor(Protocol):
    async def extract_from_url(self, url: str) -> ExtractedDocument: ...
