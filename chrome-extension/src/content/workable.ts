import type { JobContext } from "@lib/types";

/**
 * Workable ATS detector.
 *
 * URL patterns:
 *   jobs.workable.com/{company_slug}/{job_shortcode}
 *   apply.workable.com/{company_slug}/j/{shortcode}
 *   {company}.workable.com/jobs/{shortcode}  (custom subdomain)
 */
export function detectWorkable(): JobContext | null {
  const { hostname, pathname } = window.location;

  let companySlug: string | null = null;

  if (hostname === "jobs.workable.com") {
    // /acme/abc123  →  slug = "acme"
    const match = pathname.match(/^\/([^/]+)/);
    companySlug = match?.[1] ?? null;
  } else if (hostname === "apply.workable.com") {
    // /acme/j/abc123  →  slug = "acme"
    const match = pathname.match(/^\/([^/]+)/);
    companySlug = match?.[1] ?? null;
  } else if (hostname.endsWith(".workable.com")) {
    companySlug = hostname.split(".")[0];
  }

  if (!companySlug) return null;

  const h1 = document.querySelector<HTMLElement>("h1");
  const jobTitle = h1?.innerText.trim() ?? null;

  const company = companySlug
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return {
    source: "workable",
    company,
    domain: null,
    jobTitle,
    url: window.location.href,
    detectedAt: new Date().toISOString(),
  };
}
