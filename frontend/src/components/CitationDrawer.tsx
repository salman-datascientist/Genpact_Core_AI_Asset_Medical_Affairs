import type { Citation } from "../lib/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

export function CitationDrawer({
  open,
  citation,
  onClose,
}: {
  open: boolean;
  citation: Citation | null;
  onClose: () => void;
}) {
  if (!open || !citation) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        aria-label="Close"
        onClick={onClose}
      />
      <aside className="relative w-full max-w-md bg-white shadow-2xl border-l border-slate-200 p-6 animate-[slide_0.2s_ease-out]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase text-slate-400">
              {citation.source_type}
            </div>
            <h3 className="font-display text-lg font-semibold text-slate-900 mt-1">
              {citation.label}
            </h3>
          </div>
          <ConfidenceBadge value={citation.confidence} />
        </div>
        <p className="text-sm text-slate-600 mt-4 leading-relaxed">{citation.detail}</p>
        {citation.url && (
          <a
            href={citation.url}
            target="_blank"
            rel="noreferrer"
            className="inline-block mt-4 text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            Open source link →
          </a>
        )}
        <div className="mt-8 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-slate-900 text-white text-sm font-medium px-4 py-2 hover:bg-slate-800"
          >
            Close
          </button>
        </div>
      </aside>
      <style>{`
        @keyframes slide {
          from { transform: translateX(100%); opacity: 0.5; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
