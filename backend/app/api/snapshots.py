"""Logisys + BT snapshot upload + list endpoints."""
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.session import get_db
from app.ingestion.bt import ingest_bt
from app.ingestion.logisys import ingest_logisys
from app.schemas import SnapshotOut

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.post("/logisys", response_model=SnapshotOut)
def upload_logisys(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Logisys dump must be .xlsx")
    dest = settings.storage_dir / f"logisys_{uuid.uuid4().hex}_{file.filename}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    try:
        snap = ingest_logisys(db, dest, filename=file.filename)
    except KeyError as e:
        raise HTTPException(400, f"Expected sheet 'AJWW LOGYSIS SOA'. Missing: {e}")
    return snap


@router.post("/bt", response_model=SnapshotOut)
def upload_bt(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "BT dump must be .xlsx")
    dest = settings.storage_dir / f"bt_{uuid.uuid4().hex}_{file.filename}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    try:
        snap = ingest_bt(db, dest, filename=file.filename)
    except KeyError as e:
        raise HTTPException(400, f"Expected sheet 'Waiting'. Missing: {e}")
    return snap


@router.get("/logisys", response_model=list[SnapshotOut])
def list_logisys(db: Session = Depends(get_db)):
    return db.query(models.LogisysSnapshot).order_by(models.LogisysSnapshot.uploaded_at.desc()).all()


@router.get("/bt", response_model=list[SnapshotOut])
def list_bt(db: Session = Depends(get_db)):
    return db.query(models.BTSnapshot).order_by(models.BTSnapshot.uploaded_at.desc()).all()
