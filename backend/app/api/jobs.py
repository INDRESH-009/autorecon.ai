"""Recon job lifecycle: create, upload SOA, suggest mapping, confirm + run."""
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.session import get_db
from app.extraction import extract_file, list_sheets
from app.mapping.apply import apply_mapping
from app.mapping.dictionary import ALIASES
from app.mapping.resolver import header_signature, suggest_mapping
from app.recon.runner import run_job
from app.schemas import (
    ConfirmMappingIn,
    CreateJobIn,
    MappingSuggestOut,
    ReconJobBrief,
    ReconJobDetail,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _detect_header_row(path, sheet_name, max_scan: int = 5) -> int:
    """Auto-detect which row in the SOA holds the column headers.

    Scans the first `max_scan` rows, treats each as a candidate header row,
    and scores it by how many of its cells look like canonical field aliases
    (invoice number / date / amount synonyms). The row with the most hits
    wins. Falls back to 0 if no row stands out.

    Real-world SOAs vary: clean 3-column files have headers on row 1
    (header_row=0); AP-team templates with sub-total preambles have them on
    row 2 (header_row=1). This makes the upload robust to both.
    """
    all_aliases = {a.lower() for v in ALIASES.values() for a in v}
    best_row, best_hits = 0, 0
    for hr in range(max_scan):
        try:
            t = extract_file(path, sheet_name=sheet_name, header_row=hr)
        except Exception:
            continue
        hits = 0
        for h in t.headers:
            if not isinstance(h, str):
                continue
            hl = h.strip().lower()
            if not hl:
                continue
            if any(a in hl or hl in a for a in all_aliases):
                hits += 1
        if hits > best_hits:
            best_hits, best_row = hits, hr
    return best_row


@router.get("", response_model=list[ReconJobBrief])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(models.ReconJob).order_by(models.ReconJob.created_at.desc()).all()


@router.post("", response_model=ReconJobBrief)
def create_job(body: CreateJobIn, db: Session = Depends(get_db)):
    vendor = db.query(models.Vendor).get(body.vendor_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    if not db.query(models.LogisysSnapshot).get(body.logisys_snapshot_id):
        raise HTTPException(404, "Logisys snapshot not found")
    if not db.query(models.BTSnapshot).get(body.bt_snapshot_id):
        raise HTTPException(404, "BT snapshot not found")
    job = models.ReconJob(
        vendor_id=body.vendor_id,
        logisys_snapshot_id=body.logisys_snapshot_id,
        bt_snapshot_id=body.bt_snapshot_id,
        status="draft",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _job_to_detail(job: models.ReconJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "residual": job.residual,
        "closed": job.closed,
        "summary": job.summary,
        "vendor": job.vendor,
        "logisys_snapshot": job.logisys_snapshot,
        "bt_snapshot": job.bt_snapshot,
        "results": job.results,
        "mapping": job.soa.mapping if job.soa else None,
        "soa_filename": job.soa.filename if job.soa else None,
    }


@router.get("/{job_id}", response_model=ReconJobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.ReconJob).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_detail(job)


@router.post("/{job_id}/soa")
def upload_soa(
    job_id: int,
    sheet: str | None = None,
    header_row: int | None = None,  # None → auto-detect; explicit int → use as-is
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> MappingSuggestOut:
    """Upload the vendor's SOA, auto-detect column mapping, return suggestion.

    `header_row` semantics:
      - omitted/None: scan the first few rows and pick the one whose cells
        look most like canonical field names (handles clean 3-col SOAs AND
        AP-team templates with sub-total preambles automatically).
      - explicit int: use that row index verbatim (accountant override).
    """
    job = db.query(models.ReconJob).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".csv")):
        raise HTTPException(400, "SOA must be .xlsx or .csv (PDF support deferred)")

    dest = settings.storage_dir / f"soa_{job.id}_{uuid.uuid4().hex}_{file.filename}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)

    # Resolve sheet
    sheets = list_sheets(dest)
    chosen_sheet = sheet if sheet in sheets else (sheets[0] if sheets else None)

    # Auto-detect header row if not explicitly provided
    if header_row is None:
        header_row = _detect_header_row(dest, chosen_sheet)

    try:
        table = extract_file(dest, sheet_name=chosen_sheet, header_row=header_row)
    except Exception as e:
        raise HTTPException(400, f"Failed to read SOA: {e}")

    if not table.headers:
        raise HTTPException(400, "SOA has no headers at the chosen row.")

    suggested = suggest_mapping(table.headers, table.rows)

    # Try cache
    sig = header_signature(table.headers)
    cached = (
        db.query(models.VendorMappingCache)
        .filter_by(vendor_id=job.vendor_id, header_signature=sig)
        .one_or_none()
    )

    if cached:
        # Pre-fill suggestion with cached choices (still let the user override).
        for field, header in cached.mapping.items():
            if field in suggested:
                suggested[field]["header"] = header
                suggested[field]["score"] = 100

    # Persist UploadedSOA (overwrite any prior one)
    if job.soa is not None:
        db.delete(job.soa)
        db.flush()
    soa = models.UploadedSOA(
        job_id=job.id,
        filename=file.filename,
        storage_path=str(dest),
        raw_headers=table.headers,
        raw_preview=table.rows[:25],
        mapping={"_suggested": suggested, "_sheet": chosen_sheet, "_header_row": header_row},
    )
    db.add(soa)
    job.status = "mapping_pending"
    db.commit()
    db.refresh(soa)

    return MappingSuggestOut(
        headers=table.headers,
        preview=table.rows[:10],
        suggested=suggested,
        cached=cached is not None,
    )


@router.post("/{job_id}/mapping/confirm", response_model=ReconJobDetail)
def confirm_mapping(job_id: int, body: ConfirmMappingIn, db: Session = Depends(get_db)):
    """Confirm column mapping, materialize canonical rows, run reconciliation."""
    job = db.query(models.ReconJob).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.soa is None:
        raise HTTPException(400, "No SOA uploaded for this job.")

    mapping = body.mapping or {}
    required = ("invoice_no", "invoice_date", "amount")
    missing = [f for f in required if not mapping.get(f)]
    if missing:
        raise HTTPException(400, f"Missing mapping for: {', '.join(missing)}")

    # Re-extract from disk to get full rows (we only stored preview)
    soa_meta = job.soa.mapping or {}
    chosen_sheet = soa_meta.get("_sheet")
    header_row = soa_meta.get("_header_row", 0)
    try:
        table = extract_file(job.soa.storage_path, sheet_name=chosen_sheet, header_row=header_row)
    except Exception as e:
        raise HTTPException(400, f"Failed to re-read SOA: {e}")

    canonical = apply_mapping(table, mapping)
    # Strip _raw before persisting to keep JSON column compact
    persisted = [{k: v for k, v in r.items() if k != "_raw"} for r in canonical]

    job.soa.canonical_rows = persisted
    job.soa.mapping = {**mapping, "_sheet": chosen_sheet, "_header_row": header_row}
    job.status = "mapping_confirmed"
    db.commit()

    # Cache mapping by header signature
    sig = header_signature(table.headers)
    existing = (
        db.query(models.VendorMappingCache)
        .filter_by(vendor_id=job.vendor_id, header_signature=sig)
        .one_or_none()
    )
    if existing:
        existing.mapping = {k: v for k, v in mapping.items() if k in ("invoice_no", "invoice_date", "amount")}
    else:
        db.add(models.VendorMappingCache(
            vendor_id=job.vendor_id,
            header_signature=sig,
            mapping={k: v for k, v in mapping.items() if k in ("invoice_no", "invoice_date", "amount")},
        ))
    db.commit()

    # Run reconciliation
    try:
        run_job(db, job)
    except Exception as e:
        raise HTTPException(500, f"Reconciliation failed: {e}")
    db.refresh(job)
    return _job_to_detail(job)


@router.post("/{job_id}/rerun", response_model=ReconJobDetail)
def rerun(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.ReconJob).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.soa is None or not job.soa.canonical_rows:
        raise HTTPException(400, "Mapping not confirmed yet.")
    run_job(db, job)
    db.refresh(job)
    return _job_to_detail(job)