import { useState } from "react";
import { DraftPanel } from "./DraftPanel";

interface LiveEmail {
  email: string;
  source: string;
  confidence: number;
  status: string;
}

interface Props {
  emails: LiveEmail[];
  domain: string;
  scanning?: boolean;
  onExportCSV: () => void;
  onRescan: () => void;
}

const STATUS_META: Record<string, { style: string; icon: string; tip: string }> = {
  valid: { style: "bg-green-900 text-green-300", icon: "✓", tip: "SMTP verified" },
  catch_all: { style: "bg-yellow-900 text-yellow-300", icon: "~", tip: "Catch-all domain" },
  unknown: { style: "bg-gray-800 text-gray-400", icon: "?", tip: "Not yet verified" },
  risky: { style: "bg-orange-900 text-orange-300", icon: "!", tip: "No MX records" },
  undeliverable: { style: "bg-red-900 text-red-400", icon: "✗", tip: "Rejected by SMTP" },
  invalid: { style: "bg-red-900 text-red-400", icon: "✗", tip: "Invalid address" },
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="text-gray-600 hover:text-gray-200 transition-colors text-sm leading-none"
      title="Copy email"
    >
      {copied ? "✓" : "⎘"}
    </button>
  );
}

export function EmailTable({ emails, domain, scanning, onExportCSV, onRescan }: Props) {
  const [copiedAll, setCopiedAll] = useState(false);
  const [filter, setFilter] = useState<"all" | "valid">("all");
  const [draftOpen, setDraftOpen] = useState<string | null>(null); // email address with open panel

  const valid = emails.filter((e) => e.status === "valid");
  const shown = filter === "valid" ? valid : emails;

  const handleCopyAll = async () => {
    await navigator.clipboard.writeText(shown.map((e) => e.email).join("\n"));
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 1500);
  };

  return (
    <div className="space-y-2">
      {/* Header row */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">
          <span className="text-white font-semibold">{emails.length}</span> found
          {valid.length > 0 && (
            <span className="text-green-400 ml-1">· {valid.length} verified</span>
          )}
          {scanning && <span className="text-yellow-400 ml-1 animate-pulse">· scanning…</span>}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyAll}
            className="text-brand hover:text-blue-300 transition-colors"
          >
            {copiedAll ? "✓ Copied" : "Copy all"}
          </button>
          <button
            onClick={onExportCSV}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            CSV ↓
          </button>
          {!scanning && (
            <button
              onClick={onRescan}
              className="text-gray-600 hover:text-gray-300 transition-colors"
              title="New search"
            >
              ↺
            </button>
          )}
        </div>
      </div>

      {/* Filter pills */}
      {emails.length > 3 && (
        <div className="flex gap-1">
          {(["all", "valid"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded text-xs transition-colors
                ${filter === f ? "bg-brand text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"}`}
            >
              {f === "all" ? `All (${emails.length})` : `Verified (${valid.length})`}
            </button>
          ))}
        </div>
      )}

      {/* Email rows */}
      <div className="space-y-0.5 max-h-72 overflow-y-auto">
        {shown.map((email) => {
          const meta = STATUS_META[email.status] ?? STATUS_META["unknown"];
          const isOpen = draftOpen === email.email;

          return (
            <div key={email.email}>
              {/* Email row */}
              <div
                className={`px-2 py-2 rounded-lg transition-colors space-y-1
                  ${isOpen ? "bg-gray-800 rounded-b-none" : "bg-gray-900 hover:bg-gray-800"}`}
              >
                <div className="flex items-center gap-2">
                  {/* Email address */}
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-white text-xs truncate">{email.email}</div>
                  </div>

                  {/* Actions: draft button + copy */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => setDraftOpen(isOpen ? null : email.email)}
                      title={isOpen ? "Close draft" : "Draft cold email with Groq"}
                      className={`px-1.5 py-0.5 rounded text-xs font-medium transition-colors
                        ${isOpen
                          ? "bg-brand/20 text-brand"
                          : "bg-gray-800 text-gray-400 hover:bg-brand/20 hover:text-brand"
                        }`}
                    >
                      ✏️
                    </button>
                    <CopyButton text={email.email} />
                  </div>
                </div>

                {/* Status + confidence */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`px-1.5 py-0.5 rounded text-xs font-mono ${meta.style}`}
                    title={meta.tip}
                  >
                    {meta.icon} {email.status}
                  </span>
                  <div className="flex items-center gap-1">
                    <div className="w-8 h-1 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          email.confidence >= 70
                            ? "bg-green-500"
                            : email.confidence >= 40
                              ? "bg-yellow-500"
                              : "bg-gray-600"
                        }`}
                        style={{ width: `${email.confidence}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">{email.confidence}</span>
                  </div>
                  <span className="text-xs text-gray-600 truncate max-w-[100px]">
                    {email.source}
                  </span>
                </div>
              </div>

              {/* Draft panel — slides in below the row */}
              {isOpen && (
                <DraftPanel
                  email={email.email}
                  domain={domain}
                  onClose={() => setDraftOpen(null)}
                />
              )}
            </div>
          );
        })}
      </div>

      {shown.length < emails.length && (
        <button
          onClick={() => setFilter("all")}
          className="text-xs text-gray-500 hover:text-gray-300 w-full text-center"
        >
          Show all {emails.length} emails →
        </button>
      )}
    </div>
  );
}
