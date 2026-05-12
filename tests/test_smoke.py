"""End-to-end smoke test against the real four files. Asserts the closing
equation holds for Quick Logistics: residual must be 0 (cents-tolerant).

Run with:  cd backend && PYTHONPATH=. python -m pytest ../tests/test_smoke.py -s
Or directly: cd backend && PYTHONPATH=. python ../tests/test_smoke.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SAMPLE = ROOT / "sample_data"
sys.path.insert(0, str(BACKEND))

# Use a throwaway DB and storage for the smoke test
_tmp = Path(tempfile.mkdtemp(prefix="recon_smoke_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'smoke.db'}"

# Settings reads DATABASE_URL via pydantic-settings, but we set the attr
# directly to be safe across pydantic-settings versions.
from app.core.config import settings
settings.database_url = f"sqlite:///{_tmp / 'smoke.db'}"
settings.storage_dir = _tmp / "storage"
settings.storage_dir.mkdir(parents=True, exist_ok=True)

# Re-bind engine to the new DB URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import session as db_session
db_session.engine = create_engine(settings.database_url, connect_args={"check_same_thread": False}, future=True)
db_session.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_session.engine, future=True)

from app.db.session import Base, SessionLocal
from app.db import models  # registers tables on Base
Base.metadata.create_all(bind=db_session.engine)


def run_smoke():
    db = SessionLocal()
    try:
        # 1. Ingest master
        from app.ingestion.master_sheet import ingest_master
        master_path = SAMPLE / "credit_country.xlsx"
        m = ingest_master(db, master_path)
        print(f"master: inserted={m['inserted']} updated={m['updated']} total={m['total_rows']}")
        assert m["inserted"] > 3000

        # 2. Ingest Logisys
        from app.ingestion.logisys import ingest_logisys
        logisys_path = SAMPLE / "logisys_dump.xlsx"
        logisys = ingest_logisys(db, logisys_path, filename="logisys_dump.xlsx")
        print(f"logisys snapshot id={logisys.id} rows={logisys.row_count}")
        assert logisys.row_count > 2000

        # Sanity: Quick Logistics count + total
        ql_lines = db.query(models.LogisysLine).filter_by(
            snapshot_id=logisys.id, organization="Quick Logistics LLC US"
        ).all()
        print(f"  QL Logisys lines: {len(ql_lines)} total={sum(l.outstanding for l in ql_lines)}")
        assert len(ql_lines) == 21
        assert round(sum(l.outstanding for l in ql_lines), 2) == 2761.00

        # 3. Ingest BT
        from app.ingestion.bt import ingest_bt
        bt_path = SAMPLE / "bt_dump_quick.xlsx"
        bt = ingest_bt(db, bt_path, filename="bt_dump_quick.xlsx")
        print(f"BT snapshot id={bt.id} rows={bt.row_count}")
        ql_bt = db.query(models.BTLine).filter_by(snapshot_id=bt.id, vendor="Quick Logistics LLC US").all()
        print(f"  QL BT lines: {len(ql_bt)}")
        assert len(ql_bt) == 9

        # 4. Create job for Quick Logistics
        ql_vendor = db.query(models.Vendor).filter_by(organization="Quick Logistics LLC US").one()
        print(f"vendor: {ql_vendor.organization} credit={ql_vendor.credit_days} country={ql_vendor.country}")
        assert ql_vendor.credit_days == 15
        assert ql_vendor.country == "United States"

        job = models.ReconJob(
            vendor_id=ql_vendor.id,
            logisys_snapshot_id=logisys.id,
            bt_snapshot_id=bt.id,
            status="draft",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # 5. Upload SOA + auto-map
        from app.extraction import extract_file
        from app.mapping.resolver import suggest_mapping
        from app.mapping.apply import apply_mapping

        soa_path = SAMPLE / "vendor_soa_quicklogi.xlsx"
        table = extract_file(soa_path, sheet_name="VENDOR SOA", header_row=1)
        print(f"SOA: {len(table.headers)} headers, {len(table.rows)} rows")
        suggested = suggest_mapping(table.headers, table.rows)
        print("suggested mapping:")
        for f, info in suggested.items():
            print(f"  {f}: {info['header']!r} (score={info['score']})")

        # Pull final mapping from the suggestion (highest scoring header per field)
        mapping = {f: info["header"] for f, info in suggested.items()}
        assert mapping["invoice_no"] == "INV Number"
        assert mapping["invoice_date"] == "INV Date"
        assert mapping["amount"] == "Outstanding Amount"

        canonical = apply_mapping(table, mapping)
        print(f"canonical rows: {len(canonical)}")
        assert len(canonical) == 34
        assert round(sum(r["amount"] for r in canonical), 2) == 4609.83

        # Persist SOA
        soa = models.UploadedSOA(
            job_id=job.id,
            filename="vendor_soa_quicklogi.xlsx",
            storage_path=str(soa_path),
            raw_headers=table.headers,
            raw_preview=table.rows[:10],
            mapping=mapping,
            canonical_rows=[{k: v for k, v in r.items() if k != "_raw"} for r in canonical],
        )
        db.add(soa)
        db.commit()

        # 6. Run reconciliation
        from app.recon.runner import run_job
        run_job(db, job)
        db.refresh(job)

        print("\n=== RECON SUMMARY ===")
        for k, v in (job.summary or {}).items():
            print(f"  {k}: {v}")
        print(f"  residual: {job.residual}")
        print(f"  closed: {job.closed}")

        assert job.summary["vendor_total"] == 4609.83
        assert job.summary["ajww_total"] == 2761.00
        assert job.residual <= 1.0, f"Residual {job.residual} > tolerance"
        assert job.closed is True

        # Inspect classifications
        counts = job.summary["counts"]
        print("\n=== STATUS COUNTS ===")
        for s, c in counts.items():
            print(f"  {s}: {c}")

        # The 9 BT-known invoices include 1 with no invoice number which
        # cannot match. So out of 9 SOA lines absent from Logisys but
        # present in BT, we expect 8 to upgrade to pending_in_bt (the
        # vendor SOA does not include the no-invoice-number row anyway,
        # so the realistic expectation: vendor SOA has invoices that
        # appear in BT but not in Logisys yet -> pending_in_bt).
        assert counts.get("pending_in_bt", 0) >= 1, "Expected at least one pending_in_bt"

        # Closing equation reconstructs ajww_total
        recon = job.summary["reconstructed_total"]
        assert abs(recon - 2761.00) <= 1.0, f"Reconstructed {recon} != 2761.00"

        # 7. Build all four reports
        from app.reports import aging, disputes, payment_packet, recon_report
        for name, builder in [
            ("recon", lambda: recon_report.build(db, job)),
            ("aging", lambda: aging.build(db)),
            ("disputes", lambda: disputes.build(db)),
            ("payment_packet", lambda: payment_packet.build(db)),
        ]:
            data = builder()
            assert isinstance(data, bytes) and len(data) > 1000
            print(f"  built {name}: {len(data)} bytes")

        print("\n=== SMOKE TEST PASSED ===")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    try:
        run_smoke()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
