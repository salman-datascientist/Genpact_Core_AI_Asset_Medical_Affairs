import type { Citation } from "../lib/types";
import { CitationChip } from "./CitationChip";
import { ConfidenceBadge } from "./ConfidenceBadge";

export function EvidenceLandscapeTable({
  literature,
  hta,
  rwe,
  narrative,
  citations,
  onCitation,
}: {
  literature: Record<string, unknown>[];
  hta: Record<string, unknown>[];
  rwe: Record<string, unknown>[];
  narrative: string;
  citations: Citation[];
  onCitation: (c: Citation) => void;
}) {
  return (
    <div className="space-y-8">
      <p className="text-sm text-slate-600 leading-relaxed bg-brand-50/50 border border-brand-100 rounded-xl p-4">
        {narrative}
      </p>

      <section>
        <h3 className="font-display text-base font-semibold text-slate-900 mb-3">
          Literature (PubMed / Embase style)
        </h3>
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Cite</th>
                <th className="px-4 py-3">Year</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Journal</th>
                <th className="px-4 py-3">Conf.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {literature.map((row) => (
                <tr key={String(row.pmid)} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <CitationChip
                      citeId={String(row.cite_id)}
                      citations={citations}
                      onOpen={onCitation}
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{String(row.year)}</td>
                  <td className="px-4 py-3 text-slate-800 max-w-md">{String(row.title)}</td>
                  <td className="px-4 py-3 text-slate-500">{String(row.journal)}</td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge value={Number(row.confidence)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="font-display text-base font-semibold text-slate-900 mb-3">
          HTA decisions
        </h3>
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Cite</th>
                <th className="px-4 py-3">Agency</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Summary</th>
                <th className="px-4 py-3">Conf.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {hta.map((row) => (
                <tr key={String(row.hta_id)} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <CitationChip
                      citeId={String(row.cite_id)}
                      citations={citations}
                      onOpen={onCitation}
                    />
                  </td>
                  <td className="px-4 py-3 font-medium">{String(row.agency)}</td>
                  <td className="px-4 py-3 max-w-sm">{String(row.title)}</td>
                  <td className="px-4 py-3 text-slate-600 max-w-lg">{String(row.decision_summary)}</td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge value={Number(row.confidence)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="font-display text-base font-semibold text-slate-900 mb-3">
          RWE studies
        </h3>
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Cite</th>
                <th className="px-4 py-3">Design</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Outcome summary</th>
                <th className="px-4 py-3">Conf.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rwe.map((row) => (
                <tr key={String(row.study_id)} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <CitationChip
                      citeId={String(row.cite_id)}
                      citations={citations}
                      onOpen={onCitation}
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{String(row.study_design)}</td>
                  <td className="px-4 py-3 max-w-sm">{String(row.title)}</td>
                  <td className="px-4 py-3 text-slate-600 max-w-lg">{String(row.outcome_summary)}</td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge value={Number(row.confidence)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
