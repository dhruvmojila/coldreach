/**
 * ColdReach background service worker (Manifest V3).
 *
 * Responsibilities:
 *  1. Context menus (right-click "Find emails for...")
 *  2. Run scan jobs — background SW stays alive even when popup closes,
 *     so the SSE stream isn't dropped mid-scan.
 *  3. Push results to chrome.storage.session so the popup can read them.
 *  4. Update badge with email count.
 */

const BASE = "http://localhost:8765";

// ── Types ─────────────────────────────────────────────────────────────────────

interface EmailFoundEvent {
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
  emails: EmailFoundEvent[];
  sourcesDone: string[];
  error?: string;
  startedAt: string;
}

// ── Context menus ─────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "coldreach-selection",
    title: 'Find emails for "%s"',
    contexts: ["selection"],
  });
  chrome.contextMenus.create({
    id: "coldreach-page",
    title: "Find emails for this company",
    contexts: ["page", "frame"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const text =
    info.menuItemId === "coldreach-selection"
      ? (info.selectionText ?? "").trim()
      : "";
  await chrome.storage.session.set({
    contextMenuQuery: {
      text,
      url: tab?.url ?? "",
      triggeredAt: new Date().toISOString(),
    },
  });
  try {
    // @ts-expect-error — openPopup() available Chrome 127+
    await chrome.action.openPopup();
  } catch {
    // older Chrome — user must click the icon
  }
});

// ── Badge + job-detected messages ─────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "JOB_DETECTED") {
    chrome.action.setBadgeText({ text: "●" });
    chrome.action.setBadgeBackgroundColor({ color: "#22c55e" });
    sendResponse({ ok: true });
  }

  // Popup asks SW to start a scan (so SSE connection survives popup close)
  if (msg.type === "START_SCAN") {
    startScanInBackground(msg.domain, msg.mode, msg.name);
    sendResponse({ ok: true });
  }

  // Popup polls for current results
  if (msg.type === "GET_SCAN_STATE") {
    chrome.storage.session
      .get(["scanState"])
      .then((data) => sendResponse({ state: data["scanState"] ?? null }));
    return true; // async response
  }

  // Popup cancels the scan
  if (msg.type === "CANCEL_SCAN") {
    chrome.storage.session.get(["scanState"]).then(async (data) => {
      const state = data["scanState"] as ScanState | undefined;
      if (state?.jobId) {
        await fetch(`${BASE}/api/v2/scan/${state.jobId}`, { method: "DELETE" }).catch(() => {});
        await chrome.storage.session.remove("scanState");
      }
      sendResponse({ ok: true });
    });
    return true;
  }

  return false;
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading") {
    chrome.action.setBadgeText({ tabId, text: "" });
  }
});

// ── Scan runner — lives in background SW, survives popup close ────────────────

async function startScanInBackground(domain: string, mode: string, name?: string): Promise<void> {
  // Reset state
  const initialState: ScanState = {
    jobId: "",
    domain,
    mode,
    status: "running",
    emails: [],
    sourcesDone: [],
    startedAt: new Date().toISOString(),
  };
  await chrome.storage.session.set({ scanState: initialState });
  chrome.action.setBadgeText({ text: "…" });
  chrome.action.setBadgeBackgroundColor({ color: "#5b8cff" });

  try {
    // 1. Start the job
    const startResp = await fetch(`${BASE}/api/v2/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        domain,
        name: name ?? null,
        quick: mode === "quick",
        full_scan: mode === "full",
      }),
    });

    if (!startResp.ok) {
      const body = await startResp.json().catch(() => ({}));
      await setError((body as { detail?: string }).detail ?? `Error ${startResp.status}`);
      return;
    }

    const { job_id } = (await startResp.json()) as { job_id: string };
    await chrome.storage.session.set({
      scanState: { ...initialState, jobId: job_id },
    });

    // 2. Poll every 3 seconds until complete
    // Background SW polling is reliable even when popup is closed.
    let attempts = 0;
    const MAX_ATTEMPTS = 200; // 200 × 3s = 10 min max

    while (attempts < MAX_ATTEMPTS) {
      await delay(3000);
      attempts++;

      const pollResp = await fetch(`${BASE}/api/v2/scan/${job_id}`, {
        headers: { Accept: "application/json" },
      }).catch(() => null);

      if (!pollResp?.ok) continue;

      const data = (await pollResp.json()) as {
        status: string;
        emails: EmailFoundEvent[];
        sources_done: string[];
        total: number;
      };

      const newState: ScanState = {
        jobId: job_id,
        domain,
        mode,
        status: data.status === "complete" ? "complete" : "running",
        emails: data.emails ?? [],
        sourcesDone: data.sources_done ?? [],
        startedAt: initialState.startedAt,
      };

      await chrome.storage.session.set({ scanState: newState });

      // Update badge with count
      const count = data.total;
      chrome.action.setBadgeText({ text: count > 0 ? String(count) : "…" });
      chrome.action.setBadgeBackgroundColor({
        color: count > 0 ? "#22c55e" : "#5b8cff",
      });

      // Notify popup if open
      chrome.runtime.sendMessage({
        type: "SCAN_UPDATE",
        state: newState,
      }).catch(() => {}); // popup might not be open

      if (data.status === "complete" || data.status === "cancelled") {
        chrome.action.setBadgeText({ text: count > 0 ? `${count}` : "0" });
        break;
      }
    }

    if (attempts >= MAX_ATTEMPTS) {
      // Timeout — cancel on server
      await fetch(`${BASE}/api/v2/scan/${job_id}`, { method: "DELETE" }).catch(() => {});
    }
  } catch (err) {
    await setError(err instanceof Error ? err.message : "Scan failed");
  }
}

async function setError(message: string): Promise<void> {
  const existing = await chrome.storage.session.get(["scanState"]);
  const current = (existing["scanState"] as ScanState | undefined) ?? {
    jobId: "",
    domain: "",
    mode: "standard",
    emails: [],
    sourcesDone: [],
    startedAt: new Date().toISOString(),
  };
  await chrome.storage.session.set({
    scanState: { ...current, status: "error", error: message },
  });
  chrome.action.setBadgeText({ text: "!" });
  chrome.action.setBadgeBackgroundColor({ color: "#ef4444" });
  chrome.runtime.sendMessage({ type: "SCAN_UPDATE", error: message }).catch(() => {});
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
