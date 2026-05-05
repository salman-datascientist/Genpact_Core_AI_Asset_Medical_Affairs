import { useState } from "react";
import { useRole } from "../lib/roleContext";

export function ReviewPanel({
  status,
  onSubmit,
}: {
  status: string;
  onSubmit: (d: { decision: "approve" | "reject" | "comment"; comments: string }) => Promise<void>;
}) {
  const { role } = useRole();
  const [comments, setComments] = useState("");
  const [busy, setBusy] = useState(false);

  const locked = status !== "in_review" || role !== "medical_director";

  async function act(decision: "approve" | "reject" | "comment") {
    if (locked) return;
    setBusy(true);
    try {
      await onSubmit({ decision, comments });
      if (decision !== "comment") setComments("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-card p-6">
      <h3 className="font-display font-semibold text-slate-900">Human-in-the-loop review</h3>
      <p className="text-sm text-slate-600 mt-2">
        BR-IEP-06: Medical Director approval is mandatory before an IEP is marked complete.
      </p>
      {locked && (
        <div className="mt-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-sm px-4 py-3">
          {status !== "in_review"
            ? "Submit the draft to the review queue first (status must be In review)."
            : "Switch role to Medical Director in the top bar to approve or reject."}
        </div>
      )}
      <label className="block mt-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">
        Comments
      </label>
      <textarea
        value={comments}
        onChange={(e) => setComments(e.target.value)}
        disabled={locked || busy}
        rows={4}
        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        placeholder="MLR notes, evidence concerns, or approval rationale…"
      />
      <div className="flex flex-wrap gap-3 mt-4">
        <button
          type="button"
          disabled={locked || busy}
          onClick={() => act("approve")}
          className="rounded-lg bg-emerald-600 text-white text-sm font-semibold px-4 py-2 hover:bg-emerald-700 disabled:opacity-50"
        >
          Approve IEP
        </button>
        <button
          type="button"
          disabled={locked || busy}
          onClick={() => act("reject")}
          className="rounded-lg bg-white border border-slate-200 text-sm font-semibold px-4 py-2 hover:bg-slate-50 disabled:opacity-50"
        >
          Reject to revision
        </button>
        <button
          type="button"
          disabled={locked || busy}
          onClick={() => act("comment")}
          className="rounded-lg bg-slate-900 text-white text-sm font-semibold px-4 py-2 hover:bg-slate-800 disabled:opacity-50"
        >
          Add comment only
        </button>
      </div>
    </div>
  );
}
