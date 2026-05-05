import { useEffect, useState } from "react";
import { api } from "../api/client";

type Row = Record<string, string>;

export function Library() {
  const [drugs, setDrugs] = useState<Row[]>([]);
  const [areas, setAreas] = useState<Row[]>([]);
  const [lit, setLit] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [d, a, l] = await Promise.all([api.drugs(), api.therapyAreas(), api.literature()]);
        setDrugs(d as Row[]);
        setAreas(a as Row[]);
        setLit(l as Row[]);
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, []);

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      <div>
        <h2 className="font-display text-2xl font-semibold text-slate-900">Evidence library</h2>
        <p className="text-slate-600 mt-2 text-sm">
          Browse seeded CSV catalogs backing the mock RAG landscape (BR-IEP-02).
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 text-rose-900 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white shadow-card p-6">
        <h3 className="font-display font-semibold text-slate-900">Drugs</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {drugs.map((d) => (
            <div key={d.drug_id} className="rounded-xl border border-slate-100 p-4 bg-slate-50/60">
              <div className="font-semibold text-slate-900">{d.name}</div>
              <div className="text-xs text-slate-500 mt-1 font-mono">{d.drug_id}</div>
              <div className="text-sm text-slate-600 mt-2">{d.sponsor}</div>
              <div className="text-xs text-brand-700 mt-2 font-medium">{d.lifecycle_stage}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white shadow-card p-6">
        <h3 className="font-display font-semibold text-slate-900">Therapy areas</h3>
        <ul className="mt-4 divide-y divide-slate-100">
          {areas.map((a) => (
            <li key={a.therapy_area_id} className="py-3 flex flex-col sm:flex-row sm:justify-between gap-2">
              <div className="font-semibold text-slate-900">{a.name}</div>
              <div className="text-sm text-slate-600 max-w-3xl">{a.description}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white shadow-card p-6">
        <h3 className="font-display font-semibold text-slate-900">Literature (sample)</h3>
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">PMID</th>
                <th className="px-4 py-3">Year</th>
                <th className="px-4 py-3">Title</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {lit.slice(0, 15).map((r) => (
                <tr key={r.pmid}>
                  <td className="px-4 py-3 font-mono text-xs">{r.pmid}</td>
                  <td className="px-4 py-3">{r.year}</td>
                  <td className="px-4 py-3 text-slate-800">{r.title}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
