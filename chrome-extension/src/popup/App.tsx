/**
 * ColdReach popup — reads scan state from the background service worker.
 *
 * The background SW runs the actual scan (SSE/polling) and stores results in
 * chrome.storage.session.  The popup just reads that state and renders it.
 * This means:
 *   - Results survive popup close/reopen
 *   - Badge shows email count even when popup is closed
 *   - No race conditions between SSE and popup lifecycle
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ContextMenuQuery, JobContext, ScanMode } from "@lib/types";
import { checkServerOnline, resolveCompany } from "@lib/api";
import { Header } from "./components/Header";
import { ServerStatus } from "./components/ServerStatus";
import { JobDetected } from "./components/JobDetected";
import { DomainInput } from "./components/DomainInput";
import { EmailTable } from "./components/EmailTable";

interface LiveEmail {
  email: string;
  source: string;
  confidence: number;
  status: string;
}

interface ScanState {
  jobId: string;
  domain: string;
  mode: string;
  status: "running" | "complete" | "error";
  emails: LiveEmail[];
  sourcesDone: string[];
  error?: string;
  startedAt: string;
}

const MODE_LABELS: Record<ScanMode, { label: string; time: string; desc: string }> = {
  quick: { label: "Quick", time: "~30s", desc: "Web, GitHub, WHOIS, SearXNG" },
  standard: { label: "Standard", time: "~5 min", desc: "All sources + SpiderFoot PGP keyservers" },
  full: { label: "Full Scan", time: "8-10 min", desc: "Everything incl. breach databases" },
};

export function App() {
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);
  const [jobContext, setJobContext] = useState<JobContext | null>(null);
  const [domain, setDomain] = useState("");
  const [scanMode, setScanMode] = useState<ScanMode>("standard");
  const [scanState, setScanState] = useState<ScanState | null>(null);
  const pollInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load initial state and start polling
  useEffect(() => {
    checkServerOnline().then(setServerOnline);

    // Load context (job board detection, context menu)
    chrome.storage.session.get(["jobContext", "contextMenuQuery"]).then((data) => {
      const ctxMenu = data["contextMenuQuery"] as ContextMenuQuery | undefined;
      const ctx = data["jobContext"] as JobContext | undefined;
      if (ctxMenu?.text) {
        setDomain(ctxMenu.text);
        chrome.storage.session.remove("contextMenuQuery");
      } else if (ctxMenu?.url && !ctxMenu.text) {
        try { setDomain(new URL(ctxMenu.url).hostname.replace(/^www\./, "")); } catch { /* ignore */ }
        chrome.storage.session.remove("contextMenuQuery");
      } else if (ctx && !ctxMenu) {
        setJobContext(ctx);
        if (ctx.domain) setDomain(ctx.domain);
      }
    });

    // Load any existing scan state (may be running from before popup closed)
    chrome.storage.session.get(["scanState"]).then((data) => {
      const state = data["scanState"] as ScanState | undefined;
      if (state) {
        setScanState(state);
        if (state.domain) setDomain(state.domain);
      }
    });

    // Listen for real-time updates from background SW
    const onMessage = (msg: { type: string; state?: ScanState }) => {
      if (msg.type === "SCAN_UPDATE" && msg.state) {
        setScanState(msg.state);
      }
    };
    chrome.runtime.onMessage.addListener(onMessage);

    // Also poll storage every 2s as a fallback (in case messages are missed)
    pollInterval.current = setInterval(() => {
      chrome.storage.session.get(["scanState"]).then((data) => {
        const state = data["scanState"] as ScanState | undefined;
        if (state) setScanState(state);
      });
    }, 2000);

    return () => {
      chrome.runtime.onMessage.removeListener(onMessage);
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  const handleFind = useCallback(async () => {
    if (!domain.trim()) return;

    let targetDomain = domain.trim().toLowerCase().replace(/^www\./, "");

    // If it looks like a company name (no dot), resolve via API
    if (!targetDomain.includes(".")) {
      const resolved = await resolveCompany(targetDomain);
      if (resolved) targetDomain = resolved;
    }

    // Clear old state
    await chrome.storage.session.remove("scanState");
    setScanState(null);

    // Ask background SW to run the scan (survives popup close)
    chrome.runtime.sendMessage({
      type: "START_SCAN",
      domain: targetDomain,
      mode: scanMode,
    });
  }, [domain, scanMode]);

  const handleCancel = useCallback(() => {
    chrome.runtime.sendMessage({ type: "CANCEL_SCAN" });
    setScanState(null);
    chrome.storage.session.remove("scanState");
  }, []);

  const handleExportCSV = useCallback(() => {
    if (!scanState?.emails.length) return;
    const rows = [
      ["email", "confidence", "status", "source"].join(","),
      ...scanState.emails.map((e) =>
        [e.email, e.confidence, e.status, e.source].join(",")
      ),
    ].join("\n");
    const blob = new Blob([rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${scanState.domain}-emails.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [scanState]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleFind();
  };

  const isScanning = scanState?.status === "running";
  const isIdle = !scanState;
  const isDone = scanState?.status === "complete";

  return (
    <div className="bg-gray-950 text-gray-100 font-sans text-sm">
      <Header />
      <div className="px-4 py-3 space-y-3">
        <ServerStatus online={serverOnline} />

        {jobContext && isIdle && (
          <JobDetected context={jobContext} onUseDomain={setDomain} />
        )}

        {/* Input + mode only when not scanning */}
        {(isIdle || isDone) && (
          <>
            <DomainInput
              value={domain}
              onChange={setDomain}
              onKeyDown={handleKeyDown}
              disabled={false}
            />

            {isIdle && (
              <div className="space-y-1.5">
                <div className="text-xs text-gray-500">Scan depth</div>
                <div className="grid grid-cols-3 gap-1">
                  {(["quick", "standard", "full"] as ScanMode[]).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setScanMode(mode)}
                      className={`px-2 py-1.5 rounded text-xs font-medium transition-colors text-left
                        ${scanMode === mode
                          ? "bg-brand text-white"
                          : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                        }`}
                    >
                      <div className="font-semibold">{MODE_LABELS[mode].label}</div>
                      <div className={`text-xs mt-0.5 ${scanMode === mode ? "text-blue-200" : "text-gray-600"}`}>
                        {MODE_LABELS[mode].time}
                      </div>
                    </button>
                  ))}
                </div>
                <div className="text-xs text-gray-600">{MODE_LABELS[scanMode].desc}</div>
              </div>
            )}
          </>
        )}

        {/* Main action button */}
        <button
          onClick={isScanning ? handleCancel : handleFind}
          disabled={!serverOnline || (!isScanning && !domain.trim())}
          className={`w-full py-2 rounded-lg font-semibold transition-colors
            ${!serverOnline || (!isScanning && !domain.trim())
              ? "bg-gray-700 text-gray-500 cursor-not-allowed"
              : isScanning
                ? "bg-red-800 hover:bg-red-700 text-white cursor-pointer"
                : "bg-brand hover:bg-brand-dark text-white cursor-pointer"
            }`}
        >
          {isScanning ? "⏹ Stop" : isDone ? "New Search" : "Find Emails"}
        </button>

        {/* Scanning progress */}
        {isScanning && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span className="animate-pulse">
                Scanning {scanState.domain}…
              </span>
              {scanState.emails.length > 0 && (
                <span className="text-brand font-semibold">
                  {scanState.emails.length} found so far
                </span>
              )}
            </div>
            {/* Source pills */}
            {scanState.sourcesDone.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {scanState.sourcesDone.map((s) => (
                  <span key={s} className="px-1.5 py-0.5 bg-green-900 text-green-300 rounded text-xs font-mono">
                    ✓ {s}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {scanState?.status === "error" && (
          <div className="bg-red-950 border border-red-800 rounded-lg px-3 py-2 text-red-300 text-xs space-y-1">
            <div><strong>Error:</strong> {scanState.error}</div>
            <button onClick={() => { setScanState(null); chrome.storage.session.remove("scanState"); }}
              className="text-red-500 hover:text-red-300 underline">
              Try again
            </button>
          </div>
        )}

        {/* Results — shown whether scanning or done */}
        {(scanState?.emails.length ?? 0) > 0 && (
          <EmailTable
            emails={scanState!.emails}
            domain={scanState!.domain}
            scanning={isScanning}
            onExportCSV={handleExportCSV}
            onRescan={() => { setScanState(null); chrome.storage.session.remove("scanState"); }}
          />
        )}

        {/* No results on completion */}
        {isDone && scanState.emails.length === 0 && (
          <div className="bg-gray-900 rounded-lg px-3 py-4 text-center space-y-2">
            <div className="text-gray-400 text-sm">
              No emails found for <strong className="text-white">{scanState.domain}</strong>
            </div>
            <div className="text-xs text-gray-600">
              Try <strong>Full Scan</strong> mode for deeper OSINT coverage (breach databases, etc.)
            </div>
            <button
              onClick={() => { setScanState(null); chrome.storage.session.remove("scanState"); }}
              className="text-xs text-brand hover:text-blue-300 underline"
            >
              ← Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
