import { RefreshCw, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import UsageAnalytics from "../components/UsageAnalytics";
import { deleteDocument, listDocuments, reindexAll, reindexDocument, uploadDocument } from "../lib/api";

const STATUS_PILL = {
  indexed: "pill-success",
  pending: "pill-warning",
  failed: "pill-danger",
};

export default function AdminPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  async function refresh() {
    setLoading(true);
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusyId("upload");
    try {
      await uploadDocument(file);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
      e.target.value = "";
    }
  }

  async function handleReindex(id) {
    setBusyId(id);
    try {
      await reindexDocument(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleReindexAll() {
    setBusyId("all");
    try {
      await reindexAll();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Remove this document and its indexed chunks?")) return;
    setBusyId(id);
    try {
      await deleteDocument(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header
        style={{
          padding: "20px 24px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Knowledge base</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13.5, color: "var(--text-secondary)" }}>
            {documents.length} documents · {totalChunks} indexed chunks
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-secondary" onClick={handleReindexAll} disabled={busyId === "all"}>
            <RefreshCw size={15} strokeWidth={2} className={busyId === "all" ? "spin" : ""} />
            Re-index all
          </button>
          <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()} disabled={busyId === "upload"}>
            <Upload size={15} strokeWidth={2} />
            {busyId === "upload" ? "Uploading…" : "Upload document"}
          </button>
          <input ref={fileInputRef} type="file" hidden accept=".pdf,.docx,.html,.htm,.md" onChange={handleUpload} />
        </div>
      </header>

      {error && (
        <div style={{ margin: "12px 24px 0", padding: "10px 14px", background: "color-mix(in srgb, var(--color-danger) 12%, transparent)", color: "var(--color-danger)", borderRadius: "var(--radius-button)", fontSize: 13.5 }}>
          {error}
        </div>
      )}

      <div className="scroll-region" style={{ flex: 1, padding: 24 }}>
        <UsageAnalytics />
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 12 }}>Indexed documents</div>
        {loading ? (
          <div className="empty-state">Loading documents…</div>
        ) : documents.length === 0 ? (
          <div className="empty-state">
            No documents indexed yet. Upload a PDF, DOCX, HTML, or Markdown file for your teams to query.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="card hoverable"
                style={{ padding: "14px 18px", display: "flex", alignItems: "center", justifyContent: "space-between" }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14.5 }}>{doc.title}</div>
                  <div style={{ fontSize: 12.5, color: "var(--text-tertiary)", marginTop: 3 }}>
                    {doc.filename} · {doc.source_format.toUpperCase()} · {doc.chunk_count} chunks
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className={`pill ${STATUS_PILL[doc.status] ?? "pill-neutral"}`}>{doc.status}</span>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleReindex(doc.id)}
                    disabled={busyId === doc.id}
                    title="Re-index this document"
                  >
                    <RefreshCw size={14} strokeWidth={2} />
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleDelete(doc.id)}
                    disabled={busyId === doc.id}
                    title="Delete this document"
                  >
                    <Trash2 size={14} strokeWidth={2} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
