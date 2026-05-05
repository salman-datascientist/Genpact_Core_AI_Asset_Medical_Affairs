export function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    pct >= 85 ? "bg-emerald-50 text-emerald-800 border-emerald-200" : 
    pct >= 75 ? "bg-amber-50 text-amber-900 border-amber-200" : 
    "bg-rose-50 text-rose-800 border-rose-200";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${tone}`}
      title="Citation confidence (mock heuristic)"
    >
      {pct}% conf.
    </span>
  );
}
