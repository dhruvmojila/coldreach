# How It Works

---

## Verification pipeline

Every email runs through up to 5 sequential checks. Each check either passes (adding to the score), fails (stopping the pipeline), warns (noting uncertainty), or skips (service unavailable).

```
Email input
    │
    ▼
① Syntax check ─────────── RFC 5322 validation via email-validator
    │ FAIL → stop           Normalises to lowercase, rejects typos
    ▼
② Disposable check ──────── 500+ known throwaway domain blocklist
    │ FAIL → stop           (mailinator.com, guerrillamail.com, etc.)
    ▼
③ DNS / MX check ────────── Async DNS lookup via dnspython
    │ FAIL → stop           Fails on NXDOMAIN or zero MX records
    │                       Detects catch-all domains
    ▼
④ Reacher SMTP ──────────── POST /v0/check_email to Reacher microservice
    │ SKIP if no Docker      Rust service handles Gmail/Outlook quirks
    │ FAIL → stop            Returns: is_deliverable, is_catch_all, can_connect
    ▼
⑤ Holehe platforms ──────── Checks email against 120+ platforms (opt-in)
    │ SKIP unless --holehe   Useful on catch-all domains where SMTP is unreliable
    ▼
Confidence score [0–100]
```

### Score baseline and deltas

All emails start at **30**. Each passing check adds points:

| Check | Delta | Condition |
| ----- | ----- | --------- |
| Syntax | 0 | Gate only — no delta |
| Disposable | +5 | Not a disposable domain |
| DNS | +10 | MX records found |
| Reacher | +20 | SMTP accepted, not catch-all |
| Holehe | +15 | Registered on ≥2 platforms |
| Holehe | +5 | Registered on exactly 1 platform |
| Source hint | +15–35 | Website contact page, team page, etc. |

Final score is clamped to `[0, 100]`.

!!! tip "Catch-all domains"
    Domains like Google Workspace or Office 365 accept **all** RCPT TO commands,
    so SMTP verification is useless. Use `--holehe` on these — platform presence
    is a reliable signal when SMTP isn't.

---

## Discovery pipeline

When you run `coldreach find`, all sources execute concurrently:

```
coldreach find --domain acme.com
        │
        ├─── Cache check ──── HIT → return immediately
        │
        ├─── Source 1: WebCrawlerSource      (homepage + /contact + /team + /about)
        ├─── Source 2: WhoisSource           (registrant contact)
        ├─── Source 3: GitHubSource          (commit author emails)
        ├─── Source 4: RedditSource          (mentions with email patterns)
        ├─── Source 5: SearchEngineSource    (SearXNG → DDG → Brave fallback)
        ├─── Source 6: HarvesterSource       (theHarvester Docker container)
        └─── Source 7: SpiderFootSource      (SpiderFoot Docker container)
                │
                ▼
        Merge all SourceResult lists
                │
                ▼
        Pattern generation
        (if --name: infer email format from found emails → generate targeted guesses)
                │
                ▼
        Deduplicate by email address (keep highest confidence_hint)
                │
                ▼
        Verification (run_basic_pipeline for each unique email)
                │
                ▼
        Score + rank results
                │
                ▼
        Store in cache (full results, before min_confidence filter)
                │
                ▼
        Display (filter by min_confidence unless --all)
```

Sources that are unavailable (Docker not running, timeout, etc.) are silently skipped — they contribute a SKIP status to the summary but don't fail the run.

---

## Pattern generation

When a target name is provided (`--name "Jane Smith"`), ColdReach uses found emails to infer the company's email format before generating guesses.

**Example:**

```
Known emails found: ["m.chen@acme.com", "r.jones@acme.com"]
↓
Inferred format: "f.last"   (first initial + dot + last name)
↓
Generated for "Jane Smith":
  - j.smith@acme.com   (inferred format — confidence: higher)
  - jane.smith@acme.com  (companion format — common co-occurrence)
```

When no known emails exist, ColdReach falls back to the top 3 most common B2B formats: `first.last`, `flast`, `first`.

### Supported formats

| Format | Example |
| ------ | ------- |
| `first.last` | jane.smith@acme.com |
| `flast` | jsmith@acme.com |
| `first` | jane@acme.com |
| `f.last` | j.smith@acme.com |
| `firstl` | janes@acme.com |
| `last` | smith@acme.com |
| `last.first` | smith.jane@acme.com |
| `first.last.initial` | jane.smith.j@acme.com |

---

## Caching

ColdReach uses a two-layer cache to avoid repeating expensive discovery runs.

```
coldreach find --domain acme.com
        │
        ▼
① Check Redis (if available)
        │ HIT → deserialize → return
        │ MISS ↓
② Check SQLite (~/.coldreach/cache.db)
        │ HIT + not expired → promote to Redis → return
        │ MISS ↓
③ Run all sources (expensive)
        │
        ▼
Store full results in both Redis + SQLite
(TTL: 7 days, configurable via COLDREACH_CACHE_TTL_DAYS)
```

**Important**: results are cached *before* the `min_confidence` filter is applied. This means a future call with `--all` will still use the cached full result set without re-querying.

Use `--refresh` to bypass the cache for one run, or `coldreach cache clear` to remove entries.
