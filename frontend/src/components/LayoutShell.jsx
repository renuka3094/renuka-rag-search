import { LayoutGrid, MessageSquare, Database, Moon, SquarePen, Sun, Trash2 } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

import { deleteConversation, listConversations } from "../lib/api";

/**
 * Shared layout shell (Section 6.2 frontend requirement: "a shared layout
 * shell reused across all three apps"). Copy this component, and
 * styles/tokens.css + styles/global.css, into the Week 2 and Week 3
 * projects unchanged so all three DataFactZ apps look like one product
 * family.
 */
export default function LayoutShell() {
  const [theme, setTheme] = useState(() => localStorage.getItem("df-theme") || "dark");
  const [conversations, setConversations] = useState([]);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    localStorage.setItem("df-theme", theme);
  }, [theme]);

  useEffect(() => {
    listConversations()
      .then(setConversations)
      .catch(() => setConversations([]));
  }, [location.pathname]);

  async function handleDeleteConversation(id) {
    if (!confirm("Delete this conversation?")) return;
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (location.pathname === `/c/${id}`) navigate("/");
    } catch {
      /* best-effort; stale entry clears on next list refresh */
    }
  }

  return (
    <div className={`app-shell${theme === "light" ? " theme-light" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 8px 22px" }}>
            <div className="brand-mark" style={{ padding: 0 }}>
              <div className="mark" />
              <div className="name">
                Data<span>FactZ</span>
              </div>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              style={{ padding: 6 }}
            >
              {theme === "dark" ? <Sun size={14} strokeWidth={2} /> : <Moon size={14} strokeWidth={2} />}
            </button>
          </div>

          <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <NavLink to="/" end className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
              <MessageSquare size={17} strokeWidth={1.75} />
              Chat
            </NavLink>
            <NavLink to="/admin" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
              <Database size={17} strokeWidth={1.75} />
              Admin
            </NavLink>
          </nav>

          <div style={{ borderTop: "1px solid var(--border-subtle)", margin: "14px 0 10px" }} />

          <NavLink
            to="/"
            end
            className="nav-item"
            style={{ color: "var(--color-orange)", fontWeight: 600 }}
          >
            <SquarePen size={17} strokeWidth={1.75} />
            New chat
          </NavLink>
        </div>

        <div className="scroll-region" style={{ display: "flex", flexDirection: "column", gap: 2, paddingTop: 4 }}>
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`nav-item${location.pathname === `/c/${c.id}` ? " active" : ""}`}
              style={{ padding: "9px 6px 9px 12px", gap: 4 }}
            >
              <NavLink
                to={`/c/${c.id}`}
                style={{ flex: 1, minWidth: 0, fontSize: 13, color: "inherit", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                title={c.title}
              >
                {c.title}
              </NavLink>
              <button
                onClick={() => handleDeleteConversation(c.id)}
                title="Delete conversation"
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 4, flexShrink: 0, display: "flex" }}
              >
                <Trash2 size={13} strokeWidth={1.75} />
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <LayoutGrid size={13} strokeWidth={1.75} />
            Use Case 1 · RAG Chatbot
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <Outlet />
      </main>
    </div>
  );
}
