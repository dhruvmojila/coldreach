import { useCallback, useRef, useState } from "react";
import type { DraftResult } from "@lib/api";
import { streamDraft } from "@lib/api";

interface Props {
  email: string;
  domain: string;
  onClose: () => void;
}

type PanelState =
  | { phase: "form" }
  | { phase: "generating"; companyName: string }
  | { phase: "done"; draft: DraftResult }
  | { phase: "error"; message: string };

export function DraftPanel({ email, domain, onClose }: Props) {
  const [senderName, setSenderName] = useState(
    () => localStorage.getItem("cr_sender_name") ?? ""
  );
  const [intent, setIntent] = useState("");
  const [emailType, setEmailType] = useState("auto");
  const [state, setState] = useState<PanelState>({ phase: "form" });
  const [copied, setCopied] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);

  const handleGenerate = useCallback(() => {
    if (!senderName.trim() || !intent.trim()) return;
    localStorage.setItem("cr_sender_name", senderName.trim());

    setState({ phase: "generating", companyName: domain });
    stopRef.current?.();

    const stop = streamDraft({
      email,
      domain,
      senderName: senderName.trim(),
      senderIntent: intent.trim(),
      emailType,
      onContext: (name) => setState({ phase: "generating", companyName: name }),
      onComplete: (draft) => setState({ phase: "done", draft }),
      onError: (msg) => setState({ phase: "error", message: msg }),
    });
    stopRef.current = stop;
  }, [email, domain, senderName, intent, emailType]);

  const handleCopy = useCallback(async () => {
    if (state.phase !== "done") return;
    const text = `Subject: ${state.draft.subject}\n\n${state.draft.body}\n\nBest,\n${senderName}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [state, senderName]);

  const isGenerating = state.phase === "generating";

  return (
    <div className="mt-1 mb-2 rounded-lg border border-brand/30 bg-gray-900/80 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
        <div>
          <span className="text-xs font-semibold text-brand">✏️ Draft cold email</span>
          <span className="text-xs text-gray-600 ml-2 font-mono">{email}</span>
        </div>
        <button
          onClick={() => { stopRef.current?.(); onClose(); }}
          className="text-gray-600 hover:text-gray-300 text-sm leading-none"
          title="Close"
        >
          ✕
        </button>
      </div>

      <div className="px-3 py-2.5 space-y-2">
        {/* Form — always visible unless done/error */}
        {(state.phase === "form" || state.phase === "generating") && (
          <>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">Your name</label>
              <input
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                placeholder="Jane Smith"
                disabled={isGenerating}
                className="w-full px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-white text-xs placeholder-gray-600
                  focus:outline-none focus:border-brand disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-0.5">What do you want? <span className="text-gray-600">(one sentence)</span></label>
              <textarea
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                placeholder="Explore a partnership on B2B payments for SMBs in India."
                disabled={isGenerating}
                rows={2}
                className="w-full px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-white text-xs placeholder-gray-600 resize-none
                  focus:outline-none focus:border-brand disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            <div className="flex items-center gap-1.5 flex-wrap">
              {(["auto", "partnership", "job_application", "sales"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setEmailType(t)}
                  disabled={isGenerating}
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors disabled:opacity-40
                    ${emailType === t
                      ? "bg-brand text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    }`}
                >
                  {t === "auto" ? "🤖 Auto" : t === "partnership" ? "🤝" : t === "job_application" ? "💼" : "💰"}{" "}
                  {t === "auto" ? "Auto" : t === "partnership" ? "Partner" : t === "job_application" ? "Job" : "Sales"}
                </button>
              ))}
            </div>

            {isGenerating ? (
              <div className="text-xs text-brand animate-pulse py-1">
                Reading {state.companyName}… writing your email…
              </div>
            ) : (
              <button
                onClick={handleGenerate}
                disabled={!senderName.trim() || !intent.trim()}
                className="w-full py-1.5 rounded-lg bg-brand hover:bg-brand-dark text-white text-xs font-semibold
                  disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ✨ Generate draft
              </button>
            )}
          </>
        )}

        {/* Error state */}
        {state.phase === "error" && (
          <div className="space-y-2">
            <div className="text-xs text-red-400 bg-red-950 rounded px-2 py-1.5">
              {state.message.includes("Groq") || state.message.includes("api key")
                ? "Add COLDREACH_GROQ_API_KEY to .env and restart coldreach serve."
                : state.message}
            </div>
            <button
              onClick={() => setState({ phase: "form" })}
              className="text-xs text-gray-500 hover:text-gray-300 underline"
            >
              ← Try again
            </button>
          </div>
        )}

        {/* Draft result */}
        {state.phase === "done" && (
          <div className="space-y-2">
            <div className="rounded-lg bg-gray-800 border border-gray-700 p-2.5 space-y-2">
              <div>
                <div className="text-xs text-brand font-semibold uppercase tracking-wider mb-0.5">Subject</div>
                <div className="text-xs font-semibold text-white">{state.draft.subject}</div>
              </div>
              <div>
                <div className="text-xs text-brand font-semibold uppercase tracking-wider mb-0.5">Body</div>
                <div className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{state.draft.body}</div>
                <div className="text-xs text-gray-500 mt-1">Best,<br />{senderName}</div>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleCopy}
                className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors
                  ${copied
                    ? "bg-green-800 text-green-200"
                    : "bg-brand hover:bg-brand-dark text-white"
                  }`}
              >
                {copied ? "✓ Copied!" : "📋 Copy full email"}
              </button>
              <button
                onClick={() => setState({ phase: "form" })}
                className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium transition-colors"
                title="Regenerate"
              >
                ↺
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
