# Local API Server

`coldreach serve` starts a FastAPI server on `localhost:8765`.  The Chrome
extension, n8n automations, or any script can call it directly — no
authentication needed.

!!! info "Localhost only"
    The server binds to `127.0.0.1` by default. Do not expose it on
    `0.0.0.0` to the network without a reverse proxy and authentication.

## Start

```bash
coldreach serve                        # default: localhost:8765
coldreach serve --port 9000            # custom port
coldreach serve --reload               # dev mode — auto-restart on code change
```

Interactive Swagger UI is available at **http://localhost:8765/docs** once
the server is running.

---

## Endpoints

### `GET /`

Health probe. Always returns `200 OK`.

```json
{ "status": "ok", "docs": "/docs", "version": "0.1.0" }
```

---

### `POST /api/find`

Discover email addresses for a domain.  Blocks until all enabled sources
complete, then returns the full result.

For live progress while sources are running use
[`POST /api/find/stream`](#post-apifindstream).

**Request body**

```json
{
  "domain": "stripe.com",
  "company": null,
  "name": null,
  "quick": true,
  "min_confidence": 0,
  "use_firecrawl": false,
  "use_crawl4ai": false,
  "no_cache": false,
  "refresh": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `domain` | `string` | — | Target domain (e.g. `"stripe.com"`). One of `domain` or `company` is required. |
| `company` | `string` | — | Company name — resolved to a domain via Clearbit → DDG. |
| `name` | `string` | — | Full name for pattern-based narrowing (e.g. `"Patrick Collison"`). |
| `quick` | `bool` | `true` | Skip slow OSINT tools (theHarvester + SpiderFoot). Results in ~10s. |
| `min_confidence` | `int [0–100]` | `0` | Hide emails below this confidence score. |
| `use_firecrawl` | `bool` | `false` | Enable Firecrawl JS scraping (requires `pip install firecrawl-py` + server). |
| `use_crawl4ai` | `bool` | `false` | Enable crawl4ai Playwright scraping (requires `pip install crawl4ai`). |
| `no_cache` | `bool` | `false` | Skip cache read and write. |
| `refresh` | `bool` | `false` | Ignore cached result and re-run all sources. |

**Response** — `DomainResult` JSON

```json
{
  "domain": "stripe.com",
  "company_name": null,
  "total": 3,
  "emails": [
    {
      "email": "legal@stripe.com",
      "confidence": 91,
      "status": "valid",
      "sources": [{ "source": "website/contact", "url": "https://stripe.com/contact" }],
      "mx_records": ["aspmx.l.google.com"],
      "is_catch_all_domain": false,
      "checked_at": "2024-01-15T10:32:00"
    }
  ]
}
```

**Quick example**

```bash
curl -s -X POST http://localhost:8765/api/find \
     -H "Content-Type: application/json" \
     -d '{"domain": "stripe.com", "quick": true}' \
  | jq '.emails[] | {email, confidence, status}'
```

---

### `POST /api/find/stream`

Same as `POST /api/find` but returns **Server-Sent Events** — one event per
source as it finishes, then a final `complete` event.

Useful for the Chrome extension popup to show live progress while sources are
still running.

**Event types**

| Event | When | Data |
|-------|------|------|
| `progress` | Each source finishes | `{ source, found, new, total_so_far, errors }` |
| `complete` | All sources done | Full `DomainResult` JSON (same as `POST /api/find`) |
| `error` | Fatal error (no domain given, unresolvable company) | `{ detail: "..." }` |

**Example stream**

```
event: progress
data: {"source": "web_crawler", "found": 2, "new": 2, "total_so_far": 2, "errors": []}

event: progress
data: {"source": "github", "found": 1, "new": 1, "total_so_far": 3, "errors": []}

event: progress
data: {"source": "searxng", "found": 0, "new": 0, "total_so_far": 3, "errors": []}

event: complete
data: {"domain": "stripe.com", "emails": [...], "total": 3}
```

**JavaScript (browser / extension)**

```js
const es = new EventSource('');  // not supported for POST — use fetch + ReadableStream

const resp = await fetch('http://localhost:8765/api/find/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ domain: 'stripe.com', quick: true }),
});

const reader = resp.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // parse SSE frames from text
  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      const payload = JSON.parse(line.slice(6));
      console.log(payload);
    }
  }
}
```

---

### `POST /api/verify`

Verify a single email address through the full pipeline.

**Request body**

```json
{
  "email": "patrick@stripe.com",
  "run_holehe": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `email` | `string` | required | Email address to verify. |
| `run_holehe` | `bool` | `false` | Run Holehe platform check — checks 120+ platforms, adds ~15–45s. |

**Response** — `PipelineResult` JSON

```json
{
  "email": "patrick@stripe.com",
  "normalized": "patrick@stripe.com",
  "passed": true,
  "score": 75,
  "mx_records": ["aspmx.l.google.com"],
  "checks": {
    "syntax":     { "status": "pass", "reason": "Valid RFC 5322", "score_delta": 0 },
    "disposable": { "status": "pass", "reason": "Not disposable", "score_delta": 5 },
    "dns":        { "status": "pass", "reason": "5 MX record(s)", "score_delta": 10 },
    "reacher":    { "status": "pass", "reason": "SMTP deliverable", "score_delta": 20 }
  }
}
```

---

### `GET /api/status`

Return service health and optional package status.

**Response**

```json
{
  "services": [
    { "name": "SearXNG", "online": true, "latency_ms": 84, "port": "8088",
      "role": "Metasearch engine (40+ sources)", "separate_stack": false },
    { "name": "Reacher", "online": true, "latency_ms": 55,
      "role": "SMTP email verifier (Rust)", "separate_stack": false },
    { "name": "Firecrawl", "online": false, "latency_ms": null,
      "role": "JS scraper (optional — separate stack)", "separate_stack": true }
  ],
  "packages": [
    { "name": "holehe", "installed": false, "version": "" },
    { "name": "crawl4ai", "installed": false, "version": "" }
  ],
  "summary": { "services_online": 4, "packages_installed": 0 }
}
```

---

### `GET /api/cache`

List all cached domains.

**Response**

```json
{
  "total": 2,
  "domains": [
    { "domain": "stripe.com", "cached_at": "2024-01-15T10:32:00", "expired": false },
    { "domain": "acme.com",   "cached_at": "2024-01-08T09:15:00", "expired": true  }
  ]
}
```

---

### `DELETE /api/cache/{domain}`

Remove a domain from the cache. The next `find` call for that domain will
re-run all sources.

```bash
curl -X DELETE http://localhost:8765/api/cache/stripe.com
```

**Response**

```json
{ "success": true, "domain": "stripe.com" }
```

---

### `GET /api/version`

```json
{ "version": "0.1.0" }
```

---

### `POST /api/v2/draft`

Generate a personalized cold email using Groq. Streams SSE events so the
UI can show text appearing progressively (like ChatGPT).

**Requires:** `COLDREACH_GROQ_API_KEY` in `.env`

**Request body**

```json
{
  "email": "patrick@stripe.com",
  "domain": "stripe.com",
  "sender_name": "Jane Smith",
  "sender_intent": "explore a partnership on embedded payments",
  "email_type": "partnership"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `email` | `string` | Recipient email address |
| `domain` | `string` | Company domain — scraped for context |
| `sender_name` | `string` | Your full name |
| `sender_intent` | `string` | One sentence: what you want from this person |
| `email_type` | `string` | `job_application` \| `partnership` \| `sales` \| `introduction` \| `auto` |
| `groq_api_key` | `string?` | Override the key from `.env` |

**SSE event stream**

```
event: context_ready
data: {"company_name": "Stripe", "description": "Financial infrastructure...", "industry": "fintech"}

event: draft_complete
data: {
  "to": "patrick@stripe.com",
  "subject": "Quick question about Stripe's embedded payments",
  "body": "Hi Patrick,\n\nI came across Stripe's recent...",
  "email_type": "partnership",
  "model": "groq/llama-3.1-8b-instant"
}

event: error
data: {"detail": "Groq API key required..."}
```

**Quick example**

```bash
curl -X POST http://localhost:8765/api/v2/draft \
  -H "Content-Type: application/json" \
  -d '{
    "email": "legal@stripe.com",
    "domain": "stripe.com",
    "sender_name": "Jane Smith",
    "sender_intent": "partnership on embedded finance",
    "email_type": "partnership"
  }'
```

---

## CORS

The server accepts cross-origin requests from:

- `http://localhost` and `http://127.0.0.1` — for local scripts and tools
- `chrome-extension://*` — for the Chrome extension (any extension ID)

---

## Use from Python

```python
import httpx

with httpx.Client(base_url="http://localhost:8765") as client:
    result = client.post("/api/find", json={"domain": "stripe.com", "quick": True})
    emails = result.json()["emails"]
    for e in emails:
        print(e["email"], e["confidence"], e["status"])
```

## Use from JavaScript / Node

```js
const res = await fetch('http://localhost:8765/api/find', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ domain: 'stripe.com', quick: true }),
});
const { emails } = await res.json();
```

## Makefile shortcut

```bash
make find DOMAIN=stripe.com   # calls coldreach find --domain ... --quick
```

There is no `make serve` target — just run `coldreach serve` directly.
