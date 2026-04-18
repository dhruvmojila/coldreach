# ColdReach

**Open-source email finder and lead discovery — free alternative to Hunter.io and Apollo.io.**

[![CI](https://github.com/dhruvmojila/coldreach/actions/workflows/ci.yml/badge.svg)](https://github.com/dhruvmojila/coldreach/actions)
[![PyPI](https://img.shields.io/pypi/v/coldreach)](https://pypi.org/project/coldreach/)
[![Python](https://img.shields.io/pypi/pyversions/coldreach)](https://pypi.org/project/coldreach/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://dhruvmojila.github.io/coldreach/)

---

## Install

**Simple** (once on PyPI — no Docker required for basic use):
```bash
pip install coldreach
```

**Full stack** (clone + Docker for SMTP verification and deep OSINT):
```bash
git clone https://github.com/dhruvmojila/coldreach.git && cd coldreach
./scripts/setup.sh && docker compose up -d && pip install coldreach
```

## Quick start

```bash
coldreach verify john@acme.com                          # verify an email
coldreach find --domain acme.com --quick                # discover emails
coldreach find --domain acme.com --name "Jane Smith"    # target a person
coldreach cache list                                    # manage cache
```

## Why ColdReach?

|                   | Hunter.io   | Apollo.io   | **ColdReach**          |
| ----------------- | ----------- | ----------- | ---------------------- |
| Cost              | $34–$399/mo | $49–$149/mo | **Free forever**       |
| Self-hosted       | No          | No          | **Yes**                |
| API keys required | Yes         | Yes         | **No** (Groq optional) |
| Rate limits       | 25k/mo      | 10k/mo      | **None (local)**       |
| Privacy           | Their servers | Their servers | **Your machine only** |

## Documentation

Full docs at **[dhruvmojila.github.io/coldreach](https://dhruvmojila.github.io/coldreach/)**

- [Getting Started](https://dhruvmojila.github.io/coldreach/getting-started/)
- [CLI Reference](https://dhruvmojila.github.io/coldreach/cli-reference/)
- [How It Works](https://dhruvmojila.github.io/coldreach/how-it-works/)
- [Discovery Sources](https://dhruvmojila.github.io/coldreach/sources/)
- [Configuration](https://dhruvmojila.github.io/coldreach/configuration/)
- [API Reference](https://dhruvmojila.github.io/coldreach/api/)

## License

MIT — see [LICENSE](LICENSE).
