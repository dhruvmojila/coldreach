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
./scripts/setup.sh
```

Then launch the TUI:

```bash
coldreach
```

Or use headless CLI:

```bash
coldreach --cli find --domain stripe.com --quick
coldreach --cli verify john@stripe.com
```

→ See the full [Getting Started](getting-started.md) guide.

---

## What's included

<div class="grid cards" markdown>

-   :material-monitor: **Interactive TUI**

    ---

    Full-screen terminal app — type a domain, watch emails stream in live from 8 sources in parallel. Four tabs: Find, Verify, Status, Cache.

    [TUI Guide →](tui.md)

-   :material-email-check: **Email Verification**

    ---

    5-step pipeline: syntax → disposable check → DNS/MX → Reacher SMTP → Holehe platform check. Score 0–100.

    [How It Works →](how-it-works.md)

-   :material-magnify: **Multi-Source Discovery**

    ---

    Website crawler, GitHub commits, WHOIS, SearXNG, Reddit, theHarvester, SpiderFoot — all in parallel, deduplicated.

    [Discovery Sources →](sources.md)

-   :material-puzzle: **Chrome Extension**

    ---

    One-click email discovery on Greenhouse, Lever, Indeed, LinkedIn, and Workable job boards.

    [Chrome Extension →](chrome-extension.md)

-   :material-api: **Local API Server**

    ---

    `coldreach serve` starts a FastAPI server at `localhost:8765` with streaming SSE scan, verify, cache, and status endpoints.

    [API Reference →](api-server.md)

-   :material-cached: **Smart Caching**

    ---

    SQLite cache with 7-day TTL. Re-queries skip all sources automatically. Browse and manage from the TUI Cache tab.

    [Configuration →](configuration.md)

</div>

---

## Project Status

| Phase       | Status      | Description                                                                    |
| ----------- | ----------- | ------------------------------------------------------------------------------ |
| **Phase 1** | ✅ Complete | Verification pipeline + multi-source discovery + scoring + SQLite cache + CLI  |
| **Phase 2** | ✅ Complete | Docker stack (SearXNG, Reacher, SpiderFoot, theHarvester) + health checks      |
| **Phase 3** | ✅ Complete | Local FastAPI server (`coldreach serve`) + Chrome extension (5 job boards)     |
| **Phase 4** | ✅ Complete | Full-screen Textual TUI — Find, Verify, Status, Cache tabs                     |
| Phase 5     | 🔄 Next     | Groq-powered cold email drafting + outreach dashboard                          |

---

## Quick demo

```
coldreach                          # → launches TUI (no args)

  ⚡ Find  ✓ Verify  ● Status  ⊟ Cache
  ──────────────────────────────────────
  Domain: stripe.com_   [Quick] [Standard] [Full]  [▶ Scan]

  Sources               │  Email                    Conf  Status
  ✓ web_crawler  +3     │  legal@stripe.com          91   ● likely
  ✓ github       +24    │  press@stripe.com          87   ● likely
  ✓ searxng      +2     │  patrick@stripe.com        55   ○ unverified
  ⟳ spiderfoot…        │  info@stripe.com           35   ○ pattern
  ────────────────────────────────────────────────
  ████████░░  6/8 sources  31 emails found
```
