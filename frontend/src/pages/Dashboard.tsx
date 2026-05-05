import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { KpiCard } from "../components/KpiCard";
import { StatusPill } from "../components/StatusPill";
import type { KpiRow, RequestSummary } from "../lib/types";

export function Dashboard() {
  const [kpis, setKpis] = useState<KpiRow[]>([]);
  const [requests, setRequests] = useState<RequestSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const [k, r] = await Promise.all([api.kpis(), api.requests()]);
        if (!cancelled) {
          setKpis(k);
          setRequests(r);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const chartData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const q of requests) {
      counts[q.status] = (counts[q.status] ?? 0) + 1;
    }
    return Object.entries(counts).map(([status, count]) => ({ status: status.replace(/_/g, " "), count }));
  }, [requests]);

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-slate-900">Executive dashboard</h2>
          <p className="text-slate-600 mt-1 text-sm">
            KPIs sourced from `kpis.csv` · throughput from active IEP requests
          </p>
        </div>
        <Link
          to="/requests/new"
          className="inline-flex items-center justify-center rounded-xl bg-brand-600 text-white font-semibold text-sm px-5 py-2.5 shadow hover:bg-brand-700"
        >
          New IEP request
        </Link>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 text-rose-900 px-4 py-3 text-sm">
          <strong>Could not reach API.</strong> {error} — start backend on port 8000.
        </div>
      )}

      {loading ? (
        <div className="text-slate-500 text-sm">Loading…</div>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {kpis.map((k) => (
              <KpiCard key={k.kpi_id} name={k.name} baseline={k.baseline} target={k.target} unit={k.unit} />
            ))}
          </section>

          <section className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
              <div className="font-display font-semibold text-slate-900">Request throughput by status</div>
              <div className="h-72 mt-4">
                {chartData.length === 0 ? (
                  <p className="text-sm text-slate-500">No requests yet — create one to populate the chart.</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <XAxis dataKey="status" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
              <div className="font-display font-semibold text-slate-900">Recent requests</div>
              <ul className="mt-4 divide-y divide-slate-100">
                {requests.slice(0, 8).map((r) => (
                  <li key={r.request_id} className="py-3 flex items-start justify-between gap-3">
                    <div>
                      <Link
                        to={`/requests/${r.request_id}`}
                        className="text-sm font-semibold text-brand-700 hover:underline"
                      >
                        {r.title}
                      </Link>
                      <div className="text-xs text-slate-500 mt-1">{r.request_id}</div>
                    </div>
                    <StatusPill status={r.status} />
                  </li>
                ))}
                {requests.length === 0 && (
                  <li className="text-sm text-slate-500 py-4">No requests yet.</li>
                )}
              </ul>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
