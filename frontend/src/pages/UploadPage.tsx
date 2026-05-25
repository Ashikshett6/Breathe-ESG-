import { useEffect, useState } from "react";
import { uploadFile, api } from "../api";

interface SourceInfo {
  id: string;
  label: string;
  format: string;
  scope: string;
}

export default function UploadPage() {
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [sourceType, setSourceType] = useState("sap");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<SourceInfo[]>("/ingest/sources/").then((s) => {
      setSources(s);
      if (s.length) setSourceType(s[0].id);
    });
  }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const batch = await uploadFile(sourceType, file);
      setResult(batch as Record<string, unknown>);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  const current = sources.find((s) => s.id === sourceType);

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Upload data</h2>
      <p style={{ color: "var(--muted)" }}>
        File upload matches how sustainability teams typically receive exports — emailed CSVs from SAP,
        portal downloads, or Concur extract files.
      </p>

      <div className="source-pills">
        {sources.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`source-pill ${sourceType === s.id ? "active" : ""}`}
            onClick={() => setSourceType(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {current && (
        <p className="hint">
          Expected: {current.format} · Maps to Scope {current.scope}
        </p>
      )}

      <form className="card" onSubmit={handleUpload}>
        <div className="upload-zone">
          <p>Drop a CSV export from your source system</p>
          <input
            type="file"
            accept=".csv,.txt"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          {file && <p style={{ color: "var(--text)" }}>Selected: {file.name}</p>}
        </div>
        {error && <div className="error-msg">{error}</div>}
        <button className="btn btn-primary" type="submit" disabled={!file || loading} style={{ marginTop: "1rem" }}>
          {loading ? "Processing…" : "Upload & ingest"}
        </button>
      </form>

      {result && (
        <div className="card">
          <h2>Ingestion result</h2>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}

      <div className="card">
        <h2>Sample files (in repo /samples)</h2>
        <ul style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
          <li>sap_procurement_q1.csv — semicolon-delimited, German headers</li>
          <li>utility_electricity_q1.csv — billing period columns</li>
          <li>concur_travel_q1.csv — Concur-style expense extract</li>
        </ul>
      </div>
    </>
  );
}
