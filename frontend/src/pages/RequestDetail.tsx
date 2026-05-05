import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ChatPanel } from "../components/ChatPanel";
import { CitationDrawer } from "../components/CitationDrawer";
import { EvidenceGapMatrix } from "../components/EvidenceGapMatrix";
import { EvidenceLandscapeTable } from "../components/EvidenceLandscapeTable";
import { IepDraftViewer } from "../components/IepDraftViewer";
import { ProgressChecklist } from "../components/ProgressChecklist";
import { ReviewPanel } from "../components/ReviewPanel";
import { StatusPill } from "../components/StatusPill";
import { StudyDesignCards } from "../components/StudyDesignCard";
import type { Citation, ChatMessage, IepPayload, RequestDetail as RD } from "../lib/types";

const tabs = [
  { id: "landscape", label: "Landscape" },
  { id: "gaps", label: "Gap matrix" },
  { id: "studies", label: "Study recs" },
  { id: "iep", label: "IEP draft" },
  { id: "chat", label: "Co-pilot chat" },
  { id: "review", label: "HITL review" },
] as const;

export function RequestDetail() {
  const { id } = useParams();
  const [data, setData] = useState<RD | null>(null);
  const [tab, setTab] = useState<(typeof tabs)[number]["id"]>("landscape");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [citeOpen, setCiteOpen] = useState<Citation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!id) return;
    const d = await api.request(id);
    setData(d);
    const msgs = await api.messages(id);
    setMessages(msgs);
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!id) return;
      try {
        setLoading(true);
        setError(null);
        await reload();
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, reload]);

  const allCitations: Citation[] = useMemo(() => {
    if (!data) return [];
    const lists = [
      data.landscape?.citations,
      data.gaps?.citations,
      data.studies?.citations,
      data.iep?.citations,
    ].flatMap((x) => x ?? []);
    const map = new Map<string, Citation>();
    for (const c of lists) map.set(c.cite_id, c);
    return Array.from(map.values());
  }, [data]);

  async function onSubmitReview(payload: {
    decision: "approve" | "reject" | "comment";
    comments: string;
  }) {
    if (!id) return;
    setBusy(true);
    try {
      await api.reviewDecision(id, {
        decision: payload.decision,
        comments: payload.comments,
        approver: "Medical Director",
      });
      await reload();
    } finally {
      setBusy(false);
    }
  }

  async function onSendChat(text: string) {
    if (!id) return;
    await api.chat(id, text);
    await reload();
  }

  async function onRegenerate(heading: string) {
    if (!id) return;
    setBusy(true);
    try {
      await api.regenerateSection(id, heading);
      await reload();
    } finally {
      setBusy(false);
    }
  }

  async function submitToHitl() {
    if (!id) return;
    setBusy(true);
    try {
      await api.submitReview(id);
      await reload();
      setTab("review");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="p-8 text-slate-500 text-sm">Loading request…</div>;
  if (error || !data)
    return (
      <div className="p-8">
        <p className="text-rose-700 text-sm">{error ?? "Not found"}</p>
        <Link className="text-brand-700 text-sm font-semibold" to="/">
          ← Back
        </Link>
      </div>
    );

  const iepPayload = (data.iep ?? null) as IepPayload | null;

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col lg:flex-row gap-8">
        <div className="lg:w-72 shrink-0 space-y-4">
          <Link to="/" className="text-sm font-semibold text-brand-700 hover:underline">
            ← Dashboard
          </Link>
          <div>
            <h2 className="font-display text-xl font-semibold text-slate-900 leading-snug">{data.title}</h2>
            <div className="mt-2 flex flex-wrap gap-2 items-center">
              <StatusPill status={data.status} />
              <span className="text-xs text-slate-500 font-mono">{data.request_id}</span>
            </div>
            <p className="text-sm text-slate-600 mt-3">
              {data.drug_name} · {data.therapy_area_name} · {data.geography_name}
            </p>
          </div>
          <ProgressChecklist status={data.status} />
          {data.status === "iep" && (
            <button
              type="button"
              disabled={busy}
              onClick={submitToHitl}
              className="w-full rounded-xl bg-amber-500 text-white font-semibold text-sm py-2.5 hover:bg-amber-600 disabled:opacity-50 shadow"
            >
              Submit for HITL review
            </button>
          )}
        </div>

        <div className="flex-1 min-w-0 space-y-4">
          <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={[
                  "px-3 py-1.5 rounded-lg text-sm font-semibold border transition-colors",
                  tab === t.id
                    ? "bg-slate-900 text-white border-slate-900"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50",
                ].join(" ")}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "landscape" &&
            (data.landscape ? (
              <EvidenceLandscapeTable
                literature={data.landscape.literature as Record<string, unknown>[]}
                hta={data.landscape.hta_decisions as Record<string, unknown>[]}
                rwe={data.landscape.rwe_studies as Record<string, unknown>[]}
                narrative={data.landscape.narrative}
                citations={data.landscape.citations}
                onCitation={(c) => setCiteOpen(c)}
              />
            ) : (
              <EmptyStage />
            ))}

          {tab === "gaps" &&
            (data.gaps ? (
              <EvidenceGapMatrix
                matrix={data.gaps.matrix as Record<string, unknown>[]}
                narrative={data.gaps.narrative}
                citations={data.gaps.citations}
                onCitation={(c) => setCiteOpen(c)}
              />
            ) : (
              <EmptyStage />
            ))}

          {tab === "studies" &&
            (data.studies ? (
              <StudyDesignCards
                recommendations={data.studies.recommendations as Record<string, unknown>[]}
                narrative={data.studies.narrative}
                citations={data.studies.citations}
                onCitation={(c) => setCiteOpen(c)}
              />
            ) : (
              <EmptyStage />
            ))}

          {tab === "iep" &&
            (iepPayload ? (
              <IepDraftViewer
                payload={iepPayload}
                citations={allCitations.length ? allCitations : iepPayload.citations}
                onCitation={(c) => setCiteOpen(c)}
                onRegenerate={onRegenerate}
                busy={busy}
              />
            ) : (
              <EmptyStage />
            ))}

          {tab === "chat" && (
            <ChatPanel
              messages={messages}
              onSend={onSendChat}
              disabled={!data.iep || data.status === "approved"}
            />
          )}

          {tab === "review" && (
            <ReviewPanel status={data.status} onSubmit={onSubmitReview} />
          )}
        </div>
      </div>

      <CitationDrawer open={!!citeOpen} citation={citeOpen} onClose={() => setCiteOpen(null)} />
    </div>
  );
}

function EmptyStage() {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-600">
      Run orchestration from the wizard — stages populate here.
    </div>
  );
}
