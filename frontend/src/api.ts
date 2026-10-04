import type {
  AiModel, AskResult, Asset, Campaign, Cde, EvidencePack, GateRow, Impact, Issue, Overview, Policy, ReportDetail,
  ReportSummary, ReviewItem, Rule, Scan, SearchHit, SimilarTerm, Suggestion, Task, Term, AuditEvent,
} from "./types";
import { authHeader } from "./auth";

// Empty in development (Vite proxies /api) and in AWS (CloudFront routes /api/* to the ALB).
const BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(await authHeader()), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let msg = `Request failed (${res.status}).`;
    try { const body = await res.json(); if (typeof body.detail === "string") msg = body.detail; } catch { /* not JSON */ }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}
const post = <T>(path: string, body?: unknown) => call<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
const q = (s: string) => encodeURIComponent(s);

export const api = {
  me: () => call<{ name: string; email: string; roles: string[] }>("/api/me"),
  overview: () => call<Overview>("/api/overview"),

  reports: () => call<ReportSummary[]>("/api/reports"),
  report: (id: string) => call<ReportDetail>(`/api/reports/${q(id)}`),
  signOff: (reportId: string, edgeId: number) => post<{ completeness: number }>(`/api/reports/${q(reportId)}/edges/${edgeId}/signoff`),
  impact: (reportId: string, nodeId: string) => call<Impact>(`/api/reports/${q(reportId)}/nodes/${q(nodeId)}/impact`),
  evidencePack: (reportId: string) => post<EvidencePack>(`/api/reports/${q(reportId)}/evidence-pack`),

  rules: () => call<Rule[]>("/api/quality/rules"),
  runRules: () => post<{ opened: string[] }>("/api/quality/run"),
  issues: () => call<Issue[]>("/api/quality/issues"),
  resolveIssue: (id: string) => post<Issue>(`/api/quality/issues/${q(id)}/resolve`),
  gates: () => call<GateRow[]>("/api/quality/gates"),

  assets: (search = "") => call<Asset[]>(`/api/catalog/assets?q=${q(search)}`),
  assignOwner: (assetId: number, owner: string) => post<Asset>(`/api/catalog/assets/${assetId}/owner`, { owner }),
  cdes: () => call<Cde[]>("/api/catalog/cdes"),
  glossary: () => call<Term[]>("/api/catalog/glossary"),
  similarTerms: (text: string) => call<SimilarTerm[]>(`/api/catalog/glossary/similar?text=${q(text)}`),
  approveTerm: (id: number) => post<Term>(`/api/catalog/glossary/${id}/approve`),

  scans: () => call<Scan[]>("/api/access/scans"),
  decideScan: (id: string, status: "Confirmed" | "Rejected") => post<Scan>(`/api/access/scans/${q(id)}`, { status }),
  suggestLabel: (column: string, description = "") => post<Suggestion>("/api/access/suggest-classification", { column, description }),
  policies: () => call<Policy[]>("/api/access/policies"),
  togglePolicy: (id: string) => post<Policy>(`/api/access/policies/${q(id)}/toggle`),

  campaigns: () => call<Campaign[]>("/api/recert/campaigns"),
  inbox: () => call<ReviewItem[]>("/api/recert/inbox"),
  decide: (id: string, keep: boolean, note: string) => post<ReviewItem>(`/api/recert/items/${q(id)}/decision`, { keep, note }),
  seal: (id: string) => post<Campaign>(`/api/recert/campaigns/${q(id)}/seal`),
  tasks: () => call<Task[]>("/api/recert/tasks"),

  models: () => call<AiModel[]>("/api/ai/models"),
  modelAction: (id: string, action: "fairness-test" | "mitigate" | "evaluate" | "approve" | "pause" | "revalidate") =>
    post<AiModel>(`/api/ai/models/${q(id)}/${action}`),

  audit: () => call<{ intact: boolean; firstBrokenId: number | null; events: AuditEvent[] }>("/api/audit"),
  search: (text: string) => call<{ query: string; results: SearchHit[] }>(`/api/search?q=${q(text)}`),
  ask: (question: string) => post<AskResult>("/api/ask", { question }),
};
