"use client";

import { useRef, useState } from "react";

type Props = {
  label: string;
  hint?: string;
  accept?: string;
  onUpload: (file: File) => Promise<void>;
};

export default function UploadBox({ label, hint, accept = ".xlsx,.xlsm", onUpload }: Props) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  async function go(file: File) {
    setBusy(true); setErr(null);
    try { await onUpload(file); }
    catch (e: any) { setErr(e.message || String(e)); }
    finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold text-slate-900">{label}</div>
          {hint && <div className="text-sm text-slate-500 mt-0.5">{hint}</div>}
        </div>
      </div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragging(false);
          const f = e.dataTransfer.files?.[0]; if (f) go(f);
        }}
        className={`mt-4 border-2 border-dashed rounded-md py-8 px-4 text-center cursor-pointer transition
          ${dragging ? "border-amber-400 bg-amber-50" : "border-slate-300 hover:border-slate-400"}`}
        onClick={() => ref.current?.click()}
      >
        <input
          ref={ref}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) go(f); }}
        />
        <div className="text-sm text-slate-600">
          {busy ? "Uploading…" : <>Drop file here or <span className="text-amber-600 font-medium">browse</span></>}
        </div>
        <div className="text-xs text-slate-400 mt-1">{accept}</div>
      </div>
      {err && <div className="mt-3 text-sm text-red-600">{err}</div>}
    </div>
  );
}
