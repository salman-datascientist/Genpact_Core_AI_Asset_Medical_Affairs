import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { StatusPill } from "../components/StatusPill";
import type { RequestSummary } from "../lib/types";

export function ReviewQueue() {
  const [rows, setRows] = useState<RequestSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const q = await api.reviewQueue();
        setRows(q);
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, []);

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h2 className="font-display text-2xl font-semibold text-slate-900">HITL review queue</h2>
      <p className="text-slate-600 mt-2 text-sm">
        Requests awaiting Medical Director decision (BR-IEP-06).
      </p>

      {error && (
        <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50 text-rose-900 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <div className="mt-8 rounded-2xl border border-slate-200 bg-white shadow-card overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-6 py-3">Request</th>
              <th className="px-6 py-3">Scope</th>
              <th className="px-6 py-3">Updated</th>
              <th className="px-6 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => (
              <tr key={r.request_id} className="hover:bg-slate-50/80">
                <td className="px-6 py-4">
                  <Link
                    to={`/requests/${r.request_id}`}
                    className="font-semibold text-brand-700 hover:underline"
                  >
                    {r.title}
                  </Link>
                  <div className="text-xs text-slate-500 font-mono mt-1">{r.request_id}</div>
                </td>
                <td className="px-6 py-4 text-slate-600">
                  {r.drug_id} · {r.therapy_area_id}
                </td>
                <td className="px-6 py-4 text-slate-500">{new Date(r.updated_at).toLocaleString()}</td>
                <td className="px-6 py-4">
                  <StatusPill status={r.status} />
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-6 py-12 text-center text-slate-500">
                  Queue is empty — submit an IEP from request detail when status is <strong>iep</strong>.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
