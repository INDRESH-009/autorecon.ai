"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { api, money, type JobDetail, type MappingSuggest } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

const CANONICAL = ["invoice_no", "invoice_date", "amount"] as const;
const FIELD_LABELS: Record<string, string> = {
  invoice_no: "Invoice Number",
  invoice_date: "Invoice Date",
  amount: "Amount",
};

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [suggest, setSuggest] = useState<MappingSuggest | null>(null);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  async function refresh() {
    const j = await api.get(`/api/jobs/${id}`);
    setJob(j);
  }

  useEffect(() => { refresh(); }, [id]);

  // When the job is in mapping_pending state, fetch suggested mapping by re-uploading? No —
  // the suggestion was returned when the SOA was uploaded. Reconstruct from job.mapping._suggested.
  useEffect(() => {
    if (!job) return;
    if (job.status === "mapping_pending" && job.mapping && job.mapping._suggested) {
      const s = job.mapping._suggested;
      // Collect all candidate headers across fields for a fallback header list
      const headers = Array.from(new Set(
        Object.values(s).flatMap((f: any) => (f.candidates || []).map((c: any) => c.header))
      )) as string[];
      setSuggest({ headers, preview: [], suggested: s, cached: false });
      const init: Record<string, string | null> = {};
      for (const f of CANONICAL) init[f] = s[f]?.header || null;
      setMapping(init);
    }
  }, [job?.status]);

  async function confirm() {
    setBusy(true); setErr(null);
    try {
      const m: Record<string, string> = {};
      for (const f of CANONICAL) if (mapping[f]) m[f] = mapping[f]!;
      const j = await api.post(`/api/jobs/${id}/mapping/confirm`, { mapping: m });
      setJob(j);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function rerun() {
    setBusy(true); setErr(null);
    try {
      const j = await api.post(`/api/jobs/${id}/rerun`);
      setJob(j);
    } catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  }

  const filteredLines = useMemo(() => {
    if (!job) return [];
    if (filter === "all") return job.results;
    return job.results.filter(r => r.status === filter);
  }, [job, filter]);

  if (!job) return <div className="text-sm text-slate-500">Loading job…</div>;

  const counts = (job.summary?.counts || {}) as Record<string, number>;
  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-4">
        <div>
          <div className="text-sm text-slate-500">Job #{job.id} · {job.vendor.country || "—"} · credit {job.vendor.credit_days}d</div>
          <h1 className="text-2xl font-bold">{job.vendor.organization}</h1>
          <div className="text-sm text-slate-500 mt-0.5">{job.vendor.gl_group || "—"}</div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={job.status} />
          {job.status === "reconciled" && (
            <>
              <button onClick={rerun} disabled={busy} className="btn-secondary text-sm">Re-run</button>
              <a className="btn-primary text-sm" href={api.fileUrl(`/api/reports/recon/${job.id}.xlsx`)}>Download Recon</a>
            </>
          )}
        </div>
      </header>

      {err && <div className="card p-3 text-red-600">{err}</div>}

      {job.status === "mapping_pending" && suggest && (
        <div className="card p-5">
          <h2 className="font-semibold mb-1">Confirm Column Mapping</h2>
          <p className="text-sm text-slate-500 mb-4">
            {suggest.cached ? "Loaded from cached mapping for this vendor format. " : ""}
            Auto-detected columns — override any that look wrong, then run reconciliation.
          </p>
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-slate-500">Canonical Field</th>
                <th className="text-left px-3 py-2 font-medium text-slate-500">Suggested</th>
                <th className="text-left px-3 py-2 font-medium text-slate-500">Confidence</th>
                <th className="text-left px-3 py-2 font-medium text-slate-500">Override</th>
              </tr>
            </thead>
            <tbody>
              {CANONICAL.map(f => {
                const s = suggest.suggested[f];
                const candidates = s?.candidates || [];
                const headerOptions = Array.from(new Set([
                  ...candidates.map(c => c.header),
                  ...suggest.headers,
                ])).filter(Boolean) as string[];
                return (
                  <tr key={f} className="border-b border-slate-100">
                    <td className="px-3 py-2 font-medium">{FIELD_LABELS[f]}</td>
                    <td className="px-3 py-2 font-mono text-xs">{s?.header || <span className="text-slate-400">(none)</span>}</td>
                    <td className="px-3 py-2">
                      <Confidence score={s?.score ?? 0} />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={mapping[f] || ""}
                        onChange={(e) => setMapping(prev => ({ ...prev, [f]: e.target.value || null }))}
                        className="px-2 py-1 border rounded text-sm bg-white max-w-[280px]"
                      >
                        <option value="">— pick column —</option>
                        {headerOptions.map(h => <option key={h} value={h}>{h}</option>)}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="mt-4 flex items-center gap-3">
            <button onClick={confirm} disabled={busy} className="btn-primary text-sm">
              {busy ? "Running…" : "Confirm & Reconcile"}
            </button>
            <span className="text-xs text-slate-500">SOA file: {job.soa_filename}</span>
          </div>
        </div>
      )}

      {job.status === "reconciled" && (
        <>
          <div className="grid md:grid-cols-5 gap-3">
            <Stat label="Vendor Total"        value={money(job.summary?.vendor_total)} />
            <Stat label="AJWW Total"          value={money(job.summary?.ajww_total)} />
            <Stat label="Reconstructed"       value={money(job.summary?.reconstructed_total)} />
            <Stat label="Residual"            value={money(job.summary?.residual)} accent={job.closed ? "text-green-600" : "text-red-600"} />
            <Stat label="Closed"              value={job.closed ? "YES" : "NO"} accent={job.closed ? "text-green-600" : "text-red-600"} />
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <FilterPill label={`All (${job.results.length})`} value="all" filter={filter} set={setFilter} />
            {Object.entries(counts).map(([k, v]) => (
              <FilterPill key={k} label={`${k} (${v})`} value={k} filter={filter} set={setFilter} />
            ))}
          </div>

          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  {["Status","Match","Vendor Inv","Vendor Date","Vendor Amt","Age",
                    "AJWW Inv","AJWW Txn","AJWW Date","AJWW Amt","Diff",
                    "BT Label","BT Owner","BT Link"].map(h => (
                    <th key={h} className="text-left px-3 py-2 font-medium text-slate-500 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredLines.map(r => (
                  <tr key={r.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                    <td className="px-3 py-2 text-xs text-slate-500">{r.match_method || ""}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.vendor_inv_no || ""}</td>
                    <td className="px-3 py-2">{r.vendor_date || ""}</td>
                    <td className="px-3 py-2 text-right">{money(r.vendor_amount)}</td>
                    <td className="px-3 py-2 text-right">{r.vendor_age_days ?? ""}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.ajww_inv_no || ""}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.ajww_txn_no || ""}</td>
                    <td className="px-3 py-2">{r.ajww_date || ""}</td>
                    <td className="px-3 py-2 text-right">{money(r.ajww_amount)}</td>
                    <td className="px-3 py-2 text-right">{r.diff !== null && r.diff !== undefined ? money(r.diff) : ""}</td>
                    <td className="px-3 py-2">{r.bt_label || ""}</td>
                    <td className="px-3 py-2 text-xs">{r.bt_owner || ""}</td>
                    <td className="px-3 py-2">
                      {r.bt_link ? <a href={r.bt_link} target="_blank" rel="noreferrer" className="text-amber-600">open</a> : ""}
                    </td>
                  </tr>
                ))}
                {filteredLines.length === 0 && (
                  <tr><td colSpan={14} className="text-center text-slate-500 py-8 text-sm">No lines</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: any; accent?: string }) {
  return (
    <div className="card p-4">
      <div className="label">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${accent || "text-slate-900"}`}>{value}</div>
    </div>
  );
}
function Confidence({ score }: { score: number }) {
  const color = score >= 90 ? "bg-green-500" : score >= 70 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-slate-200 rounded h-1.5">
        <div className={`${color} h-1.5 rounded`} style={{ width: `${Math.max(5, Math.min(100, score))}%` }} />
      </div>
      <span className="text-xs text-slate-500 tabular-nums">{score}</span>
    </div>
  );
}
function FilterPill({ label, value, filter, set }: { label: string; value: string; filter: string; set: (s: string) => void }) {
  const active = filter === value;
  return (
    <button
      onClick={() => set(value)}
      className={`px-3 py-1 rounded-full text-xs font-medium ${active ? "bg-slate-900 text-white" : "bg-white border border-slate-300 hover:bg-slate-100"}`}
    >
      {label}
    </button>
  );
}
