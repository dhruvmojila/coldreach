/**
 * ColdReach content script — runs on job board pages.
 *
 * Detects the current page's job board, extracts company + job context,
 * and stores it in chrome.storage.session so the popup can read it.
 */

import { detectGreenhouse } from "./greenhouse";
import { detectIndeed } from "./indeed";
import { detectLever } from "./lever";
import { detectLinkedIn } from "./linkedin";
import { detectWorkable } from "./workable";
import type { JobContext } from "@lib/types";

function detect(): JobContext | null {
  return (
    detectGreenhouse() ??
    detectLever() ??
    detectIndeed() ??
    detectLinkedIn() ??
    detectWorkable()
  );
}

function run(): void {
  const ctx = detect();

  if (ctx) {
    // Store for the popup to read on open
    chrome.storage.session.set({ jobContext: ctx });

    // Update the extension badge to show "1" when a job is detected
    chrome.runtime.sendMessage({ type: "JOB_DETECTED", context: ctx }).catch(
      () => {
        // Popup or service worker might not be listening — that's fine
      }
    );
  } else {
    // Clear stale context when navigating away from a job page
    chrome.storage.session.remove("jobContext");
  }
}

// Run immediately and again after a short delay (for SPAs that render async)
run();
setTimeout(run, 1500);
setTimeout(run, 3000);

// Re-run on SPA navigation (LinkedIn, Indeed use pushState)
let lastUrl = location.href;
const observer = new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    setTimeout(run, 500);
  }
});
observer.observe(document.body, { childList: true, subtree: true });
