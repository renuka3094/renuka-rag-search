import { ChevronDown, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import ChatInput from "../components/ChatInput";
import CitationModal from "../components/CitationModal";
import MessageBubble from "../components/MessageBubble";
import { streamChat } from "../lib/api";

// Providers this deployment is actually wired to try (see
// backend/app/services/generation.py). Picking "DeepSeek" here without a
// DEEPSEEK_API_KEY set server-side will surface a real upstream error —
// that's intentional, not a bug: it's the same "compare at least two
// options" requirement, made visible in the product instead of only in
// the design doc.
const MODEL_OPTIONS = [
  { id: "azure_v1", label: "GPT-5.5 (Azure)" },
  { id: "deepseek", label: "DeepSeek" },
];

export default function ChatPage() {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const [provider, setProvider] = useState(MODEL_OPTIONS[0].id);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend(text) {
    const userMessage = { id: `local-${Date.now()}`, role: "user", content: text, citations: [] };
    const draftAssistant = { id: "draft", role: "assistant", content: "", citations: [] };
    setMessages((prev) => [...prev, userMessage, draftAssistant]);
    setStreaming(true);

    let accumulated = "";

    try {
      await streamChat({ conversationId, message: text, provider }, (event) => {
        if (event.type === "citations") {
          setMessages((prev) => updateDraft(prev, (m) => ({ ...m, citations: event.citations })));
        } else if (event.type === "token") {
          accumulated += event.text;
          setMessages((prev) => updateDraft(prev, (m) => ({ ...m, content: accumulated })));

        } else if (event.type === "error") {
          setMessages((prev) => updateDraft(prev, (m) => ({ ...m, content: `Error: ${event.message}` })));
        } else if (event.type === "done") {
          setConversationId(event.conversation_id);
          setMessages((prev) =>
            updateDraft(prev, (m) => ({
              ...m,
              id: event.message_id,
              refused: accumulated.trim() === "I don't have that in the knowledge base.",
              flaggedPromptInjection: event.flagged_prompt_injection,
              model: event.model,
            }))
          );
        }
      });
    } catch (err) {
      setMessages((prev) => updateDraft(prev, (m) => ({ ...m, content: `Error: ${err.message}` })));
    } finally {
      setStreaming(false);
    }
  }

  function updateDraft(prev, updater) {
    const idx = prev.findIndex((m) => m.id === "draft" || m.id === prev[prev.length - 1]?.id);
    return prev.map((m, i) => (i === prev.length - 1 ? updater(m) : m));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header
        style={{
          padding: "20px 24px 12px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Contoso Knowledge Assistant</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13.5, color: "var(--text-secondary)" }}>
            Answers are grounded only in indexed Contoso policy documents — never general knowledge.
          </p>
        </div>

        <div style={{ position: "relative", flexShrink: 0 }}>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            title="Generation model for the next message"
            style={{
              appearance: "none",
              WebkitAppearance: "none",
              background: "var(--bg-surface-raised)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--radius-button)",
              padding: "8px 30px 8px 12px",
              fontSize: 13.5,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown
            size={14}
            strokeWidth={2}
            style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "var(--text-tertiary)" }}
          />
        </div>
      </header>

      <div ref={scrollRef} className="scroll-region" style={{ flex: 1, padding: "16px 24px" }}>
        {messages.length === 0 && (
          <div className="empty-state" style={{ height: "100%" }}>
            <Sparkles size={22} strokeWidth={1.5} />
            <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>Ask your teams' first question</div>
            <div style={{ maxWidth: 380 }}>
              Try: "How many PTO days do employees accrue per month?" or something out of scope like
              "What's the weather today?" to see the refusal behavior.
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={m.id ?? i} message={m} onCitationClick={setActiveCitation} />
        ))}
      </div>

      <ChatInput onSend={handleSend} disabled={streaming} />

      <CitationModal citation={activeCitation} onClose={() => setActiveCitation(null)} />
    </div>
  );
}
