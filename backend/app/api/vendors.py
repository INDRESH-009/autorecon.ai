"""Vendor master read endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas import VendorOut

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.get("", response_model=list[VendorOut])
def list_vendors(q: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    qry = db.query(models.Vendor)
    if q:
        qry = qry.filter(models.Vendor.organization.ilike(f"%{q}%"))
    return qry.order_by(models.Vendor.organization).limit(limit).all()


@router.get("/{vendor_id}", response_model=VendorOut)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    v = db.query(models.Vendor).get(vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    return v
