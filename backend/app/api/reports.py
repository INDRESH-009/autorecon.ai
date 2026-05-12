"""Report endpoints — each returns an .xlsx file."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.reports import aging, disputes, payment_packet, recon_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/recon/{job_id}.xlsx")
def export_recon(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.ReconJob).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    data = recon_report.build(db, job)
    safe = "".join(c if c.isalnum() else "_" for c in job.vendor.organization)
    return _xlsx(data, f"recon_{safe}_{job.id}.xlsx")


@router.get("/aging.xlsx")
def export_aging(db: Session = Depends(get_db)):
    return _xlsx(aging.build(db), "aging_summary.xlsx")


@router.get("/disputes.xlsx")
def export_disputes(db: Session = Depends(get_db)):
    return _xlsx(disputes.build(db), "dispute_log.xlsx")


@router.get("/payment_packet.xlsx")
def export_payment_packet(db: Session = Depends(get_db)):
    return _xlsx(payment_packet.build(db), "payment_packet.xlsx")
