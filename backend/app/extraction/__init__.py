from pathlib import Path

from app.extraction import csv as _csv
from app.extraction import pdf as _pdf
from app.extraction import xlsx as _xlsx
from app.extraction.types import ExtractedTable


def extract_file(
    path: str | Path,
    *,
    sheet_name: str | None = None,
    header_row: int = 0,
) -> ExtractedTable:
    """Dispatch based on extension."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return _xlsx.extract(p, sheet_name=sheet_name, header_row=header_row)
    if ext == ".csv":
        return _csv.extract(p)
    if ext == ".pdf":
        return _pdf.extract(p)
    raise ValueError(f"Unsupported file type: {ext}")


def list_sheets(path: str | Path) -> list:
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        return _xlsx.list_sheets(p)
    return []


__all__ = ["extract_file", "list_sheets", "ExtractedTable"]
