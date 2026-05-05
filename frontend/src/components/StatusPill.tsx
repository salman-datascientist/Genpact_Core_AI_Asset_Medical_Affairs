import type { RequestStatus } from "../lib/types";

const styles: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700 border-slate-200",
  landscape: "bg-sky-50 text-sky-900 border-sky-200",
  gaps: "bg-violet-50 text-violet-900 border-violet-200",
  studies: "bg-fuchsia-50 text-fuchsia-900 border-fuchsia-200",
  iep: "bg-indigo-50 text-indigo-900 border-indigo-200",
  in_review: "bg-amber-50 text-amber-900 border-amber-200",
  approved: "bg-emerald-50 text-emerald-900 border-emerald-200",
  rejected: "bg-rose-50 text-rose-900 border-rose-200",
};

export function StatusPill({ status }: { status: RequestStatus | string }) {
  const s = styles[status] ?? "bg-slate-100 text-slate-700 border-slate-200";
  const label = status.replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${s}`}
    >
      {label}
    </span>
  );
}
