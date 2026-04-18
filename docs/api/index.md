# API Reference

ColdReach is structured as a set of importable Python modules. All public APIs are documented here — auto-generated from docstrings in the source code.

## Packages

| Package | Description |
| ------- | ----------- |
| [`coldreach.core.models`](models.md) | Pydantic data models — `DomainResult`, `EmailRecord`, `SourceRecord` |
| [`coldreach.verify`](verify.md) | Verification pipeline — `run_basic_pipeline`, individual checkers |
| [`coldreach.sources`](sources.md) | Discovery sources — `BaseSource`, `SourceResult`, all source implementations |
| [`coldreach.generate`](generate.md) | Email pattern generation — `generate_patterns`, `targeted_patterns` |
| [`coldreach.storage`](storage.md) | Cache layer — `CacheStore` (SQLite + Redis) |

## Typical usage

```python
import asyncio
from coldreach.verify import run_basic_pipeline
from coldreach.core.finder import FinderConfig, find_emails

# Verify a single email
async def main():
    result = await run_basic_pipeline(
        "john@acme.com",
        reacher_url="http://localhost:8083",
    )
    print(result.score, result.passed)

    # Find emails for a domain
    config = FinderConfig(domain="acme.com", person_name="Jane Smith")
    domain_result = await find_emails(config)
    for email in domain_result.emails:
        print(email.email, email.confidence)

asyncio.run(main())
```

!!! note "Docstring convention"
    All docstrings use **NumPy style** (`Parameters\n----------`).
    mkdocstrings renders them as formatted tables automatically.
