"""Master sheet upload endpoint."""
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.ingestion.master_sheet import ingest_master
from app.schemas import MasterUploadResult

router = APIRouter(prefix="/api/master", tags=["master"])


@router.post("/upload", response_model=MasterUploadResult)
def upload_master(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Master sheet must be .xlsx")
    dest = settings.storage_dir / f"master_{uuid.uuid4().hex}_{file.filename}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    try:
        result = ingest_master(db, dest)
    except KeyError as e:
        raise HTTPException(400, f"Expected sheet 'country' with columns Organization, CountryName, Paybl_CreditDays, GL Group. Missing: {e}")
    return MasterUploadResult(**result)
