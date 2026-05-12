"""Dispute log: lines in pending_in_bt or amount_dispute, with BT context."""
from io import BytesIO

from sqlalchemy.orm import Session

from app.db import models
from app.reports.excel_export import autosize, new_workbook, write_body_cell, write_header_row

COLUMNS = [
    "Vendor", "Status", "Invoice", "Amount", "Diff", "BT Label", "BT Labels",
    "Note", "Owner", "Link", "Age (days)",
]


def build(db: Session) -> bytes:
    wb = new_workbook()
    ws = wb.create_sheet("Disputes")
    write_header_row(ws, 1, COLUMNS, widths=[28, 16, 14, 12, 10, 14, 22, 40, 22, 28, 10])

    rows = (
        db.query(models.ReconLineResult, models.ReconJob, models.Vendor)
        .join(models.ReconJob, models.ReconLineResult.job_id == models.ReconJob.id)
        .join(models.Vendor, models.ReconJob.vendor_id == models.Vendor.id)
        .filter(models.ReconLineResult.status.in_(["pending_in_bt", "amount_dispute"]))
        .order_by(models.Vendor.organization, models.ReconLineResult.status)
        .all()
    )

    r = 2
    for line, _job, vendor in rows:
        vals = [
            vendor.organization,
            line.status,
            line.vendor_inv_no or line.ajww_inv_no or "",
            line.vendor_amount,
            line.diff,
            line.bt_label or "",
            line.bt_labels or "",
            line.bt_note or "",
            line.bt_owner or "",
            line.bt_link or "",
            line.vendor_age_days if line.vendor_age_days is not None else "",
        ]
        for j, val in enumerate(vals, 1):
            fmt = "#,##0.00" if j in (4, 5) else None
            write_body_cell(ws.cell(row=r, column=j), val, status=line.status, fmt=fmt)
        r += 1

    ws.freeze_panes = "A2"
    autosize(ws, len(COLUMNS))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
