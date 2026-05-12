"""JSON-safe coercion for cell values.

The bug we got bitten by previously: SQLAlchemy JSON columns fall back to
json.dumps, which trips on datetime / date / Decimal. Anything we put into a
JSON column or send out over the API must go through jsonable() first.
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import math


def jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, (int, str, bool)):
        return v
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, time):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): jsonable(val) for k, val in v.items()}
    return str(v)


def dedupe_headers(headers: list) -> list:
    """Strip and de-duplicate header names (a, a -> a, a__2)."""
    out = []
    seen = {}
    for h in headers:
        s = str(h).strip() if h is not None else ""
        if not s:
            s = "col"
        if s in seen:
            seen[s] += 1
            out.append(f"{s}__{seen[s]}")
        else:
            seen[s] = 1
            out.append(s)
    return out
