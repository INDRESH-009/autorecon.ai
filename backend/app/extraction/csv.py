import csv as _csv
from pathlib import Path

from app.extraction.coerce import dedupe_headers, jsonable
from app.extraction.types import ExtractedTable


def extract(path: str | Path) -> ExtractedTable:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = _csv.reader(fh)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return ExtractedTable(headers=[], rows=[])
        headers = dedupe_headers(raw_headers)
        rows = []
        for row in reader:
            if all(not (c or "").strip() for c in row):
                continue
            d = {h: jsonable(v) if v != "" else None for h, v in zip(headers, row)}
            rows.append(d)
        return ExtractedTable(headers=headers, rows=rows)
