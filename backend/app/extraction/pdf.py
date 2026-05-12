"""PDF extractor stub. Real PDF support is deferred to v2; we provide a
placeholder so the file dispatcher can recognise the type and fail loud."""
from pathlib import Path

from app.extraction.types import ExtractedTable


def extract(path: str | Path) -> ExtractedTable:
    raise NotImplementedError(
        "PDF SOA ingestion is not enabled in MVP. Convert to XLSX first."
    )
