import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import { authEnabled, signOut } from "./auth";
import { useLoad } from "./components/ui";
import Access from "./pages/Access";
import AiGovernance from "./pages/AiGovernance";
import Audit from "./pages/Audit";
import Catalog from "./pages/Catalog";
import Lineage from "./pages/Lineage";
import OverviewPage from "./pages/Overview";
import Payments from "./pages/Payments";
import Quality from "./pages/Quality";
import Recert from "./pages/Recert";
import Search from "./pages/Search";

const NAV: { to: string; label: string; group: string; badge?: "issues" | "reviews" | "models" }[] = [
  { to: "/", label: "Overview", group: "Console" },
  { to: "/search", label: "Ask Aegis", group: "Console" },
  { to: "/payments", label: "Payment rails", group: "Console" },
  { to: "/lineage", label: "Lineage", group: "Pillars" },
  { to: "/quality", label: "Data quality", group: "Pillars", badge: "issues" },
  { to: "/catalog", label: "Catalog", group: "Pillars" },
  { to: "/access", label: "Access & privacy", group: "Pillars" },
  { to: "/recert", label: "Recertification", group: "Pillars", badge: "reviews" },
  { to: "/ai", label: "AI governance", group: "Pillars", badge: "models" },
  { to: "/audit", label: "Audit log", group: "Evidence" },
];

export default function App() {
  const loc = useLocation();
  // Badge counts refresh on every navigation.
  const { data: ov } = useLoad(api.overview, [loc.pathname]);
  const { data: me } = useLoad(api.me);
  const badges = {
    issues: ov?.kpis.openIssues ?? 0,
    reviews: ov?.kpis.openReviews ?? 0,
    models: ov?.kpis.modelsWithAlerts ?? 0,
  };
  let group = "";
  return (
    <div className="app">
      <aside className="rail">
        <div className="brand">
          <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
            <path d="M14 2 25 6v8c0 6.4-4.6 10.6-11 12C7.6 24.6 3 20.4 3 14V6z" fill="var(--accent)" />
            <path d="M9 14.5l3.2 3.2L19.5 10" stroke="var(--on-accent)" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div><b>Aegis</b><small>Data and AI governance</small></div>
        </div>
        <nav className="nav" aria-label="Sections">
          {NAV.map((n) => {
            const head = n.group !== group ? <div className="grp" key={`g-${n.group}`}>{n.group}</div> : null;
            group = n.group;
            const count = n.badge ? badges[n.badge] : 0;
            return [head, (
              <NavLink key={n.to} to={n.to} end={n.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
                <span>{n.label}</span>{count > 0 && <span className="count">{count}</span>}
              </NavLink>
            )];
          })}
        </nav>
        <div className="who"><b>{me?.name ?? "…"}</b>{me && me.roles.length > 0 && <div>{me.roles.join(", ")}</div>}{authEnabled ? <button className="btn sm" style={{ marginTop: 8 }} onClick={signOut}>Sign out</button> : "Local dev mode"}</div>
      </aside>
      <main>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/search" element={<Search />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/payments/:railId" element={<Payments />} />
          <Route path="/lineage" element={<Lineage />} />
          <Route path="/lineage/:reportId" element={<Lineage />} />
          <Route path="/quality" element={<Quality />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/access" element={<Access />} />
          <Route path="/recert" element={<Recert />} />
          <Route path="/ai" element={<AiGovernance />} />
          <Route path="/ai/:modelId" element={<AiGovernance />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="*" element={<p>That page does not exist. Use the menu to pick a section.</p>} />
        </Routes>
      </main>
    </div>
  );
}
