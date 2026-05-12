"""Ingest Bravotran waiting-queue dump.

Sheet: "Waiting"
The "Request Sent To" column (not "Request Sent To.1") is the canonical owner.
"""
from sqlalchemy.orm import Session

from app.db import models
from app.extraction import extract_file
from app.recon.normalize import normalize_invno


def _f(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _s(v):
    if v is None:
        return None
    if isinstance(v, float):
        # vendor codes / invoice numbers come through as 18991.0 — strip the .0
        if v.is_integer():
            return str(int(v))
        return str(v)
    return str(v).strip() or None


def ingest_bt(db: Session, path, filename: str):
    table = extract_file(path, sheet_name="Waiting", header_row=0)
    snap = models.BTSnapshot(filename=filename, storage_path=str(path), row_count=0)
    db.add(snap)
    db.flush()

    for r in table.rows:
        inv = r.get("Invoice Number")
        line = models.BTLine(
            snapshot_id=snap.id,
            bt_label=_s(r.get("BT Label")),
            request_sent_to=_s(r.get("Request Sent To")),
            email_subject=_s(r.get("Email Subject")),
            vendor=_s(r.get("Vendor")),
            vendor_code=_s(r.get("Vendor Code")),
            invoice_number=_s(inv),
            invoice_total=_f(r.get("Invoice Total")),
            accrued_total=_f(r.get("Accrued Total")),
            job_numbers=_s(r.get("Job Number(s)")),
            charge_codes=_s(r.get("Charge Code(s)")),
            invoice_date=_s(r.get("Invoice Date")),
            invoice_due_date=_s(r.get("Invoice Due Date")),
            invoice_received_on=_s(r.get("Invoice Received On")),
            request_sent_on=_s(r.get("Request Sent On")),
            labels=_s(r.get("Labels")),
            note=_s(r.get("Note")),
            link_to_item=_s(r.get("Link to Item")),
            bt_invoice_id=_s(r.get("bt_invoice_id")),
            norm_invno=normalize_invno(inv),
        )
        db.add(line)
    snap.row_count = len(table.rows)
    db.commit()
    db.refresh(snap)
    return snap
