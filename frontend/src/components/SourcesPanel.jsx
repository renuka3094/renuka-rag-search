import { useEffect } from "react";
import { FileText, X } from "lucide-react";

export default function SourcesPanel({ citations, onClose }) {
  useEffect(() => {
    if (!citations) return;
    function handleKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [citations, onClose]);

  if (!citations) return null;

  const uniqueDocs = new Set(citations.map((c) => c.document_title)).size;

  return (
    <>
      <div
        onClick={onClose}
        style={{ position: "fixed", inset: 0, background: "rgba(0, 0, 0, 0.45)", zIndex: 99 }}
      />
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width: 380,
          maxWidth: "90vw",
          background: "var(--bg-surface-raised)",
          borderLeft: "1px solid var(--border-subtle)",
          boxShadow: "var(--shadow-card-hover)",
          zIndex: 100,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "18px 20px",
            borderBottom: "1px solid var(--border-subtle)",
            flexShrink: 0,
          }}
        >
          <div style={{ fontWeight: 700, fontSize: 16, color: "var(--text-primary)" }}>Sources</div>
          <button onClick={onClose} className="btn btn-secondary" style={{ padding: 6 }} title="Close">
            <X size={15} strokeWidth={2} />
          </button>
        </div>

        <div style={{ padding: "14px 20px 4px", fontSize: 12, color: "var(--text-tertiary)", flexShrink: 0 }}>
          Documents · {uniqueDocs}
        </div>

        <div
          className="scroll-region"
          style={{ flex: 1, padding: "10px 20px 20px", display: "flex", flexDirection: "column", gap: 12 }}
        >
          {citations.map((c) => (
            <div key={c.chunk_id} className="card" style={{ padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <FileText size={13} strokeWidth={1.75} color="var(--color-orange)" />
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>
                  {c.document_title}
                </div>
              </div>
              {c.section_heading && (
                <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", marginBottom: 6 }}>
                  {c.section_heading}
                </div>
              )}
              <div style={{ fontSize: 13, lineHeight: 1.5, color: "var(--text-secondary)" }}>{c.snippet}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
