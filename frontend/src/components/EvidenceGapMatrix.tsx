import type { Citation } from "../lib/types";
import { CitationChip } from "./CitationChip";
import { ConfidenceBadge } from "./ConfidenceBadge";

const sevStyle: Record<string, string> = {
  high: "bg-rose-50 text-rose-900 border-rose-200",
  medium: "bg-amber-50 text-amber-900 border-amber-200",
  low: "bg-slate-50 text-slate-800 border-slate-200",
};

export function EvidenceGapMatrix({
  matrix,
  narrative,
  citations,
  onCitation,
}: {
  matrix: Record<string, unknown>[];
  narrative: string;
  citations: Citation[];
  onCitation: (c: Citation) => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 leading-relaxed bg-violet-50/50 border border-violet-100 rounded-xl p-4">
        {narrative}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {matrix.map((cell, i) => {
          const sev = String(cell.severity ?? "low");
          const badge = sevStyle[sev] ?? sevStyle.low;
          const ids = (cell.cite_ids as string[]) ?? [];
          return (
            <div
              key={i}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-card flex flex-col gap-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold uppercase text-slate-400">
                  {String(cell.stakeholder)}
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${badge}`}>
                  {sev} gap
                </span>
              </div>
              <div className="font-semibold text-slate-900">{String(cell.tpp_attribute)}</div>
              <p className="text-sm text-slate-600">{String(cell.gap_topic)}</p>
              <p className="text-xs text-slate-500">{String(cell.mitigations)}</p>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                {ids.map((id) => (
                  <CitationChip key={id} citeId={id} citations={citations} onOpen={onCitation} />
                ))}
                <ConfidenceBadge value={Number(cell.confidence)} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
