"""Pydantic schemas for the HTTP layer."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization: str
    country: Optional[str] = None
    credit_days: int = 0
    gl_group: Optional[str] = None


class MasterUploadResult(BaseModel):
    inserted: int
    updated: int
    total_rows: int


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    uploaded_at: datetime
    row_count: int


class ReconJobBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_id: int
    logisys_snapshot_id: int
    bt_snapshot_id: int
    status: str
    residual: Optional[float] = None
    closed: Optional[bool] = None
    created_at: datetime
    updated_at: datetime


class CreateJobIn(BaseModel):
    vendor_id: int
    logisys_snapshot_id: int
    bt_snapshot_id: int


class MappingFieldOut(BaseModel):
    header: Optional[str] = None
    score: int = 0
    candidates: list = []


class MappingSuggestOut(BaseModel):
    headers: list
    preview: list
    suggested: dict
    cached: bool = False


class ConfirmMappingIn(BaseModel):
    mapping: dict  # {invoice_no: header, invoice_date: header, amount: header}


class ReconLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
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


class ReconJobDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    residual: Optional[float] = None
    closed: Optional[bool] = None
    summary: Optional[dict] = None
    vendor: VendorOut
    logisys_snapshot: SnapshotOut
    bt_snapshot: SnapshotOut
    results: list[ReconLineOut] = []
    mapping: Optional[dict] = None
    soa_filename: Optional[str] = None
