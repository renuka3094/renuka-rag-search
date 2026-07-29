import { Send } from "lucide-react";
import { useState } from "react";

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  function submit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <form
      onSubmit={submit}
      style={{
        display: "flex",
        gap: 10,
        padding: "14px 24px 20px",
        borderTop: "1px solid var(--border-subtle)",
        background: "var(--bg-canvas)",
      }}
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask about Contoso policies, benefits, or procedures…"
        disabled={disabled}
        style={{
          flex: 1,
          background: "var(--bg-surface)",
          border: "1px solid var(--border-strong)",
          borderRadius: "var(--radius-button)",
          padding: "11px 14px",
          color: "var(--text-primary)",
          fontSize: 14.5,
          outline: "none",
        }}
      />
      <button className="btn btn-primary" type="submit" disabled={disabled || !value.trim()}>
        <Send size={15} strokeWidth={2} />
        Send
      </button>
    </form>
  );
}
