const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY || "";

function headers(extra = {}) {
  return { "X-API-Key": API_KEY, ...extra };
}

async function handleJson(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.error?.message || detail;
    } catch {
      /* ignore parse failure */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE}/api/v1/documents`, { headers: headers() });
  return handleJson(res);
}

export async function reindexDocument(id) {
  const res = await fetch(`${API_BASE}/api/v1/documents/${id}/reindex`, {
    method: "POST",
    headers: headers(),
  });
  return handleJson(res);
}

export async function reindexAll() {
  const res = await fetch(`${API_BASE}/api/v1/documents/reindex-all`, {
    method: "POST",
    headers: headers(),
  });
  return handleJson(res);
}

export async function listConversations() {
  const res = await fetch(`${API_BASE}/api/v1/chat/conversations`, { headers: headers() });
  return handleJson(res);
}

export async function getConversation(id) {
  const res = await fetch(`${API_BASE}/api/v1/chat/conversations/${id}`, { headers: headers() });
  return handleJson(res);
}

export async function deleteConversation(id) {
  const res = await fetch(`${API_BASE}/api/v1/chat/conversations/${id}`, {
    method: "DELETE",
    headers: headers(),
  });
  return handleJson(res);
}

export async function getUsageAnalytics() {
  const res = await fetch(`${API_BASE}/api/v1/chat/analytics`, { headers: headers() });
  return handleJson(res);
}

/**
 * Streams a chat answer via Server-Sent Events.
 * Calls onEvent(event) for every {type: "token"|"citations"|"done"} event
 * parsed from the stream. Returns nothing; caller drives UI from callback.
 */
export async function streamChat({ conversationId, message, provider }, onEvent) {
  const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ conversation_id: conversationId, message, provider }),
  });

  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || "Chat request failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop(); // last part may be incomplete

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.slice("data:".length).trim();
      try {
        onEvent(JSON.parse(jsonStr));
      } catch {
        /* skip malformed chunk */
      }
    }
  }
}
