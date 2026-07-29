import { MessageSquare, LayoutGrid, Database } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

/**
 * Shared layout shell (Section 6.2 frontend requirement: "a shared layout
 * shell reused across all three apps"). Copy this component, and
 * styles/tokens.css + styles/global.css, into the Week 2 and Week 3
 * projects unchanged so all three DataFactZ apps look like one product
 * family.
 */
export default function LayoutShell() {
  return (
    <div className="app-shell theme-auto">
      <aside className="sidebar">
        <div className="brand-mark">
          <div className="mark" />
          <div className="name">
            Data<span>FactZ</span>
          </div>
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
