import { useCallback, useEffect, useRef, useState } from "react";
import type { Email, FindResult, JobContext, ProgressEvent } from "@lib/types";
import { checkServerOnline, findEmailsStream } from "@lib/api";
import { Header } from "./components/Header";
import { ServerStatus } from "./components/ServerStatus";
import { JobDetected } from "./components/JobDetected";
import { DomainInput } from "./components/DomainInput";
import { ProgressBar } from "./components/ProgressBar";
import { EmailTable } from "./components/EmailTable";

type AppState =
  | { phase: "idle" }
  | { phase: "searching"; progress: ProgressEvent[] }
  | { phase: "done"; result: FindResult }
  | { phase: "error"; message: string };

export function App() {
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);
  const [jobContext, setJobContext] = useState<JobContext | null>(null);
  const [domain, setDomain] = useState("");
  const [state, setState] = useState<AppState>({ phase: "idle" });
  const abortRef = useRef<(() => void) | null>(null);

  // Check server and load job context on mount
  useEffect(() => {
    checkServerOnline().then(setServerOnline);

    chrome.storage.session.get(["jobContext"], (data) => {
      const ctx = data["jobContext"] as JobContext | undefined;
      if (ctx) {
        setJobContext(ctx);
        if (ctx.domain) setDomain(ctx.domain);
      }
    });
  }, []);

  const handleFind = useCallback(() => {
    if (!domain.trim()) return;

    // Cancel any in-flight search
    abortRef.current?.();
    setState({ phase: "searching", progress: [] });

    const stop = findEmailsStream(domain.trim(), {
      quick: true,
      onProgress: (ev) => {
        setState((prev) =>
          prev.phase === "searching"
            ? { phase: "searching", progress: [...prev.progress, ev] }
            : prev
        );
      },
      onComplete: (result) => {
        setState({ phase: "done", result });
      },
      onError: (msg) => {
        setState({ phase: "error", message: msg });
      },
    });

    abortRef.current = stop;
  }, [domain]);

  // Allow Enter key in domain input
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleFind();
  };

  const handleExportCSV = useCallback(() => {
    if (state.phase !== "done") return;
    const rows = [
      ["email", "confidence", "status", "sources"].join(","),
      ...state.result.emails.map((e: Email) =>
        [
          e.email,
          e.confidence,
          e.status,
          e.sources.map((s) => s.source).join("|"),
        ].join(",")
      ),
    ].join("\n");

    const blob = new Blob([rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${domain}-emails.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [state, domain]);

  return (
    <div className="bg-gray-950 text-gray-100 font-sans text-sm">
      <Header />

      <div className="px-4 py-3 space-y-3">
        <ServerStatus online={serverOnline} />

        {jobContext && (
          <JobDetected
            context={jobContext}
            onUseDomain={(d) => setDomain(d)}
          />
        )}

        <DomainInput
          value={domain}
          onChange={setDomain}
          onKeyDown={handleKeyDown}
          disabled={state.phase === "searching"}
        />

        <button
          onClick={handleFind}
          disabled={!domain.trim() || state.phase === "searching" || !serverOnline}
          className={`
            w-full py-2 rounded-lg font-semibold transition-colors
            ${
              domain.trim() && serverOnline && state.phase !== "searching"
                ? "bg-brand hover:bg-brand-dark text-white cursor-pointer"
                : "bg-gray-700 text-gray-500 cursor-not-allowed"
            }
          `}
        >
          {state.phase === "searching" ? "Searching…" : "Find Emails"}
        </button>

        {state.phase === "searching" && (
          <ProgressBar events={state.progress} />
        )}

        {state.phase === "error" && (
          <div className="bg-red-950 border border-red-800 rounded-lg px-3 py-2 text-red-300 text-xs">
            <strong>Error:</strong> {state.message}
            {state.message.includes("connect") && (
              <p className="mt-1 text-red-400">
                Run <code className="bg-gray-900 px-1 rounded">coldreach serve</code>{" "}
                in your terminal.
              </p>
            )}
          </div>
        )}

        {state.phase === "done" && (
          <EmailTable
            emails={state.result.emails}
            domain={state.result.domain}
            onExportCSV={handleExportCSV}
          />
        )}
      </div>
    </div>
  );
}
