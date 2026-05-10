# ColdReach

**Find professional emails and draft cold outreach — self-hosted, no subscription, no API keys.**

Free alternative to Hunter.io and Apollo.io. Runs entirely on your machine.

[![CI](https://github.com/dhruvmojila/coldreach/actions/workflows/ci.yml/badge.svg)](https://github.com/dhruvmojila/coldreach/actions)
[![PyPI](https://img.shields.io/pypi/v/coldreach)](https://pypi.org/project/coldreach/)
[![Python](https://img.shields.io/pypi/pyversions/coldreach)](https://pypi.org/project/coldreach/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

![ColdReach — find emails and draft outreach from your terminal](docs/images/demo.gif)

---

```
$ coldreach

  ⚡ Find   ✓ Verify   ● Status   ⊟ Cache   ✉ Outreach
  ─────────────────────────────────────────────────────────────────────

  Domain: stripe.com           [Quick]  [Standard]  [Full]  [▶ Scan]

  Sources              │  Email                        Conf  Status
  ✓ web_crawler  +3    │  legal@stripe.com              91   ● likely
  ✓ whois        +1    │  press@stripe.com              87   ● likely
  ✓ github       +24   │  patrick@stripe.com            71   ● likely
  ✓ searxng      +2    │  jobs@stripe.com               55   ○ unverified
  ⟳ spiderfoot…       │  info@stripe.com               35   ○ pattern
                       │
  ██████████░░  5/8 sources · 31 emails found

  ┌─ Draft for patrick@stripe.com ──────────────────────────────────┐
  │  Stripe · Fintech · San Francisco                                │
  │  "Global payments infrastructure for internet businesses"       │
  │                                                                  │
  │  A: Quick question about Stripe's payment API   ← selected      │
  │  B: Partnership on embedded payments  (press 2)                 │
  │  C: Exploring fintech collaboration   (press 3)                 │
  │                                                                  │
  │  Hi Patrick, I've been following Stripe's recent expansion…     │
  │                            [y: Copy]  [↺ Regenerate]  [Esc]    │
  └──────────────────────────────────────────────────────────────────┘
```

---

## Install

**Quick start** (no Docker required):

```bash
pip install coldreach
coldreach --cli find --domain acme.com --quick
```

**Full stack** — enables SMTP verification, OSINT sources, and the TUI:

```bash
git clone https://github.com/dhruvmojila/coldreach.git && cd coldreach
./scripts/setup.sh        # installs deps, starts Docker stack, verifies services
coldreach                 # launches the TUI
```

---

## Quick start

```bash
coldreach                                          # launch the terminal UI
coldreach --cli find --domain stripe.com           # headless scan
coldreach --cli find --domain stripe.com --quick   # fast mode (~30s, no OSINT)
coldreach --cli verify patrick@stripe.com          # verify a single email
coldreach serve                                    # start API server at localhost:8765
```

---

## Why not just use Hunter.io?

|                   | Hunter.io     | Apollo.io     | **ColdReach**          |
| ----------------- | ------------- | ------------- | ---------------------- |
| Cost              | $34–$399/mo   | $49–$149/mo   | **Free**               |
| Self-hosted       | No            | No            | **Yes**                |
| Source code       | Closed        | Closed        | **MIT**                |
| Rate limits       | 25k/mo        | 10k/mo        | **None**               |
| API keys required | Yes           | Yes           | **No** (Groq optional) |
| Data privacy      | Their servers | Their servers | **Your machine only**  |

> **Accuracy:** ColdReach finds 50–70% of addresses vs 85–90% for Hunter.io. The gap narrows
> for companies with active GitHub presence. BYOK mode (plug in your own Hunter/Apollo key as a
> fallback) is planned for Phase 6.

---

## What's included

- **Terminal UI** — full-screen Textual app; emails stream live as each source finishes
- **8 discovery sources** — web crawl, GitHub commits, WHOIS, SearXNG, Reddit, SpiderFoot, theHarvester
- **SMTP verification** — 5-step pipeline ending with a real SMTP handshake via self-hosted Reacher
- **Groq drafting** — 3 subject variants + body generated from scraped company context (~2s)

  ![Draft panel — pick a subject, copy the full email](docs/images/draft.gif)

- **Outreach tracker** — draft → sent → replied, stored in SQLite, managed from the TUI

  ![Outreach tab](docs/images/outreach.png)
- **Chrome extension** — one-click find on Greenhouse, Lever, Indeed, LinkedIn, Workable
- **Local API server** — `coldreach serve` at localhost:8765 for scripting and automation

---

## Requirements

- Python 3.11+
- Docker (for SMTP verification, OSINT sources, and SearXNG metasearch)
- A free [Groq API key](https://console.groq.com) for email drafting (optional)

The pip-only install works for basic CLI use without SMTP verification or deep OSINT.

---

## Documentation

Full docs at **[dhruvmojila.github.io/coldreach](https://dhruvmojila.github.io/coldreach/)**

- [Getting Started](https://dhruvmojila.github.io/coldreach/getting-started/)
- [Interactive TUI](https://dhruvmojila.github.io/coldreach/tui/)
- [CLI Reference](https://dhruvmojila.github.io/coldreach/cli-reference/)
- [Outreach & Drafting](https://dhruvmojila.github.io/coldreach/outreach/)
- [Chrome Extension](https://dhruvmojila.github.io/coldreach/chrome-extension/)
- [API Server](https://dhruvmojila.github.io/coldreach/api-server/)
- [Discovery Sources](https://dhruvmojila.github.io/coldreach/sources/)
- [Configuration](https://dhruvmojila.github.io/coldreach/configuration/)

---

## License

MIT — see [LICENSE](LICENSE).
