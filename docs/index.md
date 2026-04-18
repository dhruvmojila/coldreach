# ColdReach

**Open-source email finder and lead discovery — free alternative to Hunter.io and Apollo.io.**

[![CI](https://github.com/dhruvmojila/coldreach/actions/workflows/ci.yml/badge.svg)](https://github.com/dhruvmojila/coldreach/actions)
[![PyPI](https://img.shields.io/pypi/v/coldreach)](https://pypi.org/project/coldreach/)
[![Python](https://img.shields.io/pypi/pyversions/coldreach)](https://pypi.org/project/coldreach/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/dhruvmojila/coldreach/blob/main/LICENSE)

---

## Why ColdReach?

|                     | Hunter.io     | Apollo.io     | **ColdReach**          |
| ------------------- | ------------- | ------------- | ---------------------- |
| Cost                | $34–$399/mo   | $49–$149/mo   | **Free forever**       |
| Self-hosted         | No            | No            | **Yes**                |
| Source code         | Closed        | Closed        | **Open source**        |
| Rate limits         | 25k/mo        | 10k/mo        | **None (local)**       |
| API keys required   | Yes           | Yes           | **No** (Groq optional) |
| Privacy             | Their servers | Their servers | **Your machine only**  |

!!! note "Accuracy"
    ColdReach finds fewer emails than paid tools that have years of indexed data. Expected accuracy is 50–70% vs 85–90% for Hunter.io. But it's free, private, and you own everything.

---

## Install in 60 seconds

```bash
git clone https://github.com/dhruvmojila/coldreach.git && cd coldreach
./scripts/setup.sh && docker compose up -d
pip install coldreach
```

Then:

```bash
coldreach verify john@acme.com
coldreach find --domain acme.com --quick
```

→ See the full [Getting Started](getting-started.md) guide.

---

## What's in Phase 1

<div class="grid cards" markdown>

-   :material-email-check: **Email Verification**

    ---

    5-step pipeline: syntax → disposable check → DNS/MX → Reacher SMTP → Holehe platform check

    [How It Works →](how-it-works.md)

-   :material-magnify: **Multi-Source Discovery**

    ---

    Website crawler, GitHub commits, WHOIS, SearXNG, theHarvester, SpiderFoot — all in parallel

    [Discovery Sources →](sources.md)

-   :material-cached: **Smart Caching**

    ---

    SQLite + optional Redis cache with 7-day TTL. Re-queries skip all sources automatically.

    [Configuration →](configuration.md)

-   :material-code-braces: **Full CLI**

    ---

    `coldreach find`, `coldreach verify`, `coldreach cache` — pipe-friendly JSON output

    [CLI Reference →](cli-reference.md)

</div>

---

## Project Status

| Phase       | Status         | Description                                                            |
| ----------- | -------------- | ---------------------------------------------------------------------- |
| **Phase 1** | ✅ Complete    | Verification pipeline + multi-source discovery + scoring + cache + CLI |
| Phase 2     | 🔄 Next        | TUI interface, Chrome extension scaffold, PostgreSQL persistence        |
| Phase 3     | Planned        | Chrome extension — job board → hiring manager contact                  |
| Phase 4     | Planned        | Cold email outreach (templates, LLM personalization, Listmonk)         |
| Phase 5     | Planned        | BYOK integrations (Hunter.io, Apollo.io, Clearbit enrichment)          |
