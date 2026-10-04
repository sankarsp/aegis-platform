import { api } from "../api";
import { Loading, PageHead, Pill, useLoad } from "../components/ui";

export default function Audit() {
  const { data, error } = useLoad(api.audit);
  if (!data) return <Loading error={error} />;
  return (
    <>
      <PageHead title="Audit log" intro="Every decision and change, append-only. Each entry carries the hash of the one before it, so any edit to history breaks the chain."
        actions={data.intact ? <Pill tone="good">Chain verified</Pill> : <Pill tone="crit">Chain broken at event {data.firstBrokenId}</Pill>} />
      <section className="panel"><div className="tbl"><table>
        <thead><tr><th>Time (UTC)</th><th>Who</th><th>Action</th><th>Object</th><th>Hash</th></tr></thead>
        <tbody>{data.events.map((e) => (
          <tr key={e.id}><td className="mono muted" style={{ whiteSpace: "nowrap" }}>{e.ts}</td><td style={{ whiteSpace: "nowrap" }}><b>{e.actor}</b></td>
            <td>{e.action}</td><td className="mono">{e.object}</td><td className="mono muted" title={e.hash}>{e.hash.slice(0, 10)}…</td></tr>
        ))}</tbody>
      </table></div></section>
    </>
  );
}
