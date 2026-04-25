/**
 * ColdReach background service worker (Manifest V3).
 *
 * Responsibilities:
 *  - Update the extension action badge when a job page is detected.
 *  - Forward job-detected messages from content scripts.
 *
 * All heavy lifting (API calls, UI) lives in the popup.
 */

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "JOB_DETECTED") {
    // Show a green badge dot so the user knows ColdReach has context
    chrome.action.setBadgeText({ text: "●" });
    chrome.action.setBadgeBackgroundColor({ color: "#22c55e" });
    sendResponse({ ok: true });
  }
  return false; // synchronous response
});

// Clear badge when the user navigates away (tab URL changes)
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading") {
    chrome.action.setBadgeText({ tabId, text: "" });
  }
});
