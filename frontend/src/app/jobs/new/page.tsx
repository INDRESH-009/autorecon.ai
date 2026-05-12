"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Vendor, type Snapshot } from "@/lib/api";

export default function NewJobPage() {
  const router = useRouter();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [logisys, setLogisys] = useState<Snapshot[]>([]);
  const [bt, setBt] = useState<Snapshot[]>([]);
  const [vendorId, setVendorId] = useState<number | null>(null);
  const [vendorQ, setVendorQ] = useState("");
  const [logId, setLogId] = useState<number | null>(null);
  const [btId, setBtId] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const [vs, ls, bs] = await Promise.all([
        api.get("/api/vendors?limit=10000"),
        api.get("/api/snapshots/logisys"),
        api.get("/api/snapshots/bt"),
      ]);
      setVendors(vs); setLogisys(ls); setBt(bs);
      if (ls.length) setLogId(ls[0].id);
      if (bs.length) setBtId(bs[0].id);
    })();
  }, []);

  const filtered = vendorQ
    ? vendors.filter(v => v.organization.toLowerCase().includes(vendorQ.toLowerCase())).slice(0, 50)
    : vendors.slice(0, 50);

  async function go() {
    if (!vendorId || !logId || !btId || !file) {
      setErr("Pick a vendor, both snapshots, and the SOA file.");
      return;
    }
    setBusy(true); setErr(null);
    try {
      const job = await api.post("/api/jobs", {
        vendor_id: vendorId, logisys_snapshot_id: logId, bt_snapshot_id: btId,
      });
      const fd = new FormData();
      fd.append("file", file);
      // Default header_row=1 (0-indexed) matches vendor_soa_quicklogi.xlsx
      await api.postForm(`/api/jobs/${job.id}/soa`, fd);
      router.push(`/jobs/${job.id}`);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  const selectedVendor = vendors.find(v => v.id === vendorId);

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">New Reconciliation Job</h1>
        <p className="text-sm text-slate-500 mt-1">Pick a vendor, choose snapshots, and upload that vendor's SOA.</p>
      </div>

      <div className="card p-5 space-y-5">
        <div>
          <div className="label mb-1.5">Vendor</div>
          <input
            value={vendorQ}
            onChange={(e) => setVendorQ(e.target.value)}
            placeholder="Type to search…"
            className="w-full px-3 py-2 border rounded text-sm"
          />
          <div className="mt-2 border rounded max-h-56 overflow-y-auto bg-white">
            {filtered.map(v => (
              <button
                key={v.id}
                onClick={() => setVendorId(v.id)}
                className={`w-full text-left px-3 py-1.5 text-sm hover:bg-slate-100 ${vendorId === v.id ? "bg-amber-50 border-l-4 border-amber-400" : ""}`}
              >
                <div className="font-medium">{v.organization}</div>
                <div className="text-xs text-slate-500">{v.country || "—"} · credit {v.credit_days}d · {v.gl_group || "—"}</div>
              </button>
            ))}
            {filtered.length === 0 && <div className="text-sm text-slate-500 px-3 py-3">No matches</div>}
          </div>
          {selectedVendor && (
            <div className="text-sm mt-2 text-slate-700">
              Selected: <span className="font-medium">{selectedVendor.organization}</span> · credit {selectedVendor.credit_days}d
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Logisys snapshot"
            value={logId}
            onChange={setLogId}
            options={logisys.map(s => ({ id: s.id, label: `${s.filename} (${s.row_count} rows)` }))}
          />
          <Select
            label="BT snapshot"
            value={btId}
            onChange={setBtId}
            options={bt.map(s => ({ id: s.id, label: `${s.filename} (${s.row_count} rows)` }))}
          />
        </div>

        <div>
          <div className="label mb-1.5">Vendor SOA (.xlsx)</div>
          <input
            type="file"
            accept=".xlsx,.xlsm"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block text-sm"
          />
          {file && <div className="text-xs text-slate-500 mt-1">{file.name}</div>}
        </div>

        {err && <div className="text-sm text-red-600">{err}</div>}

        <div>
          <button onClick={go} disabled={busy} className="btn-primary">
            {busy ? "Creating…" : "Create Job & Detect Mapping"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Select({
  label, value, onChange, options,
}: {
  label: string; value: number | null; onChange: (n: number | null) => void;
  options: { id: number; label: string }[];
}) {
  return (
    <div>
      <div className="label mb-1.5">{label}</div>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="w-full px-3 py-2 border rounded text-sm bg-white"
      >
        <option value="">— select —</option>
        {options.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
      </select>
    </div>
  );
}
