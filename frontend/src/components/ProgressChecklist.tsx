import type { RequestStatus } from "../lib/types";

const steps: { key: RequestStatus; label: string }[] = [
  { key: "draft", label: "Draft" },
  { key: "landscape", label: "Landscape" },
  { key: "gaps", label: "Gaps" },
  { key: "studies", label: "Studies" },
  { key: "iep", label: "IEP draft" },
  { key: "in_review", label: "HITL review" },
];

const order: RequestStatus[] = [
  "draft",
  "landscape",
  "gaps",
  "studies",
  "iep",
  "in_review",
  "approved",
  "rejected",
];

export function ProgressChecklist({ status }: { status: RequestStatus | string }) {
  const idx = order.indexOf(status as RequestStatus);
  const activeIdx = idx === -1 ? 0 : idx;
  const allApproved = status === "approved";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">
        Workflow
      </div>
      <ol className="space-y-3">
        {steps.map((s, i) => {
          const stepIdx = order.indexOf(s.key);
          const done = allApproved || activeIdx > stepIdx;
          const current = !allApproved && activeIdx === stepIdx;
          return (
            <li key={s.key} className="flex items-center gap-3">
              <span
                className={[
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold border",
                  done
                    ? "bg-emerald-500 border-emerald-500 text-white"
                    : current
                      ? "bg-brand-600 border-brand-600 text-white ring-4 ring-brand-100"
                      : "bg-white border-slate-200 text-slate-400",
                ].join(" ")}
              >
                {done ? "✓" : i + 1}
              </span>
              <span
                className={
                  current ? "text-slate-900 font-semibold text-sm" : "text-slate-600 text-sm"
                }
              >
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
