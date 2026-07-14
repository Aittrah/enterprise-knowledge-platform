import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useSession } from "../stores/session";

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
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-white/8 bg-surface-1 flex flex-col">
        <div className="px-5 py-5 border-b border-white/8">
          <div className="font-display text-xl text-ink">EKIP</div>
          <div className="text-[11px] font-mono text-ink-muted tracking-wide">
            KNOWLEDGE INTELLIGENCE
          </div>
        </div>
        <nav className="flex-1 py-3" aria-label="Primary">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `focusable flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "text-verdigris-bright bg-verdigris/10 border-r-2 border-verdigris"
                    : "text-ink-muted hover:text-ink hover:bg-white/4"
                }`
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-white/8 flex items-center justify-between gap-2">
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
