import { ChevronDown, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import ChatInput from "../components/ChatInput";
import MessageBubble from "../components/MessageBubble";
import SourcesPanel from "../components/SourcesPanel";
import { getConversation, streamChat } from "../lib/api";

// Providers this deployment is actually wired to try (see
// backend/app/services/generation.py). Both options are reached through
// the same shared Azure AI Foundry project/endpoint — just different
// deployment names — satisfying the "compare at least two options for
// generation" requirement live in the product, not only in the design doc.
const MODEL_OPTIONS = [
  { id: "azure_v1", label: "GPT-5.5" },
  { id: "azure_deepseek", label: "DeepSeek-V3.2" },
];

const SUGGESTED_QUESTIONS = [
  "How many PTO days do employees accrue per month?",
  "How many days per week can employees work remotely?",
  "What benefits and perks are offered?",
];

export default function ChatPage() {
  const { conversationId: routeConversationId } = useParams();
  const navigate = useNavigate();

  const [conversationId, setConversationId] = useState(routeConversationId ?? null);
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [activeSources, setActiveSources] = useState(null);
  const [provider, setProvider] = useState(MODEL_OPTIONS[0].id);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Sync with the URL: clicking a past chat in the sidebar (or "New chat")
  // changes the route param, which is the source of truth for which
  // conversation is loaded.
  useEffect(() => {
    if (!routeConversationId) {
      setConversationId(null);
      setMessages([]);
      return;
    }
    if (routeConversationId === conversationId && messages.length > 0) return;

    setConversationId(routeConversationId);
    getConversation(routeConversationId)
      .then((data) => {
        setMessages(
          data.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            refused: m.refused,
            model: m.model,
            citations: m.citations,
          }))
        );
      })
      .catch(() => setMessages([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeConversationId]);

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
          if (routeConversationId !== event.conversation_id) {
            navigate(`/c/${event.conversation_id}`, { replace: true });
          }
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
          <Sparkles
            size={14}
            strokeWidth={2}
            style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "var(--color-orange)" }}
          />
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
              padding: "8px 30px 8px 30px",
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
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 16,
                background: "var(--brand-gradient)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 6,
              }}
            >
              <Sparkles size={28} strokeWidth={2} color="var(--text-on-gradient)" />
            </div>
            <div style={{ fontWeight: 700, fontSize: 21, color: "var(--text-primary)" }}>
              Ask the Knowledge Assistant
            </div>
            <div style={{ maxWidth: 420, marginBottom: 6 }}>
              Answers are grounded only in indexed Contoso policy documents — never general knowledge.
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 480 }}>
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  className="pill pill-neutral"
                  style={{ cursor: "pointer", border: "1px solid var(--border-subtle)", padding: "7px 14px" }}
                  onClick={() => handleSend(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={m.id ?? i} message={m} onSourcesClick={setActiveSources} />
        ))}
      </div>

      <ChatInput onSend={handleSend} disabled={streaming} />

      <SourcesPanel citations={activeSources} onClose={() => setActiveSources(null)} />
    </div>
  );
}
