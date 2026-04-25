import { useState } from "react";
import type { Email } from "@lib/types";

interface Props {
  emails: Email[];
  domain: string;
  onExportCSV: () => void;
}

const STATUS_STYLES: Record<string, string> = {
  valid: "bg-green-900 text-green-300",
  catch_all: "bg-yellow-900 text-yellow-300",
  unknown: "bg-gray-800 text-gray-400",
  risky: "bg-orange-900 text-orange-300",
  undeliverable: "bg-red-900 text-red-400",
  invalid: "bg-red-900 text-red-400",
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES["unknown"];
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${style}`}>
      {status}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleCopy}
      className="text-gray-600 hover:text-gray-300 transition-colors text-xs"
      title="Copy email"
    >
      {copied ? "✓" : "⎘"}
    </button>
  );
}

export function EmailTable({ emails, domain, onExportCSV }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopyAll = async () => {
    await navigator.clipboard.writeText(emails.map((e) => e.email).join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (emails.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 text-sm">
        No emails found for <strong className="text-gray-400">{domain}</strong>.
        <p className="text-xs mt-1 text-gray-600">
          Try without <code>--quick</code> for a deeper scan.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Summary row */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">
          <span className="text-white font-semibold">{emails.length}</span>{" "}
          email{emails.length !== 1 ? "s" : ""} found
        </span>
        <div className="flex gap-2">
          <button
            onClick={handleCopyAll}
            className="text-brand hover:text-blue-300 transition-colors"
          >
            {copied ? "✓ Copied" : "Copy all"}
          </button>
          <button
            onClick={onExportCSV}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            CSV ↓
          </button>
        </div>
      </div>

      {/* Email rows */}
      <div className="space-y-1">
        {emails.map((email) => (
          <div
            key={email.email}
            className="
              flex items-center gap-2 px-2 py-1.5 rounded-lg
              bg-gray-900 hover:bg-gray-800 transition-colors group
            "
          >
            {/* Confidence bar */}
            <div className="w-1 h-6 rounded-full bg-gray-800 flex-shrink-0 overflow-hidden">
              <div
                className="w-full bg-brand rounded-full transition-all"
                style={{ height: `${email.confidence}%` }}
              />
            </div>

            {/* Email + source */}
            <div className="flex-1 min-w-0">
              <div className="font-mono text-white text-xs truncate">{email.email}</div>
              <div className="text-gray-600 text-xs truncate">
                {email.sources[0]?.source ?? "generated"}
                {email.confidence > 0 && (
                  <span className="ml-1 text-gray-700">{email.confidence}%</span>
                )}
              </div>
            </div>

            {/* Status + copy */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <StatusBadge status={email.status} />
              <CopyButton text={email.email} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
