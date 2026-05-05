import type { Citation } from "../lib/types";
import { CitationChip } from "./CitationChip";
import { ConfidenceBadge } from "./ConfidenceBadge";

export function StudyDesignCards({
  recommendations,
  narrative,
  citations,
  onCitation,
}: {
  recommendations: Record<string, unknown>[];
  narrative: string;
  citations: Citation[];
  onCitation: (c: Citation) => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 leading-relaxed bg-fuchsia-50/40 border border-fuchsia-100 rounded-xl p-4">
        {narrative}
      </p>
      <div className="space-y-3">
        {recommendations.map((r) => {
          const ids = (r.cite_ids as string[]) ?? [];
          return (
            <div
              key={String(r.design_id)}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-card flex flex-col md:flex-row md:items-start md:justify-between gap-4"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white font-display font-bold text-lg">
                  #{String(r.rank)}
                </div>
                <div>
                  <div className="font-display font-semibold text-slate-900">{String(r.name)}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {String(r.study_type)} · {String(r.duration_months)} mo ·{" "}
                    <span className="font-semibold text-slate-700">{String(r.cost_tier)}</span> cost
                  </div>
                  <p className="text-sm text-slate-600 mt-2">{String(r.rationale)}</p>
                  <div className="text-xs text-slate-500 mt-2">
                    Data sources: <span className="font-medium">{String(r.primary_data_sources)}</span>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {ids.map((id) => (
                      <CitationChip key={id} citeId={id} citations={citations} onOpen={onCitation} />
                    ))}
                  </div>
                </div>
              </div>
              <div className="shrink-0">
                <ConfidenceBadge value={Number(r.confidence)} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
