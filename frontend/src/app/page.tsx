"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, money, type JobBrief, type Vendor, type Snapshot } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobBrief[]>([]);
  const [vendors, setVendors] = useState<Record<number, Vendor>>({});
  const [logisys, setLogisys] = useState<Snapshot[]>([]);
  const [bt, setBt] = useState<Snapshot[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [j, vs, ls, bs] = await Promise.all([
          api.get("/api/jobs"),
          api.get("/api/vendors?limit=10000"),
          api.get("/api/snapshots/logisys"),
          api.get("/api/snapshots/bt"),
        ]);
        setJobs(j); setLogisys(ls); setBt(bs);
        const m: Record<number, Vendor> = {};
        for (const v of vs as Vendor[]) m[v.id] = v;
        setVendors(m);
      } catch (e: any) { setErr(e.message); }
    })();
  }, []);

  const open = jobs.filter(j => j.status !== "reconciled");
  const closed = jobs.filter(j => j.status === "reconciled");
  const residualUnsolved = closed.filter(j => !j.closed);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">AJ Worldwide vendor reconciliation</p>
      </div>

      {err && <div className="card p-4 text-red-600">{err}</div>}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Stat label="Vendors" value={Object.keys(vendors).length} />
        <Stat label="Logisys Snapshots" value={logisys.length} />
        <Stat label="BT Snapshots" value={bt.length} />
        <Stat label="Recon Jobs" value={jobs.length} />
      </div>

      <Section title="Jobs needing attention" empty="No open jobs.">
        {open.length > 0 && (
          <Table>
            <thead>
              <tr><Th>ID</Th><Th>Vendor</Th><Th>Status</Th><Th>Created</Th><Th></Th></tr>
            </thead>
            <tbody>
              {open.map(j => (
                <tr key={j.id}>
                  <Td>{j.id}</Td>
                  <Td className="font-medium">{vendors[j.vendor_id]?.organization || "—"}</Td>
                  <Td><StatusBadge status={j.status} /></Td>
                  <Td>{new Date(j.created_at).toLocaleString()}</Td>
                  <Td><Link className="text-amber-600 font-medium" href={`/jobs/${j.id}`}>Open →</Link></Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Section>

      {residualUnsolved.length > 0 && (
        <Section title="Residuals not closing" empty="">
          <Table>
            <thead>
              <tr><Th>ID</Th><Th>Vendor</Th><Th>Residual</Th><Th></Th></tr>
            </thead>
            <tbody>
              {residualUnsolved.map(j => (
                <tr key={j.id}>
                  <Td>{j.id}</Td>
                  <Td className="font-medium">{vendors[j.vendor_id]?.organization || "—"}</Td>
                  <Td className="text-red-600">{money(j.residual)}</Td>
                  <Td><Link className="text-amber-600 font-medium" href={`/jobs/${j.id}`}>Open →</Link></Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Section>
      )}

      <Section title="Recently reconciled" empty="No reconciled jobs yet.">
        {closed.length > 0 && (
          <Table>
            <thead>
              <tr><Th>ID</Th><Th>Vendor</Th><Th>Residual</Th><Th>Closed</Th><Th></Th></tr>
            </thead>
            <tbody>
              {closed.slice(0, 20).map(j => (
                <tr key={j.id}>
                  <Td>{j.id}</Td>
                  <Td className="font-medium">{vendors[j.vendor_id]?.organization || "—"}</Td>
                  <Td>{money(j.residual)}</Td>
                  <Td>{j.closed ? <span className="text-green-600 font-medium">YES</span> : <span className="text-red-600 font-medium">NO</span>}</Td>
                  <Td><Link className="text-amber-600 font-medium" href={`/jobs/${j.id}`}>Open →</Link></Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="card p-5">
      <div className="label">{label}</div>
      <div className="text-3xl font-bold mt-1 text-slate-900">{value}</div>
    </div>
  );
}
function Section({ title, children, empty }: { title: string; children: React.ReactNode; empty: string }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900 mb-3">{title}</h2>
      <div className="card overflow-hidden">
        {children || <div className="p-6 text-sm text-slate-500">{empty}</div>}
      </div>
    </div>
  );
}
function Table({ children }: { children: React.ReactNode }) {
  return <table className="w-full text-sm">{children}</table>;
}
function Th({ children }: { children?: React.ReactNode }) {
  return <th className="text-left font-medium text-slate-500 px-4 py-3 border-b">{children}</th>;
}
function Td({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-3 border-b border-slate-100 ${className}`}>{children}</td>;
}
