import { Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import ChatInput from "../components/ChatInput";
import MessageBubble from "../components/MessageBubble";
import { streamChat } from "../lib/api";

export default function ChatPage() {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
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
      await streamChat({ conversationId, message: text }, (event) => {
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
      <header style={{ padding: "20px 24px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Contoso Knowledge Assistant</h1>
        <p style={{ margin: "4px 0 0", fontSize: 13.5, color: "var(--text-secondary)" }}>
          Answers are grounded only in indexed Contoso policy documents — never general knowledge.
        </p>
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
          <MessageBubble key={m.id ?? i} message={m} />
        ))}
      </div>

      <ChatInput onSend={handleSend} disabled={streaming} />
    </div>
  );
}
