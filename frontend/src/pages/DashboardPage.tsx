import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Dashboard } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  sap: "SAP",
  utility: "Utility",
  travel: "Travel",
};

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);

  useEffect(() => {
    api<Dashboard>("/dashboard/").then(setData);
  }, []);

  if (!data) return <p>Loading dashboard…</p>;

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total rows</div>
          <div className="value">{data.total_activities}</div>
        </div>
        <div className="stat-card">
          <div className="label">Pending</div>
          <div className="value">{data.pending}</div>
        </div>
        <div className="stat-card flagged">
          <div className="label">Flagged</div>
          <div className="value">{data.flagged}</div>
        </div>
        <div className="stat-card failed">
          <div className="label">Failed</div>
          <div className="value">{data.failed}</div>
        </div>
        <div className="stat-card approved">
          <div className="label">Approved</div>
          <div className="value">{data.approved}</div>
        </div>
        <div className="stat-card">
          <div className="label">Locked</div>
          <div className="value">{data.locked}</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h2>By GHG scope</h2>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "var(--muted)" }}>
            {Object.entries(data.by_scope).map(([scope, count]) => (
              <li key={scope}>
                Scope {scope}: <strong style={{ color: "var(--text)" }}>{count}</strong>
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2>By source</h2>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "var(--muted)" }}>
            {Object.entries(data.by_source).map(([src, count]) => (
              <li key={src}>
                {SOURCE_LABELS[src] || src}: <strong style={{ color: "var(--text)" }}>{count}</strong>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <h2>Recent ingestion batches</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Source</th>
                <th>Status</th>
                <th>Rows</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_batches.map((b) => (
                <tr key={b.id}>
                  <td>{b.filename}</td>
                  <td>{SOURCE_LABELS[b.source_type] || b.source_type}</td>
                  <td>{b.status}</td>
                  <td>
                    {b.success_rows} ok / {b.flagged_rows} flagged / {b.failed_rows} failed
                  </td>
                  <td>{new Date(b.uploaded_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="toolbar" style={{ marginTop: "1rem" }}>
          <Link to="/review" className="btn btn-primary" style={{ textDecoration: "none" }}>
            Open review queue
          </Link>
          <Link to="/upload" className="btn btn-secondary" style={{ textDecoration: "none" }}>
            Upload new file
          </Link>
        </div>
      </div>
    </>
  );
}
