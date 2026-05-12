"""Payment release packet: ok_to_pay lines grouped by vendor."""
from io import BytesIO

from sqlalchemy.orm import Session

from app.db import models
from app.reports.excel_export import (
    BOLD_BODY_FONT,
    SUBHEAD_FILL,
    SUBHEAD_FONT,
    autosize,
    new_workbook,
    write_body_cell,
    write_header_row,
)

COLUMNS = ["Vendor", "Invoice", "Invoice Date", "Amount", "Age (days)", "Credit Term", "AJWW Txn No"]


def build(db: Session) -> bytes:
    wb = new_workbook()
    ws = wb.create_sheet("Payment Packet")
    write_header_row(ws, 1, COLUMNS, widths=[30, 16, 14, 14, 10, 12, 16])

    rows = (
        db.query(models.ReconLineResult, models.Vendor)
        .join(models.ReconJob, models.ReconLineResult.job_id == models.ReconJob.id)
        .join(models.Vendor, models.ReconJob.vendor_id == models.Vendor.id)
        .filter(models.ReconLineResult.status == "ok_to_pay")
        .order_by(models.Vendor.organization, models.ReconLineResult.vendor_date)
        .all()
    )

    # Group by vendor for subtotals
    by_vendor: dict = {}
    for line, vendor in rows:
        by_vendor.setdefault(vendor, []).append(line)

    r = 2
    grand = 0.0
    for vendor in sorted(by_vendor, key=lambda v: v.organization):
        # Vendor band
        c = ws.cell(row=r, column=1, value=vendor.organization)
        c.font = SUBHEAD_FONT
        c.fill = SUBHEAD_FILL
        for j in range(2, len(COLUMNS) + 1):
            ws.cell(row=r, column=j).fill = SUBHEAD_FILL
        r += 1

        subtotal = 0.0
        for line in by_vendor[vendor]:
            vals = [
                vendor.organization,
                line.vendor_inv_no or "",
                line.vendor_date or "",
                line.vendor_amount,
                line.vendor_age_days if line.vendor_age_days is not None else "",
                vendor.credit_days or 0,
                line.ajww_txn_no or "",
            ]
            for j, val in enumerate(vals, 1):
                fmt = "#,##0.00" if j == 4 else None
                write_body_cell(ws.cell(row=r, column=j), val, status="ok_to_pay", fmt=fmt)
            subtotal += line.vendor_amount or 0.0
            r += 1

        sub_cell = ws.cell(row=r, column=3, value="Subtotal")
        sub_cell.font = BOLD_BODY_FONT
        amt_cell = ws.cell(row=r, column=4, value=round(subtotal, 2))
        amt_cell.font = BOLD_BODY_FONT
        amt_cell.number_format = "#,##0.00"
        r += 2  # blank row between vendors
        grand += subtotal

    if by_vendor:
        gc = ws.cell(row=r, column=3, value="GRAND TOTAL")
        gc.font = BOLD_BODY_FONT
        ac = ws.cell(row=r, column=4, value=round(grand, 2))
        ac.font = BOLD_BODY_FONT
        ac.number_format = "#,##0.00"

    ws.freeze_panes = "A2"
    autosize(ws, len(COLUMNS))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
