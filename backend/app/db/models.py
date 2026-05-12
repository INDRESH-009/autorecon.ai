from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization: Mapped[str] = mapped_column(String, unique=True, index=True)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    credit_days: Mapped[int] = mapped_column(Integer, default=0)
    gl_group: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LogisysSnapshot(Base):
    __tablename__ = "logisys_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    lines: Mapped[list["LogisysLine"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class LogisysLine(Base):
    __tablename__ = "logisys_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("logisys_snapshots.id", ondelete="CASCADE"), index=True
    )
    organization: Mapped[str] = mapped_column(String, index=True)
    txn_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transaction_no: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vendor_invoice_no: Mapped[Optional[str]] = mapped_column(String, index=True)
    vendor_invoice_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bucket_1_15: Mapped[float] = mapped_column(Float, default=0.0)
    bucket_16_30: Mapped[float] = mapped_column(Float, default=0.0)
    bucket_31_45: Mapped[float] = mapped_column(Float, default=0.0)
    bucket_46_60: Mapped[float] = mapped_column(Float, default=0.0)
    bucket_61_90: Mapped[float] = mapped_column(Float, default=0.0)
    bucket_over_90: Mapped[float] = mapped_column(Float, default=0.0)
    outstanding: Mapped[float] = mapped_column(Float, default=0.0)
    norm_invno: Mapped[Optional[str]] = mapped_column(String, index=True)

    snapshot: Mapped[LogisysSnapshot] = relationship(back_populates="lines")


class BTSnapshot(Base):
    __tablename__ = "bt_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    lines: Mapped[list["BTLine"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class BTLine(Base):
    __tablename__ = "bt_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("bt_snapshots.id", ondelete="CASCADE"), index=True
    )
    bt_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    request_sent_to: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email_subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String, index=True)
    vendor_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String, index=True)
    invoice_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accrued_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    job_numbers: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    charge_codes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invoice_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invoice_due_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invoice_received_on: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    request_sent_on: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    labels: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link_to_item: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bt_invoice_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    norm_invno: Mapped[Optional[str]] = mapped_column(String, index=True)

    snapshot: Mapped[BTSnapshot] = relationship(back_populates="lines")


class UploadedSOA(Base):
    __tablename__ = "uploaded_soas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("recon_jobs.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)
    raw_headers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    raw_preview: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    mapping: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    canonical_rows: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


class ReconJob(Base):
    __tablename__ = "recon_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    logisys_snapshot_id: Mapped[int] = mapped_column(ForeignKey("logisys_snapshots.id"))
    bt_snapshot_id: Mapped[int] = mapped_column(ForeignKey("bt_snapshots.id"))
    status: Mapped[str] = mapped_column(String, default="draft")
    residual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    closed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    vendor: Mapped[Vendor] = relationship()
    logisys_snapshot: Mapped[LogisysSnapshot] = relationship()
    bt_snapshot: Mapped[BTSnapshot] = relationship()
    soa: Mapped[Optional[UploadedSOA]] = relationship(
        "UploadedSOA",
        uselist=False,
        cascade="all, delete-orphan",
        primaryjoin="ReconJob.id==UploadedSOA.job_id",
    )
    results: Mapped[list["ReconLineResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class ReconLineResult(Base):
    __tablename__ = "recon_line_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("recon_jobs.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String, index=True)
    match_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vendor_inv_no: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vendor_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vendor_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vendor_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ajww_inv_no: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ajww_txn_no: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ajww_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ajww_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diff: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bt_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bt_labels: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bt_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bt_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bt_owner: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    job: Mapped[ReconJob] = relationship(back_populates="results")


class VendorMappingCache(Base):
    __tablename__ = "vendor_mapping_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    header_signature: Mapped[str] = mapped_column(String, index=True)
    mapping: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
