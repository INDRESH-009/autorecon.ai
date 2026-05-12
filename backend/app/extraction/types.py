from dataclasses import dataclass
from typing import Any


@dataclass
class ExtractedTable:
    """Format-agnostic table representation produced by extractors.

    headers: list of header strings (already de-duped, trimmed).
    rows:    list of dict rows {header -> JSON-safe value}.
    sheet:   original sheet name if applicable.
    """

    headers: list
    rows: list
    sheet: str | None = None
