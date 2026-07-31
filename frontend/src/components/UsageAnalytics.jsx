import { HelpCircle, MessageSquare, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { getUsageAnalytics } from "../lib/api";

function StatTile({ icon, label, value }) {
  return (
    <div className="card" style={{ padding: "16px 18px", flex: 1, minWidth: 140 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-tertiary)", fontSize: 11.5, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
        {icon}
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, marginTop: 6, color: "var(--text-primary)" }}>{value}</div>
    </div>
  );
}

export default function UsageAnalytics() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getUsageAnalytics()
      .then(setStats)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return null; // don't block the rest of the admin page over an analytics failure
  if (!stats) return <div className="empty-state" style={{ padding: "20px 0" }}>Loading usage analytics…</div>;

  const maxTokens = Math.max(1, ...stats.by_model.map((m) => m.tokens));

  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 12 }}>Usage analytics</div>

      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <StatTile icon={<MessageSquare size={13} strokeWidth={2} />} label="Conversations" value={stats.conversations} />
        <StatTile icon={<HelpCircle size={13} strokeWidth={2} />} label="Questions asked" value={stats.questions} />
        <StatTile icon={<Zap size={13} strokeWidth={2} />} label="Tokens used" value={stats.total_tokens.toLocaleString()} />
      </div>

      {stats.by_model.length > 0 && (
        <div className="card" style={{ padding: 18 }}>
          <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 2 }}>Usage by model</div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 14 }}>
            Answered questions only — refused questions have no generation model attached. Token
            counts are estimates (same tokenizer used for chunk sizing), not exact provider-billed
            counts.
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {stats.by_model.map((m) => (
              <div key={m.model} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 130, fontSize: 13, fontWeight: 600, flexShrink: 0 }}>{m.model}</div>
                <div style={{ flex: 1, height: 8, background: "var(--bg-inset)", borderRadius: "var(--radius-pill)", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${(m.tokens / maxTokens) * 100}%`,
                      height: "100%",
                      background: "var(--brand-gradient)",
                      borderRadius: "var(--radius-pill)",
                    }}
                  />
                </div>
                <div style={{ width: 130, fontSize: 12, color: "var(--text-tertiary)", textAlign: "right", flexShrink: 0 }}>
                  {m.tokens.toLocaleString()} tokens · {m.message_count} msgs
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
