import { AlertTriangle, FileText, ShieldAlert } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === "user";

  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", padding: "6px 0" }}>
      <div style={{ maxWidth: "72%", display: "flex", flexDirection: "column", gap: 8 }}>
        {message.flaggedPromptInjection && (
          <div className="pill pill-warning" style={{ alignSelf: isUser ? "flex-end" : "flex-start" }}>
            <ShieldAlert size={12} strokeWidth={2} />
            Guardrail: instruction-override pattern detected in this message
          </div>
        )}

        <div
          className="card"
          style={{
            padding: "12px 16px",
            background: isUser ? "var(--bg-surface-raised)" : "var(--bg-surface)",
            borderColor: message.refused ? "var(--color-danger)" : "var(--border-subtle)",
          }}
        >
          {message.refused && (
            <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 6, color: "var(--color-danger)", fontSize: 12, fontWeight: 600 }}>
              <AlertTriangle size={14} strokeWidth={2} />
              Not found in knowledge base
            </div>
          )}
          <div style={{ fontSize: 14.5, lineHeight: 1.55, color: "var(--text-primary)" }}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        {!isUser && message.model && !message.refused && (
          <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", paddingLeft: 2 }}>
            {message.model}
          </div>
        )}

        {message.citations?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {message.citations.map((c) => (
              <button
                key={c.chunk_id}
                className="pill pill-neutral"
                title={c.snippet}
                onClick={() => onCitationClick?.(c)}
                style={{ cursor: "pointer", border: "1px solid var(--border-subtle)" }}
              >
                <FileText size={12} strokeWidth={1.75} />
                [{c.rank}] {c.document_title}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
