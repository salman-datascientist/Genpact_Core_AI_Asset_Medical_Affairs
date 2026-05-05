import { useEffect, useState } from "react";
import type { ChatMessage } from "../lib/types";

export function ChatPanel({
  messages,
  onSend,
  disabled,
}: {
  messages: ChatMessage[];
  onSend: (text: string) => Promise<void>;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    const el = document.getElementById("chat-end");
    el?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function submit() {
    if (!text.trim() || sending || disabled) return;
    setSending(true);
    try {
      await onSend(text.trim());
      setText("");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white shadow-card h-[480px]">
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="font-display font-semibold text-slate-900">IEP Co-pilot</div>
        <div className="text-xs text-slate-500">
          Conversational refinement (BR-IEP-07) — grounded mock responses.
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3 text-sm">
        {messages.length === 0 && (
          <p className="text-slate-500 text-sm">
            Ask to tighten payer narrative, add EU evidence, or stress FDA/EMA alignment.
          </p>
        )}
        {messages.map((m) => (
          <div
            key={m.message_id}
            className={
              m.role === "user"
                ? "ml-8 rounded-lg bg-brand-50 border border-brand-100 px-3 py-2 text-slate-800"
                : "mr-8 rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-slate-700"
            }
          >
            <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">{m.role}</div>
            {m.content}
          </div>
        ))}
        <div id="chat-end" />
      </div>
      <div className="p-3 border-t border-slate-200 flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), submit())}
          placeholder="Type a refinement instruction…"
          disabled={disabled || sending}
          className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || sending}
          className="rounded-lg bg-slate-900 text-white text-sm font-semibold px-4 py-2 hover:bg-slate-800 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
