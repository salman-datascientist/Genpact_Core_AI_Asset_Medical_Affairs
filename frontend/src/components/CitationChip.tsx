import type { Citation } from "../lib/types";

export function CitationChip({
  citeId,
  citations,
  onOpen,
}: {
  citeId: string;
  citations: Citation[];
  onOpen?: (c: Citation) => void;
}) {
  const c = citations.find((x) => x.cite_id === citeId);
  return (
    <button
      type="button"
      onClick={() => c && onOpen?.(c)}
      className="inline-flex items-center rounded-md bg-slate-100 hover:bg-brand-50 border border-slate-200 hover:border-brand-200 px-1.5 py-0.5 text-[11px] font-mono font-semibold text-brand-800 transition-colors"
    >
      [{citeId}]
    </button>
  );
}
