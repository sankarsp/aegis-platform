export type Status = "pass" | "warn" | "breach";
export type Level = "crit" | "warn" | "info";

export interface Gate { held: boolean; breached_cdes: string[] }
export interface ReportSummary { id: string; name: string; regulation: string; cadence: string; owner?: string; gate: Gate; completeness: number }
export interface AuditEvent { id: number; ts: string; actor: string; action: string; object: string; hash: string }
export interface Attention { level: Level; title: string; detail: string; go: string }

export interface Overview {
  kpis: {
    lineageCoverage: number; dataQuality: number; cdesOwned: number; cdesTotal: number;
    recertDone: number; recertTotal: number; openIssues: number; criticalIssues: number; openReviews: number;
    models: number; modelsWithAlerts: number;
  };
  qualityTrend: number[];
  attention: Attention[];
  reports: ReportSummary[];
  recentActivity: AuditEvent[];
  auditChainIntact: boolean;
}

export interface Cde {
  id: string; name: string; domain: string; owner: string | null; formerOwner: string | null; steward: string;
  lineagePct: number; classification: string; attested: string; quality: number | null; status: Status;
}
export interface LineageNode {
  id: string; label: string; sub: string; col: number; row: number; isReport: boolean; isEuc: boolean;
  owner: string; cdeIds: string[]; controls: string[]; status: Status | "none";
}
export interface LineageEdge { id: number; source: string; target: string; kind: "auto" | "manual" | "signed"; signedBy: string | null }
export interface ReportDetail extends ReportSummary {
  principles: Record<string, number>; cdes: Cde[]; nodes: LineageNode[]; edges: LineageEdge[];
}
export interface Impact { node: string; downstream: string[]; otherReports: string[] }
export interface EvidencePack { id: string; sha256: string; text: string }

export interface Rule { id: string; name: string; cdeId: string; dimension: string; threshold: number; lastValue: number; status: Status }
export interface Issue { id: string; ruleId: string; cdeId: string; severity: string; owner: string; opened: string; due: string; status: string; note: string }
export interface GateRow extends Gate { reportId: string; name: string }

export interface Asset {
  id: number; name: string; platform: string; domain: string; owner: string | null; formerOwner: string | null;
  steward: string; classification: string; certified: boolean; term: string; cdeIds: string[]; usage: string;
  qualityOk: boolean; manualLineage: boolean;
}
export interface Term { id: number; term: string; definition: string; owner: string; status: string; version: string; proposedChange: string | null }
export interface SimilarTerm { termId: number; term: string; definition: string; score: number }

export interface Scan { id: string; column: string; dataset: string; label: string; confidence: number; status: "Proposed" | "Confirmed" | "Rejected" }
export interface Policy { id: string; name: string; rule: string; scope: string; mode: "Enforced" | "Monitor only" }
export interface Suggestion { suggestion: string | null; confidence?: number; neighbours: { column: string; label: string; score: number }[]; note?: string }

export interface Campaign { id: string; name: string; type: string; due: string; total: number; done: number; sealed: boolean; evidenceId: string | null; canSeal: boolean }
export interface Decision { keep: boolean; label: string; by: string; at: string; note: string }
export interface ReviewItem {
  id: string; campaignId: string; reviewer: string; kind: string; title: string; tag: string; context: string[];
  recommendation: string; keepLabel: string; dropLabel: string; decision: Decision | null;
}
export interface Task { id: number; title: string; assignee: string; due: string; status: string; source: string }

export interface ModelAlert { level: Level; text: string }
export interface AiModel {
  id: string; name: string; version: string; use: string; type: string; source: string; tier: "High" | "Medium" | "Low";
  stage: string; owner: string; validator: string; validated: string; nextValidation: string; regulations: string[];
  dataCdes: { id: string; status: Status }[];
  fairness: { group: string; value: number }[] | null;
  performance: { metric: string; value: number; baseline: number } | null;
  psi: number | null;
  llmEvals: { name: string; value: number; target: number }[] | null;
  explainability: string; approvals: { step: string; approved: boolean; by?: string }[]; controls: string[]; alerts: ModelAlert[];
}

export interface SearchHit { kind: string; refId: string; title: string; body: string; score: number }
export interface AskResult { question: string; answer: string | null; sources: SearchHit[] }
