"use client";

import { api } from "@/lib/api";

const REPORTS = [
  {
    name: "Aging Summary",
    desc: "Per vendor across all reconciled jobs: 0-30, 31-60, 61-90, 90+ buckets.",
    href: "/api/reports/aging.xlsx",
  },
  {
    name: "Dispute Log",
    desc: "Lines flagged pending_in_bt or amount_dispute, with BT context.",
    href: "/api/reports/disputes.xlsx",
  },
  {
    name: "Payment Release Packet",
    desc: "ok_to_pay lines grouped by vendor, with subtotals.",
    href: "/api/reports/payment_packet.xlsx",
  },
];

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Reports</h1>
        <p className="text-sm text-slate-500 mt-1">Generated from all reconciled jobs. Each exports an Excel file.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {REPORTS.map(r => (
          <div key={r.name} className="card p-5 flex flex-col">
            <div className="font-semibold text-slate-900">{r.name}</div>
            <div className="text-sm text-slate-500 mt-1 flex-1">{r.desc}</div>
            <a href={api.fileUrl(r.href)} className="btn-primary text-sm self-start mt-4">Download .xlsx</a>
          </div>
        ))}
      </div>

      <div className="card p-5">
        <div className="font-semibold mb-1">Per-vendor recon reports</div>
        <p className="text-sm text-slate-500">
          Open a specific job from the <a href="/" className="text-amber-600">Dashboard</a> and click <em>Download Recon</em> in the header.
        </p>
      </div>
    </div>
  );
}
