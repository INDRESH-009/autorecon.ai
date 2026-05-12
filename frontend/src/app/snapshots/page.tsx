"use client";

import { useEffect, useState } from "react";
import { api, type Snapshot } from "@/lib/api";
import UploadBox from "@/components/UploadBox";

export default function SnapshotsPage() {
  const [logisys, setLogisys] = useState<Snapshot[]>([]);
  const [bt, setBt] = useState<Snapshot[]>([]);

  async function load() {
    const [l, b] = await Promise.all([
      api.get("/api/snapshots/logisys"),
      api.get("/api/snapshots/bt"),
    ]);
    setLogisys(l); setBt(b);
  }
  useEffect(() => { load(); }, []);

  async function uploadLogisys(f: File) {
    const fd = new FormData(); fd.append("file", f);
    await api.postForm("/api/snapshots/logisys", fd);
    await load();
  }
  async function uploadBt(f: File) {
    const fd = new FormData(); fd.append("file", f);
    await api.postForm("/api/snapshots/bt", fd);
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Snapshots</h1>
        <p className="text-sm text-slate-500 mt-1">Logisys (book of record) and Bravotran (waiting queue) dumps.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        <UploadBox
          label="Logisys dump"
          hint="Expects sheet 'AJWW LOGYSIS SOA' with header on row 3."
          onUpload={uploadLogisys}
        />
        <UploadBox
          label="Bravotran (BT) dump"
          hint="Expects sheet 'Waiting'."
          onUpload={uploadBt}
        />
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        <SnapshotList title="Logisys snapshots" items={logisys} />
        <SnapshotList title="BT snapshots" items={bt} />
      </div>
    </div>
  );
}

function SnapshotList({ title, items }: { title: string; items: Snapshot[] }) {
  return (
    <div className="card">
      <div className="px-4 py-3 border-b font-semibold">{title}</div>
      <table className="w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="text-left px-4 py-2 font-medium text-slate-500">ID</th>
            <th className="text-left px-4 py-2 font-medium text-slate-500">Filename</th>
            <th className="text-left px-4 py-2 font-medium text-slate-500">Rows</th>
            <th className="text-left px-4 py-2 font-medium text-slate-500">Uploaded</th>
          </tr>
        </thead>
        <tbody>
          {items.map(s => (
            <tr key={s.id}>
              <td className="px-4 py-2 border-b border-slate-100">{s.id}</td>
              <td className="px-4 py-2 border-b border-slate-100 font-medium">{s.filename}</td>
              <td className="px-4 py-2 border-b border-slate-100">{s.row_count}</td>
              <td className="px-4 py-2 border-b border-slate-100 text-slate-500">{new Date(s.uploaded_at).toLocaleString()}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={4} className="text-center text-slate-500 py-8 text-sm">None uploaded yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
