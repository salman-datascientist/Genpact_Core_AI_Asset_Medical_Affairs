import type { Citation, IepPayload } from "../lib/types";
import { CitationChip } from "./CitationChip";
import { ConfidenceBadge } from "./ConfidenceBadge";

export function IepDraftViewer({
  payload,
  citations,
  onCitation,
  onRegenerate,
  busy,
}: {
  payload: IepPayload;
  citations: Citation[];
  onCitation: (c: Citation) => void;
  onRegenerate: (heading: string) => void;
  busy?: boolean;
}) {
  return (
    <div className="space-y-6">
      {payload.sections.map((sec) => (
        <section
          key={sec.heading}
          className="rounded-xl border border-slate-200 bg-white shadow-card overflow-hidden"
        >
          <div className="flex items-center justify-between gap-3 px-5 py-4 bg-slate-50 border-b border-slate-200">
            <h3 className="font-display font-semibold text-slate-900">{sec.heading}</h3>
            <button
              type="button"
              disabled={busy}
              onClick={() => onRegenerate(sec.heading)}
              className="text-xs font-semibold rounded-lg border border-slate-200 bg-white px-3 py-1.5 hover:border-brand-300 hover:text-brand-800 disabled:opacity-50"
            >
              Regenerate section
            </button>
          </div>
          <div className="px-5 py-4 space-y-4">
            {sec.paragraphs.map((p, i) => (
              <div key={i} className="text-sm text-slate-700 leading-relaxed">
                <p>{p.text}</p>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  {p.cite_ids.map((id) => (
                    <CitationChip key={id} citeId={id} citations={citations} onOpen={onCitation} />
                  ))}
                  <ConfidenceBadge value={p.confidence} />
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
