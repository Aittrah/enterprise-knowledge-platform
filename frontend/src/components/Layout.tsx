import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useSession } from "../stores/session";
import { useUi } from "../stores/ui";

const NAV = [
  { to: "/", label: "Dashboard", icon: "▤" },
  { to: "/chat", label: "AI Chat", icon: "◆" },
  { to: "/knowledge", label: "Knowledge Base", icon: "▣" },
  { to: "/graph", label: "Knowledge Graph", icon: "◉" },
  { to: "/analytics", label: "Analytics", icon: "▲" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

export function Layout() {
  const { user, clear } = useSession();
  const { theme, toggleTheme } = useUi();
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-edge bg-surface-1 flex flex-col">
        <div className="px-5 py-5 border-b border-edge flex items-start justify-between">
          <div>
            <div className="font-display text-xl text-ink">EKIP</div>
            <div className="text-[11px] font-mono text-ink-muted tracking-wide">
              KNOWLEDGE INTELLIGENCE
            </div>
          </div>
          <button
            className="focusable text-ink-muted hover:text-ink rounded-lg p-1.5 hover:bg-hover transition-colors"
            title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
            onClick={toggleTheme}
          >
            {theme === "light" ? "◑" : "◐"}
          </button>
        </div>
        <nav className="flex-1 py-3" aria-label="Primary">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `focusable flex items-center gap-3 px-5 py-2.5 text-sm transition-all ${
                  isActive
                    ? "text-ink bg-accent-soft border-r-2 border-ink font-medium"
                    : "text-ink-muted hover:text-ink hover:bg-hover"
                }`
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-edge flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="text-sm truncate">{user?.name}</div>
            <div className="text-[11px] font-mono text-ink-muted">{user?.role}</div>
          </div>
          <button
            className="focusable text-xs text-ink-muted hover:text-signal px-2 py-1"
            onClick={() => {
              clear();
              navigate("/");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
