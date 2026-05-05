import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

type CatalogRow = Record<string, string>;

export function NewRequest() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [drugs, setDrugs] = useState<CatalogRow[]>([]);
  const [areas, setAreas] = useState<CatalogRow[]>([]);
  const [geos, setGeos] = useState<CatalogRow[]>([]);
  const [stages, setStages] = useState<CatalogRow[]>([]);

  const [title, setTitle] = useState("");
  const [tpp, setTpp] = useState("");
  const [drugId, setDrugId] = useState("");
  const [therapyId, setTherapyId] = useState("");
  const [geoId, setGeoId] = useState("");
  const [lifecycle, setLifecycle] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [d, a, g, s] = await Promise.all([
          api.drugs(),
          api.therapyAreas(),
          api.geographies(),
          api.lifecycleStages(),
        ]);
        setDrugs(d as CatalogRow[]);
        setAreas(a as CatalogRow[]);
        setGeos(g as CatalogRow[]);
        setStages(s as CatalogRow[]);
      } catch {
        /* handled on submit */
      }
    })();
  }, []);

  function validateStep(): boolean {
    if (step === 0) return title.trim().length >= 3 && tpp.trim().length >= 10;
    if (step === 1) return !!drugId && !!therapyId;
    if (step === 2) return !!geoId && !!lifecycle;
    return true;
  }

  async function submit() {
    setError(null);
    setLoading(true);
    try {
      const created = await api.createRequest({
        title,
        tpp_summary: tpp,
        drug_id: drugId,
        therapy_area_id: therapyId,
        geography_id: geoId,
        lifecycle_stage: lifecycle,
        auto_run_agents: false,
      });
      await api.orchestrate(created.request_id);
      nav(`/requests/${created.request_id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const steps = ["TPP & title", "Product & therapy", "Market & lifecycle", "Review"];

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <h2 className="font-display text-2xl font-semibold text-slate-900">New IEP request</h2>
      <p className="text-slate-600 mt-2 text-sm">
        BR-IEP-01 structured intake · Submit runs all four mock agents (orchestrated).
      </p>

      <div className="flex gap-2 mt-8 mb-8">
        {steps.map((label, i) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(i)}
            className={[
              "flex-1 rounded-lg px-2 py-2 text-xs font-semibold border transition-colors",
              step === i
                ? "bg-brand-600 text-white border-brand-600"
                : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50",
            ].join(" ")}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 text-rose-900 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white shadow-card p-6 space-y-4">
        {step === 0 && (
          <>
            <label className="block text-xs font-semibold text-slate-500 uppercase">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="e.g., RWE dossier — Drug X in 2L NSCLC (US)"
            />
            <label className="block text-xs font-semibold text-slate-500 uppercase mt-4">
              Target Product Profile (TPP) summary
            </label>
            <textarea
              value={tpp}
              onChange={(e) => setTpp(e.target.value)}
              rows={8}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="Describe differentiation vs comparators, pivotal endpoints, safety priorities, payer value story…"
            />
          </>
        )}

        {step === 1 && (
          <>
            <label className="block text-xs font-semibold text-slate-500 uppercase">Therapy area</label>
            <select
              value={therapyId}
              onChange={(e) => setTherapyId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">Select…</option>
              {areas.map((a) => (
                <option key={a.therapy_area_id} value={a.therapy_area_id}>
                  {a.name}
                </option>
              ))}
            </select>
            <label className="block text-xs font-semibold text-slate-500 uppercase mt-4">Drug / asset</label>
            <select
              value={drugId}
              onChange={(e) => setDrugId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">Select…</option>
              {drugs.map((d) => (
                <option key={d.drug_id} value={d.drug_id}>
                  {d.name} ({d.sponsor})
                </option>
              ))}
            </select>
          </>
        )}

        {step === 2 && (
          <>
            <label className="block text-xs font-semibold text-slate-500 uppercase">Geography</label>
            <select
              value={geoId}
              onChange={(e) => setGeoId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">Select…</option>
              {geos.map((g) => (
                <option key={g.geography_id} value={g.geography_id}>
                  {g.name}
                </option>
              ))}
            </select>
            <label className="block text-xs font-semibold text-slate-500 uppercase mt-4">Lifecycle stage</label>
            <select
              value={lifecycle}
              onChange={(e) => setLifecycle(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">Select…</option>
              {stages.map((s) => (
                <option key={s.stage_id} value={s.stage_id}>
                  {s.name}
                </option>
              ))}
            </select>
          </>
        )}

        {step === 3 && (
          <div className="text-sm text-slate-700 space-y-3">
            <p>
              <strong>Title:</strong> {title}
            </p>
            <p>
              <strong>TPP:</strong> {tpp.slice(0, 280)}
              {tpp.length > 280 ? "…" : ""}
            </p>
            <p>
              <strong>Therapy:</strong> {areas.find((a) => a.therapy_area_id === therapyId)?.name}
            </p>
            <p>
              <strong>Drug:</strong> {drugs.find((d) => d.drug_id === drugId)?.name}
            </p>
            <p>
              <strong>Geography:</strong> {geos.find((g) => g.geography_id === geoId)?.name}
            </p>
            <p>
              <strong>Lifecycle:</strong> {stages.find((s) => s.stage_id === lifecycle)?.name}
            </p>
          </div>
        )}

        <div className="flex justify-between pt-4">
          <button
            type="button"
            disabled={step === 0}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Back
          </button>
          {step < 3 ? (
            <button
              type="button"
              disabled={!validateStep()}
              onClick={() => validateStep() && setStep((s) => s + 1)}
              className="rounded-lg bg-brand-600 text-white px-5 py-2 text-sm font-semibold hover:bg-brand-700 disabled:opacity-40"
            >
              Next
            </button>
          ) : (
            <button
              type="button"
              disabled={!validateStep() || loading}
              onClick={submit}
              className="rounded-lg bg-slate-900 text-white px-5 py-2 text-sm font-semibold hover:bg-slate-800 disabled:opacity-40"
            >
              {loading ? "Running agents…" : "Submit & orchestrate"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
