import type { JobContext } from "@lib/types";

/**
 * LinkedIn Jobs detector.
 *
 * We extract only the company name that is already displayed on screen —
 * we do NOT scrape LinkedIn profile data, employee lists, or emails.
 * This avoids any ToS violation: the user sees this text, we just read it.
 *
 * URL patterns:
 *   www.linkedin.com/jobs/view/{id}/
 *   www.linkedin.com/jobs/collections/...
 */
export function detectLinkedIn(): JobContext | null {
  const { hostname, pathname } = window.location;
  if (!hostname.includes("linkedin.com")) return null;
  if (!pathname.startsWith("/jobs/view/")) return null;

  // Company name in the job detail sidebar
  const companyEl = document.querySelector<HTMLElement>(
    '.job-details-jobs-unified-top-card__company-name a, ' +
      '.jobs-unified-top-card__company-name a, ' +
      '[data-test-job-posting-company-name], ' +
      '.topcard__org-name-link, ' +
      '.jobs-details-top-card__company-url'
  );
  const company = companyEl?.innerText.trim();
  if (!company) return null;

  const titleEl = document.querySelector<HTMLElement>(
    '.job-details-jobs-unified-top-card__job-title h1, ' +
      '.jobs-unified-top-card__job-title h1, ' +
      'h1.t-24'
  );
  const jobTitle = titleEl?.innerText.trim() ?? null;

  return {
    source: "linkedin",
    company,
    domain: null, // API will resolve via Clearbit
    jobTitle,
    url: window.location.href,
    detectedAt: new Date().toISOString(),
  };
}
