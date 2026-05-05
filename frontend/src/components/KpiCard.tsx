export function KpiCard({
  name,
  baseline,
  target,
  unit,
}: {
  name: string;
  baseline: string;
  target: string;
  unit: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-card hover:shadow-lift transition-shadow">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{unit}</div>
      <div className="mt-2 font-display text-lg font-semibold text-slate-900 leading-snug">
        {name}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs text-slate-500">Baseline</div>
          <div className="font-medium text-slate-700">{baseline}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500">Target</div>
          <div className="font-semibold text-brand-700">{target}</div>
        </div>
      </div>
    </div>
  );
}
