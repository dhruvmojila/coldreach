import type { JobContext } from "@lib/types";

/**
 * Greenhouse ATS detector.
 *
 * URL patterns:
 *   boards.greenhouse.io/{company_slug}/jobs/{id}
 *   boards.greenhouse.io/{company_slug}
 *   {company}.greenhouse.io/jobs/{id}   (custom subdomain)
 *
 * DOM fallback (for custom career pages using Greenhouse embed):
 *   <meta name="application-name" content="Greenhouse">
 *   window.Grnhse or window.__GREENHOUSE__
 *   data-gh-token attribute on forms
 */
export function detectGreenhouse(): JobContext | null {
  const { hostname, pathname } = window.location;

  let companySlug: string | null = null;
  let companyName: string | null = null;

  // ── URL-based detection ───────────────────────────────────────────────────
  if (hostname === "boards.greenhouse.io") {
    const match = pathname.match(/^\/([^/]+)/);
    companySlug = match?.[1] ?? null;
  } else if (hostname.endsWith(".greenhouse.io")) {
    companySlug = hostname.split(".")[0];
  }

  // ── DOM-based detection (custom career site using Greenhouse embed) ───────
  if (!companySlug) {
    const metaApp = document.querySelector<HTMLMetaElement>(
      'meta[name="application-name"][content*="Greenhouse" i],' +
        'meta[name="generator"][content*="Greenhouse" i]'
    );
    const hasGrnhse =
      typeof (window as Record<string, unknown>)["Grnhse"] !== "undefined" ||
      typeof (window as Record<string, unknown>)["__GREENHOUSE__"] !== "undefined";
    const ghToken = document.querySelector("[data-gh-token], [data-greenhouse-token]");

    if (metaApp || hasGrnhse || ghToken) {
      // Extract company from page title or heading
      const h1 = document.querySelector<HTMLElement>("h1");
      companyName =
        document.querySelector<HTMLElement>('[class*="company"], [class*="employer"]')
          ?.innerText.trim() ?? null;
      if (!companyName) {
        // Try to pull from <title>: "Jobs at Acme Corp" or "Acme Corp Careers"
        const title = document.title;
        const m =
          title.match(/jobs?\s+at\s+(.+?)(?:\s*[-|]|$)/i) ??
          title.match(/(.+?)\s+(?:careers?|jobs?)/i);
        companyName = m?.[1]?.trim() ?? null;
      }
      if (!companyName && h1) companyName = h1.innerText.trim();
    }
  }

  if (!companySlug && !companyName) return null;

  // Build readable name from slug if we don't have an explicit name
  if (!companyName && companySlug) {
    companyName = companySlug
      .replace(/-/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  const h1 = document.querySelector<HTMLElement>(
    ".app-title, h1.job-title, h1.posting-headline, h1"
  );
  const jobTitle =
    h1?.innerText.trim() ??
    document.title.replace(/\s*[-|].*$/, "").trim() ??
    null;

  return {
    source: "greenhouse",
    company: companyName!,
    domain: null,
    jobTitle,
    url: window.location.href,
    detectedAt: new Date().toISOString(),
  };
}
