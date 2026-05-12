"""Reconciliation engine: two-pass match + closing-equation invariant.

Pass 1 — exact Concan (normalize_invno, round(amount, 2))
Pass 2 — same normalized invoice no, amount within tolerance
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.config import settings
from app.recon.normalize import normalize_invno, round_amount


@dataclass
class ReconLine:
    status: str
    match_method: Optional[str] = None
    vendor_inv_no: Optional[str] = None
    vendor_date: Optional[str] = None
    vendor_amount: Optional[float] = None
    vendor_age_days: Optional[int] = None
    ajww_inv_no: Optional[str] = None
    ajww_txn_no: Optional[str] = None
    ajww_date: Optional[str] = None
    ajww_amount: Optional[float] = None
    diff: Optional[float] = None
    bt_label: Optional[str] = None
    bt_labels: Optional[str] = None
    bt_note: Optional[str] = None
    bt_link: Optional[str] = None
    bt_owner: Optional[str] = None


@dataclass
class ReconResult:
    lines: list = field(default_factory=list)
    vendor_total: float = 0.0
    ajww_total: float = 0.0
    reconstructed_total: float = 0.0
    residual: float = 0.0
    closed: bool = False
    counts: dict = field(default_factory=dict)


def _tolerance(amount: float) -> float:
    return max(settings.amount_tolerance_abs, abs(amount) * settings.amount_tolerance_pct)


def reconcile(
    vendor_rows: list,
    ajww_rows: list,
    *,
    today_iso: Optional[str] = None,
    credit_days: int = 0,
) -> ReconResult:
    """Pure recon, no BT classification — caller plugs that in afterwards.

    vendor_rows: list of {invoice_no, invoice_date, amount}
    ajww_rows:   list of LogisysLine ORM objects OR dicts with
                 norm_invno / outstanding / transaction_no / vendor_invoice_no /
                 vendor_invoice_date.
    """
    from datetime import date

    today = date.fromisoformat(today_iso) if today_iso else date.today()

    # Index Logisys lines by normalized invno (multimap)
    ajww_by_inv: dict = {}
    for line in ajww_rows:
        if isinstance(line, dict):
            inv = line.get("norm_invno") or normalize_invno(line.get("vendor_invoice_no"))
            amount = float(line.get("outstanding") or 0.0)
            line_obj = {
                "norm_invno": inv,
                "outstanding": amount,
                "vendor_invoice_no": line.get("vendor_invoice_no"),
                "vendor_invoice_date": line.get("vendor_invoice_date"),
                "transaction_no": line.get("transaction_no"),
            }
        else:
            inv = line.norm_invno or normalize_invno(line.vendor_invoice_no)
            line_obj = {
                "norm_invno": inv,
                "outstanding": float(line.outstanding or 0.0),
                "vendor_invoice_no": line.vendor_invoice_no,
                "vendor_invoice_date": line.vendor_invoice_date,
                "transaction_no": line.transaction_no,
            }
        ajww_by_inv.setdefault(inv, []).append(line_obj)

    used_ajww_ids: set = set()
    result_lines: list = []
    matched_vendor_idx: set = set()

    vendor_total = round(sum((float(r.get("amount") or 0) for r in vendor_rows)), 2)
    ajww_total = round(sum((float(l["outstanding"]) for lines in ajww_by_inv.values() for l in lines)), 2)

    # --- Pass 1: exact Concan ---
    for i, vr in enumerate(vendor_rows):
        vinv = normalize_invno(vr.get("invoice_no"))
        vamt = round_amount(vr.get("amount"))
        candidates = ajww_by_inv.get(vinv, [])
        for j, c in enumerate(candidates):
            cid = (vinv, j)
            if cid in used_ajww_ids:
                continue
            if round(c["outstanding"], 2) == vamt:
                used_ajww_ids.add(cid)
                matched_vendor_idx.add(i)
                age = _age_days(vr.get("invoice_date"), today)
                status = "ok_to_pay" if (age is not None and age >= credit_days) else "not_due"
                result_lines.append(ReconLine(
                    status=status,
                    match_method="exact",
                    vendor_inv_no=str(vr.get("invoice_no") or "") or None,
                    vendor_date=vr.get("invoice_date"),
                    vendor_amount=vamt,
                    vendor_age_days=age,
                    ajww_inv_no=str(c["vendor_invoice_no"] or "") or None,
                    ajww_txn_no=c["transaction_no"],
                    ajww_date=c["vendor_invoice_date"],
                    ajww_amount=round(c["outstanding"], 2),
                    diff=0.0,
                ))
                break

    # --- Pass 2: tolerance (same inv no, amount close) ---
    for i, vr in enumerate(vendor_rows):
        if i in matched_vendor_idx:
            continue
        vinv = normalize_invno(vr.get("invoice_no"))
        vamt = round_amount(vr.get("amount"))
        tol = _tolerance(vamt)
        candidates = ajww_by_inv.get(vinv, [])
        for j, c in enumerate(candidates):
            cid = (vinv, j)
            if cid in used_ajww_ids:
                continue
            diff = round(vamt - round(c["outstanding"], 2), 2)
            if abs(diff) <= tol:
                used_ajww_ids.add(cid)
                matched_vendor_idx.add(i)
                age = _age_days(vr.get("invoice_date"), today)
                status = "amount_dispute" if abs(diff) > 0.01 else (
                    "ok_to_pay" if (age is not None and age >= credit_days) else "not_due"
                )
                result_lines.append(ReconLine(
                    status=status,
                    match_method="tolerance",
                    vendor_inv_no=str(vr.get("invoice_no") or "") or None,
                    vendor_date=vr.get("invoice_date"),
                    vendor_amount=vamt,
                    vendor_age_days=age,
                    ajww_inv_no=str(c["vendor_invoice_no"] or "") or None,
                    ajww_txn_no=c["transaction_no"],
                    ajww_date=c["vendor_invoice_date"],
                    ajww_amount=round(c["outstanding"], 2),
                    diff=diff,
                ))
                break

    # --- Vendor-only (unmatched vendor rows) ---
    vendor_only_rows = []
    for i, vr in enumerate(vendor_rows):
        if i in matched_vendor_idx:
            continue
        vamt = round_amount(vr.get("amount"))
        age = _age_days(vr.get("invoice_date"), today)
        line = ReconLine(
            status="to_be_booked",  # classifier may upgrade to pending_in_bt
            match_method="none",
            vendor_inv_no=str(vr.get("invoice_no") or "") or None,
            vendor_date=vr.get("invoice_date"),
            vendor_amount=vamt,
            vendor_age_days=age,
            diff=None,
        )
        vendor_only_rows.append(line)
        result_lines.append(line)

    # --- AJWW-only (unmatched Logisys lines) ---
    for inv, lines in ajww_by_inv.items():
        for j, c in enumerate(lines):
            cid = (inv, j)
            if cid in used_ajww_ids:
                continue
            result_lines.append(ReconLine(
                status="missing_in_vendor",
                match_method="none",
                ajww_inv_no=str(c["vendor_invoice_no"] or "") or None,
                ajww_txn_no=c["transaction_no"],
                ajww_date=c["vendor_invoice_date"],
                ajww_amount=round(c["outstanding"], 2),
            ))

    # --- Closing equation (provisional; classifier will recompute after status moves) ---
    return _finalize(result_lines, vendor_total, ajww_total)


def _finalize(result_lines, vendor_total, ajww_total) -> ReconResult:
    sum_missing = round(sum(
        (l.ajww_amount or 0) for l in result_lines if l.status == "missing_in_vendor"
    ), 2)
    sum_to_be_booked = round(sum(
        (l.vendor_amount or 0) for l in result_lines
        if l.status in ("to_be_booked", "pending_in_bt")
    ), 2)
    sum_paid = round(sum(
        (l.vendor_amount or 0) for l in result_lines if l.status == "paid"
    ), 2)
    sum_disp_diff = round(sum(
        (l.diff or 0) for l in result_lines if l.status == "amount_dispute"
    ), 2)

    reconstructed = round(
        vendor_total + sum_missing - sum_to_be_booked - sum_paid + sum_disp_diff,
        2,
    )
    residual = round(abs(ajww_total - reconstructed), 2)
    closed = residual <= settings.residual_tolerance

    counts: dict = {}
    for l in result_lines:
        counts[l.status] = counts.get(l.status, 0) + 1

    return ReconResult(
        lines=result_lines,
        vendor_total=vendor_total,
        ajww_total=ajww_total,
        reconstructed_total=reconstructed,
        residual=residual,
        closed=closed,
        counts=counts,
    )


def recompute_totals(result: ReconResult) -> ReconResult:
    """Recompute closing equation after the classifier rewrites statuses."""
    return _finalize(result.lines, result.vendor_total, result.ajww_total)


def _age_days(date_iso, today) -> Optional[int]:
    from datetime import date as _date, datetime as _dt
    if not date_iso:
        return None
    try:
        if isinstance(date_iso, _dt):
            d = date_iso.date()
        elif isinstance(date_iso, _date):
            d = date_iso
        else:
            s = str(date_iso)[:10]
            d = _date.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    return (today - d).days
