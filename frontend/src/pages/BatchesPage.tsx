import { useEffect, useState } from "react";
import { api } from "../api";
import type { Batch, Paginated } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  sap: "SAP",
  utility: "Utility",
  travel: "Travel",
};

export default function BatchesPage() {
  const [batches, setBatches] = useState<Batch[]>([]);

  useEffect(() => {
    api<Paginated<Batch>>("/batches/").then((d) => setBatches(d.results));
  }, []);

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Ingestion batches</h2>
      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Source</th>
                <th>Status</th>
                <th>Total</th>
                <th>Success</th>
                <th>Flagged</th>
                <th>Failed</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr key={b.id}>
                  <td>{b.filename}</td>
                  <td>{SOURCE_LABELS[b.source_type]}</td>
                  <td>{b.status}</td>
                  <td>{b.total_rows}</td>
                  <td>{b.success_rows}</td>
                  <td>{b.flagged_rows}</td>
                  <td>{b.failed_rows}</td>
                  <td>{new Date(b.uploaded_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {batches.some((b) => b.error_summary) && (
          <p className="hint" style={{ marginTop: "1rem" }}>
            Check error_summary on failed batches in API/admin.
          </p>
        )}
      </div>
    </>
  );
}
