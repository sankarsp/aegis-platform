import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { Status } from "../types";

/* ---------- Data loading ---------- */
export function useLoad<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadRef = useRef(load);
  loadRef.current = load;
  const reload = useCallback(() => {
    loadRef.current().then((d) => { setData(d); setError(null); }).catch((e: Error) => setError(e.message));
  }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(reload, deps);
  return { data, error, reload, setData };
}

export function Loading({ error }: { error?: string | null }) {
  if (error) return <div className="error" role="alert">Could not load this page: {error} Check that the API is running, then reload.</div>;
  return <div className="spinner">Loading…</div>;
}

/* ---------- Toasts ---------- */
const ToastCtx = createContext<(msg: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null);
  const timer = useRef<number>();
  const show = useCallback((m: string) => {
    setMsg(m);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setMsg(null), 2800);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {msg && <div className="toast" role="status">{msg}</div>}
    </ToastCtx.Provider>
  );
}

/** Runs an API action, shows its message or error, then refreshes. */
export function useAction() {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const run = useCallback(async <T,>(fn: () => Promise<T>, done?: (r: T) => string | void, after?: () => void) => {
    setBusy(true);
    try {
      const r = await fn();
      const m = done?.(r);
      if (m) toast(m);
      after?.();
      return r;
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [toast]);
  return { run, busy };
}

/* ---------- Small components ---------- */
export function Pill({ tone = "", children }: { tone?: "" | "good" | "warn" | "crit" | "info"; children: ReactNode }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

export function StatusPill({ status }: { status: Status }) {
  if (status === "pass") return <Pill tone="good">Pass</Pill>;
  if (status === "warn") return <Pill tone="warn">Warning</Pill>;
  return <Pill tone="crit">Breach</Pill>;
}

export function ClassTag({ cls }: { cls: string }) {
  const k = cls === "PII" ? "pii" : cls === "PCI" ? "pci" : cls === "Confidential" ? "conf" : "";
  return <span className={`tag ${k}`}>{cls}</span>;
}

export function Bar({ pct, tone = "" }: { pct: number; tone?: string }) {
  return <div className="bar"><i className={tone} style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} /></div>;
}

export function Kpi({ label, value, unit, sub, pct, tone }: { label: string; value: ReactNode; unit?: string; sub: string; pct?: number; tone?: string }) {
  return (
    <div className="kpi">
      <span className="eyebrow">{label}</span>
      <span className="v">{value}{unit && <small>{unit}</small>}</span>
      {pct !== undefined && <Bar pct={pct} tone={tone} />}
      <span className="s">{sub}</span>
    </div>
  );
}

export function PageHead({ title, intro, actions }: { title: string; intro: string; actions?: ReactNode }) {
  return (
    <div className="head">
      <div><h1>{title}</h1><p>{intro}</p></div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="card" role="dialog" aria-modal="true" aria-label={title}>
        <h2 style={{ fontSize: 17 }}>{title}</h2>
        {children}
        <div className="row"><button className="btn" onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
}

export function copyText(text: string, toast: (m: string) => void) {
  navigator.clipboard?.writeText(text).then(() => toast("Copied to clipboard"), () => toast("Copy is blocked here; select the text instead."));
}
