# Recon Platform — AJWW MVP

Reconciliation platform for AJ Worldwide. Replaces the manual Excel-based AP
workflow where accountants reconcile vendor SOAs against Logisys (book of
record) with Bravotran (BT) waiting-queue context.

The canonical test case is Quick Logistics LLC US — recon must close at
residual = 0 against the four real files in `sample_data/`.

## Stack

- **Backend** — FastAPI 0.115 + SQLAlchemy 2.0 + SQLite, openpyxl for Excel I/O,
  rapidfuzz for column mapping
- **Frontend** — Next.js 14 (App Router) + TypeScript + Tailwind, no UI library
- **Storage** — `backend/recon.db` (SQLite), uploads in `backend/storage/`

## Quick start

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev      # serves on http://localhost:3000
```

The frontend rewrites `/api/*` to `http://127.0.0.1:8000/api/*` (see
`frontend/next.config.js`), so no CORS dance needed in dev.

## Workflow (mirrors AP team's existing process)

1. **Vendor Master** — upload `credit_country.xlsx` to seed ~3,700 vendors
   with country, credit terms, GL group.
2. **Snapshots** — upload `logisys_dump.xlsx` and `bt_dump_quick.xlsx` once
   per period. Both cover all vendors.
3. **New Job** — pick vendor + both snapshots + that vendor's SOA. System
   auto-detects column mapping.
4. **Confirm mapping** — accountant reviews suggestion, overrides if needed,
   clicks Reconcile. Mapping is cached by (vendor, header signature) so
   repeat uploads need no re-confirmation.
5. **Recon view** — classified lines with filters, residual check, downloadable
   Excel report mirroring the AP team's `VENDOR SOA` tab layout.
6. **Reports** — aging summary, dispute log, payment release packet across
   all reconciled jobs.

## Recon algorithm

- **Pass 1** — exact match on `(normalize_invno(inv), round(amount, 2))`.
- **Pass 2** — same normalized invoice no, amount within tolerance
  (`max($0.50, 0.5% of amount)`).
- **Classification of unmatched vendor lines** — look up by (vendor name,
  normalized inv no) in BT; if found → `pending_in_bt` with label/note/link/
  owner attached; otherwise → `to_be_booked`.
- **AJWW-only lines** → `missing_in_vendor`.
- **Matched lines** — `ok_to_pay` if age ≥ credit term, else `not_due`.
- **Pass 2 with non-zero diff** → `amount_dispute`.

### Closing equation

```
reconstructed = vendor_total
              + sum(missing_in_vendor)
              - sum(to_be_booked + pending_in_bt)
              - sum(paid)
              + sum(amount_dispute.diff)
residual      = abs(ajww_total - reconstructed)
closed        = residual <= $1.00
```

For Quick Logistics the math closes exactly:
`4,609.83 + 170.00 − (1,678.83 + 340.00) = 2,761.00 = AJWW total`.

## Smoke test

End-to-end against the real files:

```bash
cd backend
PYTHONPATH=. python ../tests/test_smoke.py
```

Asserts residual = 0, expected line counts (21 Logisys, 9 BT, 34 SOA, 18
ok_to_pay, 2 not_due, 3 pending_in_bt, 11 to_be_booked, 1 missing_in_vendor),
and that all four Excel reports build.

## Hard-won details encoded in the code

- **`extraction/coerce.py:jsonable()`** — coerces `datetime`/`date`/`Decimal`
  before anything hits a `JSON` column. Without this, SQLAlchemy's `json.dumps`
  blows up.
- **Logisys header row** — `header_row=2` (rows 0-1 are preamble); rows with
  `Organization` in `{"Total", "Vendor Invoices Pending Write Off."}` are
  summary rows and must be filtered.
- **BT canonical owner** — `Request Sent To` column, NOT `Request Sent To.1`
  (the latter is a duplicate caused by Excel autonaming when the column
  appears twice).
- **`normalize_invno`** — must coerce `17904.0` (float-from-openpyxl) →
  `"17904"`, otherwise the canonical join key fails silently and everything
  ends up unmatched.
- **Negative keyword filter in mapping** — the AP team's `VENDOR SOA` tab has
  14 helper columns (`Look up`, `Concan`, `Ageing`, etc.) that look like
  candidates to a fuzzy matcher. They're explicitly excluded.
- **Global FastAPI exception handler** — returns JSON with CORS headers so
  the browser shows the real 500 instead of "Failed to fetch".

## What's deferred

PDF SOA ingestion, multi-file SOA merge, payment-ledger lookup for `paid`
status, vendor alias resolution, LLM column mapping (Layer 2 + rapidfuzz
covers these files), email inbox ingestion, auth, Postgres + Alembic, batch
recon all vendors at once.

## Project layout

```
backend/app/
  core/config.py           settings (residual_tolerance, amount tolerances)
  db/
    session.py             engine + Base + get_db
    models.py              Vendor, LogisysSnapshot, LogisysLine,
                           BTSnapshot, BTLine, ReconJob, UploadedSOA,
                           ReconLineResult, VendorMappingCache
  extraction/              file bytes → (headers, rows) — generic
    types.py, coerce.py, xlsx.py, csv.py, pdf.py, __init__.py
  ingestion/               format-specific parsers for the 3 real inputs
    master_sheet.py, logisys.py, bt.py
  mapping/
    dictionary.py          canonical fields + alias library + negative keywords
    resolver.py            fuzzy + data-shape mapping suggestion
    apply.py               raw rows × confirmed mapping → canonical SOA rows
  recon/
    normalize.py           invoice number + amount canonicalization
    engine.py              Pass 1 + Pass 2 + closing equation
    classifier.py          BT-aware: to_be_booked → pending_in_bt
    runner.py              orchestrate: load + recon + classify + persist
  reports/
    excel_export.py        openpyxl styling helpers
    recon_report.py        per-vendor recon report (mirrors VENDOR SOA tab)
    aging.py               aging summary across all reconciled jobs
    disputes.py            dispute log
    payment_packet.py      payment release packet
  api/
    master.py, vendors.py, snapshots.py, jobs.py, reports.py
  schemas/__init__.py      Pydantic models
  main.py                  FastAPI app + global exception handler

frontend/src/app/
  page.tsx                 Dashboard: open + reconciled jobs, residuals
  master/page.tsx          Vendor master + upload
  snapshots/page.tsx       List + upload Logisys + BT
  jobs/new/page.tsx        Create job (vendor + snapshots + SOA)
  jobs/[id]/page.tsx       Mapping confirm + recon view
  reports/page.tsx         Download aging / disputes / packet
```
