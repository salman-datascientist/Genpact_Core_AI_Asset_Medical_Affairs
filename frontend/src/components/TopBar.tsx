import { useRole } from "../lib/roleContext";

export function TopBar({ title }: { title: string }) {
  const { role, setRole } = useRole();
  return (
    <header className="sticky top-0 z-30 glass border-b border-slate-200/80">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-xl font-semibold text-slate-900 tracking-tight">
            {title}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5 hidden sm:block">
            Automated RWE Evidence Package Builder · Azure-ready architecture (mock)
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-slate-500 uppercase tracking-wide hidden sm:inline">
            Role
          </span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as "analyst" | "medical_director")}
            className="text-sm rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="analyst">Analyst</option>
            <option value="medical_director">Medical Director</option>
          </select>
          <div className="hidden md:flex items-center gap-2 rounded-full bg-emerald-50 text-emerald-800 px-3 py-1.5 text-xs font-medium border border-emerald-100">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Mock agents online
          </div>
        </div>
      </div>
    </header>
  );
}
