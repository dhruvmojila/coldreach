import type { JobContext } from "@lib/types";

/**
 * Lever ATS detector.
 *
 * URL pattern:
 *   jobs.lever.co/{company_slug}/{job_id}
 *   jobs.lever.co/{company_slug}
 */
export function detectLever(): JobContext | null {
  const { hostname, pathname } = window.location;
  if (hostname !== "jobs.lever.co") return null;

  // /acme/abc-123  →  slug = "acme"
  const match = pathname.match(/^\/([^/]+)/);
  const companySlug = match?.[1];
  if (!companySlug) return null;

  // Job title: Lever puts it in <h2> inside the posting header
  const h2 = document.querySelector<HTMLElement>(
    "h2[data-qa='posting-name'], .posting-headline h2, h2"
  );
  const jobTitle = h2?.innerText.trim() ?? document.title.replace(/\s*\|.*$/, "").trim();

  const company = companySlug
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return {
    source: "lever",
    company,
    domain: null,
    jobTitle,
    url: window.location.href,
    detectedAt: new Date().toISOString(),
  };
}
