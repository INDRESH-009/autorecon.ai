"use client";

import { useEffect, useState } from "react";
import { api, type Vendor } from "@/lib/api";
import UploadBox from "@/components/UploadBox";

export default function MasterPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function load() {
    const v = await api.get(`/api/vendors?limit=200${q ? `&q=${encodeURIComponent(q)}` : ""}`);
    setVendors(v);
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);

  async function upload(file: File) {
    const form = new FormData(); form.append("file", file);
    const r = await api.postForm("/api/master/upload", form);
    setStatus(`Master uploaded: ${r.inserted} new, ${r.updated} updated.`);
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Vendor Master</h1>
        <p className="text-sm text-slate-500 mt-1">Credit terms, country, and GL group — seeded from the master sheet.</p>
      </div>

      <UploadBox
        label="Upload Master Sheet"
        hint="Expects sheet 'country' with columns: Organization, CountryName, Paybl_CreditDays, GL Group"
        onUpload={upload}
      />

      {status && <div className="card p-3 text-sm text-green-700 bg-green-50 border-green-200">{status}</div>}

      <div className="card">
        <div className="p-4 border-b flex items-center gap-3">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search vendors…"
            className="px-3 py-1.5 border rounded text-sm w-64"
          />
          <div className="text-sm text-slate-500">{vendors.length} shown</div>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <Th>Organization</Th><Th>Country</Th><Th>Credit Days</Th><Th>GL Group</Th>
            </tr>
          </thead>
          <tbody>
            {vendors.map(v => (
              <tr key={v.id}>
                <Td className="font-medium text-slate-900">{v.organization}</Td>
                <Td>{v.country || "—"}</Td>
                <Td>{v.credit_days}</Td>
                <Td>{v.gl_group || "—"}</Td>
              </tr>
            ))}
            {vendors.length === 0 && (
              <tr><td colSpan={4} className="text-center text-slate-500 py-12 text-sm">No vendors yet. Upload the master sheet to seed.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="text-left font-medium text-slate-500 px-4 py-2 border-b">{children}</th>;
}
function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-2 border-b border-slate-100 ${className}`}>{children}</td>;
}
