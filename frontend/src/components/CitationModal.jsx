import { useEffect } from "react";
import { FileText, X } from "lucide-react";

export default function CitationModal({ citation, onClose }) {
  useEffect(() => {
    if (!citation) return;
    function handleKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [citation, onClose]);

  if (!citation) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: 24,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: 480,
          width: "100%",
          maxHeight: "70vh",
          padding: 22,
          background: "var(--bg-surface-raised)",
          boxShadow: "var(--shadow-card-hover)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <FileText size={16} strokeWidth={1.75} color="var(--color-orange)" />
            <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>
              {citation.document_title}
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary"
            style={{ padding: "6px 8px" }}
            title="Close"
          >
            <X size={15} strokeWidth={2} />
          </button>
        </div>
        <div
          className="scroll-region"
          style={{ fontSize: 14, lineHeight: 1.6, color: "var(--text-secondary)" }}
        >
          {citation.snippet}
        </div>
      </div>
    </div>
  );
}
