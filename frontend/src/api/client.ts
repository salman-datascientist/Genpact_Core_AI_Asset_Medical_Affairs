const BASE = "";

async function handle<T>(resOrPromise: Response | Promise<Response>): Promise<T> {
  const res = await resOrPromise;
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = (j as { detail?: string }).detail ?? JSON.stringify(j);
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => handle<{ status: string }>(fetch(`${BASE}/api/health`)),

  kpis: () => handle<import("../lib/types").KpiRow[]>(fetch(`${BASE}/api/kpis`)),

  drugs: () => fetch(`${BASE}/api/catalog/drugs`).then((r) => r.json()),
  therapyAreas: () => fetch(`${BASE}/api/catalog/therapy-areas`).then((r) => r.json()),
  geographies: () => fetch(`${BASE}/api/catalog/geographies`).then((r) => r.json()),
  lifecycleStages: () => fetch(`${BASE}/api/catalog/lifecycle-stages`).then((r) => r.json()),
  literature: () => fetch(`${BASE}/api/catalog/literature`).then((r) => r.json()),

  requests: () =>
    handle<import("../lib/types").RequestSummary[]>(fetch(`${BASE}/api/requests`)),
  request: (id: string) =>
    handle<import("../lib/types").RequestDetail>(fetch(`${BASE}/api/requests/${id}`)),

  createRequest: (body: Record<string, unknown>) =>
    handle<import("../lib/types").RequestSummary>(
      fetch(`${BASE}/api/requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    ),

  orchestrate: (id: string) =>
    handle<{ ok: boolean }>(
      fetch(`${BASE}/api/requests/${id}/orchestrate`, { method: "POST" }),
    ),

  submitReview: (id: string) =>
    handle<{ ok: boolean }>(
      fetch(`${BASE}/api/requests/${id}/submit-review`, { method: "POST" }),
    ),

  chat: (id: string, message: string) =>
    handle<{ assistant_message: import("../lib/types").ChatMessage }>(
      fetch(`${BASE}/api/requests/${id}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      }),
    ),

  messages: (id: string) =>
    handle<import("../lib/types").ChatMessage[]>(
      fetch(`${BASE}/api/requests/${id}/messages`),
    ),

  regenerateSection: (id: string, section_heading: string) =>
    handle<{ ok: boolean }>(
      fetch(`${BASE}/api/requests/${id}/regenerate-section`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ section_heading }),
      }),
    ),

  reviewQueue: () =>
    handle<import("../lib/types").RequestSummary[]>(
      fetch(`${BASE}/api/reviews/queue`),
    ),

  reviewDecision: (
    id: string,
    body: { decision: "approve" | "reject" | "comment"; approver?: string; comments?: string },
  ) =>
    fetch(`${BASE}/api/requests/${id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(handle),
};
