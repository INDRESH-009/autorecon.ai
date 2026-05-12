"""Ingest the vendor master sheet (credit_country format).

Last-write-wins on duplicate Organization within the same upload — the master
sheet in the wild has a handful of repeated rows (same org listed under multiple
country contexts).
"""
from sqlalchemy.orm import Session

from app.db import models
from app.extraction import extract_file


def ingest_master(db: Session, path):
    table = extract_file(path, sheet_name="country", header_row=0)

    # Collapse duplicates within this batch first
    by_org: dict = {}
    for row in table.rows:
        org_raw = row.get("Organization")
        if not isinstance(org_raw, str):
            continue
        org = org_raw.strip()
        if not org:
            continue
        country = row.get("CountryName")
        if isinstance(country, str):
            country = country.strip() or None
        credit_raw = row.get("Paybl_CreditDays")
        try:
            credit = int(float(credit_raw)) if credit_raw is not None else 0
        except (TypeError, ValueError):
            credit = 0
        gl = row.get("GL Group")
        if isinstance(gl, str):
            gl = gl.strip() or None
        by_org[org] = (country, credit, gl)

    # Pull existing vendors in one query
    existing_map = {v.organization: v for v in db.query(models.Vendor).all()}

    inserts = 0
    updates = 0
    for org, (country, credit, gl) in by_org.items():
        v = existing_map.get(org)
        if v is None:
            db.add(models.Vendor(organization=org, country=country, credit_days=credit, gl_group=gl))
            inserts += 1
        else:
            v.country = country
            v.credit_days = credit
            v.gl_group = gl
            updates += 1
    db.commit()
    return {"inserted": inserts, "updated": updates, "total_rows": len(table.rows)}
