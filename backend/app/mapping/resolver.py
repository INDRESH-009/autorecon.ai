"""Resolve a vendor's SOA columns to canonical fields.

Strategy (deterministic, no LLM):
  Layer 1: exact / normalized alias match
  Layer 2: fuzzy match via rapidfuzz token_set_ratio against the alias library
  Layer 3: data-shape hints (a column of mostly-floats is probably AMOUNT;
           a column of mostly-dates is probably INVOICE_DATE)
  Negative filter: any header containing a NEGATIVE_KEYWORDS phrase is excluded
                   from candidacy.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from rapidfuzz import fuzz

from app.mapping.dictionary import (
    ALIASES,
    AMOUNT,
    CANONICAL_FIELDS,
    INVOICE_DATE,
    INVOICE_NO,
    NEGATIVE_KEYWORDS,
)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(s or "").strip().lower())


def _is_negative(header: str) -> bool:
    n = _norm(header)
    return any(neg in n for neg in NEGATIVE_KEYWORDS)


def _score_header_against_aliases(header: str, aliases: list) -> int:
    n = _norm(header)
    if not n:
        return 0
    best = 0
    for a in aliases:
        a_n = _norm(a)
        if n == a_n:
            return 100
        # If alias is a substring of header (or vice versa) on a word boundary, very strong
        if n in a_n or a_n in n:
            best = max(best, 92)
        best = max(best, int(fuzz.token_set_ratio(n, a_n)))
    return best


_DATE_RE = re.compile(
    r"^\s*\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}([ T]\d{1,2}:\d{2}(:\d{2})?)?\s*$"
)


def _looks_like_date(v: Any) -> bool:
    if isinstance(v, (date, datetime)):
        return True
    if isinstance(v, str):
        return bool(_DATE_RE.match(v))
    return False


def _looks_like_amount(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str):
        s = v.strip().replace(",", "").replace("$", "")
        if not s:
            return False
        try:
            float(s)
            return True
        except ValueError:
            return False
    return False


def _data_shape_score(field: str, samples: list) -> int:
    """Bonus score from inspecting actual data."""
    if not samples:
        return 0
    non_null = [s for s in samples if s is not None and s != ""]
    if not non_null:
        return 0
    if field == AMOUNT:
        hits = sum(1 for s in non_null if _looks_like_amount(s))
        return int(80 * hits / len(non_null))
    if field == INVOICE_DATE:
        hits = sum(1 for s in non_null if _looks_like_date(s))
        return int(80 * hits / len(non_null))
    if field == INVOICE_NO:
        # Invoice numbers tend to be short strings or ints, mostly unique
        unique_ratio = len(set(map(str, non_null))) / len(non_null)
        short = sum(1 for s in non_null if len(str(s)) <= 30)
        return int(60 * unique_ratio * (short / len(non_null)))
    return 0


def suggest_mapping(headers: list, sample_rows: list) -> dict:
    """Return {canonical_field -> {header, score, candidates}}.

    candidates lists the top alternatives for that field so the UI can let the
    accountant override.
    """
    eligible = [h for h in headers if h and not _is_negative(h)]

    # Build {field -> [(header, score), ...]} ranked
    per_field: dict = {}
    for field in CANONICAL_FIELDS:
        aliases = ALIASES.get(field, [])
        ranked = []
        for h in eligible:
            alias_score = _score_header_against_aliases(h, aliases)
            samples = [r.get(h) for r in sample_rows[:25]]
            shape_score = _data_shape_score(field, samples)
            score = max(alias_score, int(0.6 * alias_score + 0.4 * shape_score))
            # Big bonus if both signals agree
            if alias_score >= 75 and shape_score >= 60:
                score = min(100, score + 10)
            ranked.append((h, score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        per_field[field] = ranked

    # Greedy assignment: each header used at most once.
    used: set = set()
    result: dict = {}
    # Sort fields by their top-candidate confidence — assign confident fields first.
    field_order = sorted(
        CANONICAL_FIELDS,
        key=lambda f: per_field[f][0][1] if per_field[f] else 0,
        reverse=True,
    )
    for field in field_order:
        chosen = None
        chosen_score = 0
        for h, s in per_field[field]:
            if h in used:
                continue
            chosen = h
            chosen_score = s
            break
        if chosen is not None:
            used.add(chosen)
        result[field] = {
            "header": chosen,
            "score": chosen_score,
            "candidates": [
                {"header": h, "score": s}
                for h, s in per_field[field][:5]
            ],
        }
    return result


def header_signature(headers: list) -> str:
    """Stable signature to key the mapping cache by file shape."""
    return "|".join(sorted(_norm(h) for h in headers if h))
