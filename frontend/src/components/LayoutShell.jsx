import { LayoutGrid, MessageSquare, Database, Moon, Sun } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";

/**
 * Shared layout shell (Section 6.2 frontend requirement: "a shared layout
 * shell reused across all three apps"). Copy this component, and
 * styles/tokens.css + styles/global.css, into the Week 2 and Week 3
 * projects unchanged so all three DataFactZ apps look like one product
 * family.
 */
export default function LayoutShell() {
  const [theme, setTheme] = useState(() => localStorage.getItem("df-theme") || "dark");

  useEffect(() => {
    localStorage.setItem("df-theme", theme);
  }, [theme]);

  return (
    <div className={`app-shell${theme === "light" ? " theme-light" : ""}`}>
      <aside className="sidebar">
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
            Knowledge base
          </NavLink>
        </nav>

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
