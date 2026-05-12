"""Ingest Logisys aging dump.

Sheet:      "AJWW LOGYSIS SOA"
Header row: row index 2 (rows 0-1 are preamble).
Skip rows where Organization is "Total" / "Vendor Invoices Pending Write Off." / blank.
"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.db import models
from app.extraction import extract_file
from app.recon.normalize import normalize_invno


SKIP_ORGS = {"Total", "Vendor Invoices Pending Write Off."}


def _f(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _inv_str(v):
    """Render an invoice number for display: drop the .0 on integer floats."""
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip() or None


def _date_str(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def ingest_logisys(db: Session, path, filename: str):
    table = extract_file(path, sheet_name="AJWW LOGYSIS SOA", header_row=2)
    snap = models.LogisysSnapshot(filename=filename, storage_path=str(path), row_count=0)
    db.add(snap)
    db.flush()

    kept = 0
    for r in table.rows:
        org = r.get("Organization")
        if not isinstance(org, str):
            continue
        org = org.strip()
        if not org or org in SKIP_ORGS:
            continue
        inv = r.get("Vendor Inv No.")
        line = models.LogisysLine(
            snapshot_id=snap.id,
            organization=org,
            txn_date=_date_str(r.get("Date")),
            transaction_no=_inv_str(r.get("Transaction No")),
            vendor_invoice_no=_inv_str(inv),
            vendor_invoice_date=_date_str(r.get("Vendor Inv Date")),
            document_type=r.get("Document Type"),
            bucket_1_15=_f(r.get("1 - 15 Days")),
            bucket_16_30=_f(r.get("16 - 30 Days")),
            bucket_31_45=_f(r.get("31 - 45 Days")),
            bucket_46_60=_f(r.get("46 - 60 Days")),
            bucket_61_90=_f(r.get("61 - 90 Days")),
            bucket_over_90=_f(r.get("> 90 Days")),
            outstanding=_f(r.get("OutStanding (USD)")),
            norm_invno=normalize_invno(inv),
        )
        db.add(line)
        kept += 1
    snap.row_count = kept
    db.commit()
    db.refresh(snap)
    return snap
