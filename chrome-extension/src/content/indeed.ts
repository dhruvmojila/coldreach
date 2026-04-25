import type { JobContext } from "@lib/types";

/**
 * Indeed detector.
 *
 * URL patterns:
 *   www.indeed.com/viewjob?jk={id}
 *   www.indeed.com/cmp/{company_slug}/jobs/{id}
 *   www.indeed.com/jobs?q=...  (search — no single company)
 *
 * Company name is extracted from the DOM since Indeed encodes it there,
 * not reliably in the URL.
 */
export function detectIndeed(): JobContext | null {
  const { hostname, pathname } = window.location;
  if (!hostname.includes("indeed.com")) return null;

  // Only trigger on job detail pages, not search results
  const isJobPage =
    pathname.startsWith("/viewjob") ||
    pathname.includes("/cmp/") ||
    pathname.startsWith("/jobs/") ||
    new URLSearchParams(window.location.search).has("jk");

  if (!isJobPage) return null;

  // Indeed's company name element (selector may change — list in priority order)
  const companyEl = document.querySelector<HTMLElement>(
    '[data-testid="inlineHeader-companyName"] a, ' +
      ".jobsearch-CompanyInfoWithoutHeaderImage .icl-u-lg-mr--sm, " +
      '[data-company-name], ' +
      ".css-1ioi40n, " + // fallback class
      '.companyName a, .companyName'
  );
  const company = companyEl?.innerText.trim();
  if (!company) return null;

  const h1 = document.querySelector<HTMLElement>("h1.jobsearch-JobInfoHeader-title, h1");
  const jobTitle = h1?.innerText.trim() ?? null;

  return {
    source: "indeed",
    company,
    domain: null,
    jobTitle,
    url: window.location.href,
    detectedAt: new Date().toISOString(),
  };
}
