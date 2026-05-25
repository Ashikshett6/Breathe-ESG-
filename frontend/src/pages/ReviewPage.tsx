import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Activity, Paginated } from "../types";

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export default function ReviewPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [selected, setSelected] = useState<Activity | null>(null);
  const [statusFilter, setStatusFilter] = useState("flagged");
  const [sourceFilter, setSourceFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (statusFilter) params.set("review_status", statusFilter);
    if (sourceFilter) params.set("source_type", sourceFilter);
    api<Paginated<Activity>>(`/activities/?${params}`)
      .then((d) => setActivities(d.results))
      .catch((e) => setMessage(String(e)));
  }, [statusFilter, sourceFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function approve(id: number) {
    await api(`/activities/${id}/approve/`, { method: "POST" });
    load();
    if (selected?.id === id) setSelected(null);
  }

  async function bulkApprove() {
    await api("/activities/bulk_approve/", {
      method: "POST",
      body: JSON.stringify({ ids: selectedIds }),
    });
    setSelectedIds([]);
    load();
  }

  async function lockApproved() {
    const res = await api<{ locked_count: number }>("/activities/lock_approved/", { method: "POST" });
    setMessage(`Locked ${res.locked_count} rows for audit.`);
    load();
  }

  function toggleSelect(id: number) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Review queue</h2>
      <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
        Approve normalized rows after checking flags and validation errors. Locked rows cannot be edited.
      </p>

      {message && <div className="card" style={{ borderColor: "var(--accent)" }}>{message}</div>}

      <div className="filters">
        <label>
          Status{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="flagged">Flagged</option>
            <option value="failed">Failed</option>
            <option value="approved">Approved</option>
            <option value="locked">Locked</option>
          </select>
        </label>
        <label>
          Source{" "}
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
            <option value="">All</option>
            <option value="sap">SAP</option>
            <option value="utility">Utility</option>
            <option value="travel">Travel</option>
          </select>
        </label>
        <button className="btn btn-primary" disabled={!selectedIds.length} onClick={bulkApprove}>
          Approve selected ({selectedIds.length})
        </button>
        <button className="btn btn-secondary" onClick={lockApproved}>
          Lock all approved for audit
        </button>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Status</th>
                <th>Scope</th>
                <th>Category</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>Site</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activities.map((a) => (
                <tr key={a.id} onClick={() => setSelected(a)} style={{ cursor: "pointer" }}>
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(a.id)}
                      disabled={a.review_status === "locked"}
                      onChange={() => toggleSelect(a.id)}
                    />
                  </td>
                  <td>
                    <StatusBadge status={a.review_status} />
                    {a.is_edited && <span title="Edited"> ✎</span>}
                  </td>
                  <td>{a.scope}</td>
                  <td>{a.category}</td>
                  <td>{a.description?.slice(0, 40)}</td>
                  <td>
                    {a.normalized_quantity ?? a.quantity} {a.normalized_unit || a.unit}
                  </td>
                  <td>{a.site_name || a.site_code || "—"}</td>
                  <td>{a.activity_date || (a.period_start ? `${a.period_start} → ${a.period_end}` : "—")}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    {a.review_status !== "locked" && a.review_status !== "approved" && (
                      <button className="btn btn-primary" style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }} onClick={() => approve(a.id)}>
                        Approve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="card detail-panel">
          <h3>Row detail — {selected.source_row_id}</h3>
          <p>
            <strong>Source:</strong> {selected.source_type} / {selected.batch_filename}
          </p>
          {selected.flags?.length > 0 && (
            <>
              <strong>Flags:</strong>
              <ul className="flag-list">
                {selected.flags.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </>
          )}
          {selected.validation_errors?.length > 0 && (
            <>
              <strong style={{ color: "var(--danger)" }}>Errors:</strong>
              <ul className="flag-list">
                {selected.validation_errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </>
          )}
          <pre style={{ overflow: "auto", fontSize: "0.75rem", color: "var(--muted)" }}>
            {JSON.stringify(selected.raw_payload, null, 2)}
          </pre>
        </div>
      )}
    </>
  );
}
