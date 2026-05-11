# Phase 6 — BYOK & Community

**Status:** Planned (not started)
**Prerequisite:** HN launch done, user feedback collected from Phase 1-5 users

---

## Goal

Close the accuracy gap vs Hunter.io/Apollo.io without requiring users to pay us.
Let users plug in their own paid API keys (BYOK = Bring Your Own Key) so
ColdReach becomes the free orchestration layer on top of whichever source
they already pay for.

---

## Features (in priority order)

### 1. Hunter.io BYOK (highest ROI)
- Add `COLDREACH_HUNTER_API_KEY` to config
- New source: `HunterSource` — calls `https://api.hunter.io/v2/domain-search`
- Returns emails with Hunter's verified status (valid/catch-all/etc.)
- Auto-maps Hunter status → ColdReach `VerificationStatus`
- In TUI: if key is set, HunterSource shows in source panel
- Free plan gives 25 requests/month — still useful for high-value targets

### 2. Apollo.io BYOK
- Add `COLDREACH_APOLLO_API_KEY`
- New source: `ApolloSource` — calls Apollo's people search API
- Apollo returns job title, LinkedIn URL, verified email
- Enriches existing emails with job title context for Groq drafting

### 3. Clearbit BYOK (enrichment only)
- Add `COLDREACH_CLEARBIT_API_KEY`
- Used for company enrichment (better context for Groq drafting)
- Replaces web scraping for company context when key is present
- Company name, description, industry, employee count, funding stage

### 4. Common Crawl offline index → HuggingFace Dataset
- Build a pre-extracted email index from Common Crawl monthly dumps
- Host on HuggingFace Datasets as `coldreach/email-index`
- New source: `CommonCrawlSource` — queries the HF dataset
- No API key required, high coverage, works offline
- Updated monthly via GitHub Actions

### 5. Plugin API for community sources
- Define `BaseSource` protocol as a public API (it already exists in sources/base.py)
- Document how to write a custom source
- `pyproject.toml` entry_points for community plugins
- Example: `coldreach-glassdoor`, `coldreach-producthunt`, `coldreach-crunchbase`
- Plugin registry at github.com/dhruvmojila/coldreach-plugins

### 6. Discord community
- Create Discord server
- Channels: #general, #show-your-results, #source-plugins, #bug-reports
- Link from README and docs
- Community members can share custom sources and domain patterns

---

## Config changes (pyproject.toml / .env.example)

```env
# Phase 6 BYOK keys (all optional)
COLDREACH_HUNTER_API_KEY=     # 25 req/mo free
COLDREACH_APOLLO_API_KEY=     # 50 req/mo free
COLDREACH_CLEARBIT_API_KEY=   # 100 enrichments/mo free
```

## UI changes (TUI)

- Status tab: show BYOK sources with their key status (configured/not)
- Find tab: BYOK sources appear in source panel when keys are set
- Settings overlay (new): accessible via `ctrl+,` — shows all configurable keys
  with instructions on where to get each one

---

## Key files to create/modify

| File | Change |
|------|--------|
| `coldreach/sources/hunter.py` | New HunterSource |
| `coldreach/sources/apollo.py` | New ApolloSource |
| `coldreach/sources/commoncrawl.py` | New CommonCrawlSource |
| `coldreach/config.py` | Add hunter_api_key, apollo_api_key, clearbit_api_key |
| `coldreach/tui/screens/status.py` | Show BYOK key status |
| `docs/byok.md` | New doc: how to configure BYOK keys |
| `docs/contributing-sources.md` | New doc: plugin API guide |

---

## Success metrics (before calling Phase 6 done)

- [ ] Hunter.io BYOK working end-to-end (find + TUI + status)
- [ ] Apollo.io BYOK working
- [ ] Accuracy comparison documented: ColdReach+Hunter vs Hunter alone
- [ ] Community plugin README with example source
- [ ] docs/byok.md published
- [ ] Discord server created and linked from README

---

## Notes

- Don't build sending (SMTP/Listmonk) until we have Phase 6 user feedback
- BYOK is the key differentiator: "use your existing subscriptions, ColdReach
  is the free orchestration + TUI layer on top"
- Common Crawl index is the long-term play for completely free high accuracy
