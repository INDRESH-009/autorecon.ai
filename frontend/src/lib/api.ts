"use client";

const BASE = "";

async function handle(res: Response) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      try { detail = await res.text(); } catch {}
    }
    throw new Error(detail);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

export const api = {
  get: (path: string) => fetch(`${BASE}${path}`, { cache: "no-store" }).then(handle),
  post: (path: string, body?: any) =>
    fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
    }).then(handle),
  postForm: (path: string, form: FormData) =>
    fetch(`${BASE}${path}`, { method: "POST", body: form, cache: "no-store" }).then(handle),
  fileUrl: (path: string) => `${BASE}${path}`,
};

export type Vendor = {
  id: number; organization: string; country: string | null;
  credit_days: number; gl_group: string | null;
};
export type Snapshot = { id: number; filename: string; uploaded_at: string; row_count: number };
export type JobBrief = {
  id: number; vendor_id: number; logisys_snapshot_id: number; bt_snapshot_id: number;
  status: string; residual: number | null; closed: boolean | null;
  created_at: string; updated_at: string;
};
export type MappingCandidate = { header: string; score: number };
export type MappingField = { header: string | null; score: number; candidates: MappingCandidate[] };
export type MappingSuggest = {
  headers: string[]; preview: any[]; suggested: Record<string, MappingField>; cached: boolean;
};
export type ReconLine = {
  id: number; status: string; match_method: string | null;
  vendor_inv_no: string | null; vendor_date: string | null;
  vendor_amount: number | null; vendor_age_days: number | null;
  ajww_inv_no: string | null; ajww_txn_no: string | null;
  ajww_date: string | null; ajww_amount: number | null; diff: number | null;
  bt_label: string | null; bt_labels: string | null;
  bt_note: string | null; bt_link: string | null; bt_owner: string | null;
};
export type JobDetail = {
  id: number; status: string; residual: number | null; closed: boolean | null;
  summary: Record<string, any> | null;
  vendor: Vendor; logisys_snapshot: Snapshot; bt_snapshot: Snapshot;
  results: ReconLine[]; mapping: Record<string, any> | null; soa_filename: string | null;
};

export function money(n: number | null | undefined) {
  if (n === null || n === undefined) return "";
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
