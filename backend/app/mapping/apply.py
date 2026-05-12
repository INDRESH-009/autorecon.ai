"""Apply a confirmed mapping to a raw extracted table -> canonical SOA rows."""
from __future__ import annotations

import re
from datetime import date, datetime

from app.extraction.types import ExtractedTable
from app.mapping.dictionary import AMOUNT, INVOICE_DATE, INVOICE_NO


_DATE_PATTERNS = (
    "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y",
    "%Y-%m-%d %H:%M:%S", "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y",
)


def _to_str(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip() or None


def _to_amount(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "")
    if not s:
        return None
    # Handle (123.45) negative notation
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    try:
        n = float(s)
        return -n if neg else n
    except ValueError:
        return None


def _to_date(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    if not s:
        return None
    # ISO already?
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s  # last resort: keep the raw string


def apply_mapping(table: ExtractedTable, mapping: dict) -> list:
    """Turn a raw table + {field -> header} into canonical SOA rows.

    Each output row: {invoice_no, invoice_date, amount, _raw: {...}}.
    Rows where invoice_no and amount are BOTH missing are dropped (helper rows).
    """
    inv_col = mapping.get(INVOICE_NO)
    date_col = mapping.get(INVOICE_DATE)
    amt_col = mapping.get(AMOUNT)

    out = []
    for raw in table.rows:
        invoice_no = _to_str(raw.get(inv_col)) if inv_col else None
        invoice_date = _to_date(raw.get(date_col)) if date_col else None
        amount = _to_amount(raw.get(amt_col)) if amt_col else None
        if invoice_no is None and (amount is None or amount == 0):
            continue
        out.append({
            "invoice_no": invoice_no,
            "invoice_date": invoice_date,
            "amount": amount,
            "_raw": raw,
        })
    return out
