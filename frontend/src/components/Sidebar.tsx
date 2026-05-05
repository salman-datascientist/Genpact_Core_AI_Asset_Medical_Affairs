import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: "◆" },
  { to: "/requests/new", label: "New IEP Request", icon: "+" },
  { to: "/reviews", label: "Review Queue (HITL)", icon: "✓" },
  { to: "/library", label: "Library", icon: "◇" },
];

export function Sidebar() {
  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white min-h-screen sticky top-0">
      <div className="p-6 border-b border-slate-100">
        <div className="font-display text-lg font-semibold text-slate-900 tracking-tight">
          Core AI
        </div>
        <div className="text-xs font-medium text-brand-600 uppercase tracking-wider mt-1">
          Medical Affairs
        </div>
        <p className="text-xs text-slate-500 mt-2 leading-relaxed">
          RWE Evidence Builder · POC
        </p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === "/"}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-50 text-brand-800 shadow-sm"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
              ].join(" ")
            }
          >
            <span className="text-slate-400 w-5 text-center">{l.icon}</span>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 text-[11px] text-slate-400 border-t border-slate-100 leading-snug">
        BR-IEP-01…07 · Grounded RAG mock · CSV-backed
      </div>
    </aside>
  );
}
