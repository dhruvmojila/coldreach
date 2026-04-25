import type { JobContext } from "@lib/types";

/**
 * Greenhouse ATS detector.
 *
 * URL patterns:
 *   boards.greenhouse.io/{company_slug}/jobs/{id}
 *   boards.greenhouse.io/{company_slug}
 *   {company}.greenhouse.io/jobs/{id}   (custom subdomain)
 */
export function detectGreenhouse(): JobContext | null {
  const { hostname, pathname } = window.location;

  let companySlug: string | null = null;

  if (hostname === "boards.greenhouse.io") {
    // /acme/jobs/123  →  slug = "acme"
    const match = pathname.match(/^\/([^/]+)/);
    companySlug = match?.[1] ?? null;
  } else if (hostname.endsWith(".greenhouse.io")) {
    // acme.greenhouse.io  →  slug = "acme"
    companySlug = hostname.split(".")[0];
  }

  if (!companySlug) return null;

  // Job title from page <h1> or <title>
  const h1 = document.querySelector<HTMLElement>("h1.app-title, h1");
  const jobTitle =
    h1?.innerText.trim() ??
    document.title.replace(/\s*-.*$/, "").trim() ??
    null;

  // Convert slug to readable name: "acme-corp" → "Acme Corp"
  const company = companySlug
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return {
    source: "greenhouse",
    company,
    domain: null, // API will resolve
    jobTitle,
    url: window.location.href,
    detectedAt: new Date().toISOString(),
  };
}
