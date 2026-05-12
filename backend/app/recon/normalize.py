"""Invoice number normalization, shared by ingestion + recon.

Real-world data hits us with the same invoice represented as 17904 (int),
17904.0 (float — what openpyxl returns for numeric cells), and "17904" (str).
All three must normalize identically.
"""
import re

_PREFIX_RE = re.compile(r"^(INV|INVOICE|BILL|BL|NO)[-#:\s]*", re.IGNORECASE)


def normalize_invno(value) -> str:
    if value is None:
        return ""
    # Integer-valued floats: 17904.0 -> "17904"
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value.is_integer():
            value = int(value)
    s = str(value).strip().upper()
    if not s or s in ("NAN", "NONE"):
        return ""
    # Trailing ".0" left over from float coercion of int values stored as text
    if s.endswith(".0") and s[:-2].replace("-", "").isdigit():
        s = s[:-2]
    while True:
        m = _PREFIX_RE.match(s)
        if not m:
            break
        new = s[m.end():].lstrip("-#: \t")
        if new == s:
            break
        s = new
    s = s.lstrip("0")
    return s or "0"


def round_amount(value) -> float:
    if value is None:
        return 0.0
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0
