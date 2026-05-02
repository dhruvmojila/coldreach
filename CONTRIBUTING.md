# Contributing to ColdReach

Thank you for helping make ColdReach better. This guide covers everything you need to get started.

## Ways to Contribute

- **Bug reports** — open an issue with the `bug` label
- **Feature requests** — open an issue with the `enhancement` label
- **Code** — fix a bug, add a source, improve accuracy
- **Docs** — fix typos, add examples, improve clarity
- **Job board parsers** — the Chrome extension needs parsers for more ATS platforms

## Development Setup

```bash
git clone https://github.com/dhruvmojila/coldreach.git
cd coldreach
./scripts/setup.sh          # clones OSINT tools, builds Docker images
uv sync --all-extras --dev  # install all Python deps
docker compose up -d        # start services
coldreach status            # verify everything is up
```

## Running Tests

```bash
uv run pytest tests/unit -v          # fast unit tests (no Docker needed)
uv run pytest tests/ -v              # all tests
uv run ruff check coldreach tests    # lint
uv run ruff format coldreach tests   # format
uv run mypy coldreach                # type check
```

Or use the Makefile:

```bash
make test   # pytest
make lint   # ruff + mypy
make fmt    # auto-format
```

## Adding a New Email Source

1. Create `coldreach/sources/your_source.py` — subclass `BaseSource`
2. Implement `async def fetch(self, domain, *, person_name=None) -> list[SourceResult]`
3. Register it in `coldreach/core/finder.py` → `_build_sources()`
4. Add it to `_SLOW_SOURCE_NAMES` if it takes > 60s
5. Write tests in `tests/unit/test_sources_your_source.py`
6. Document it in `docs/sources.md`

```python
class YourSource(BaseSource):
    name = "your_source"  # must be unique

    async def fetch(self, domain: str, *, person_name: str | None = None) -> list[SourceResult]:
        # never raise — catch all exceptions and return []
        results = []
        ...
        return results
```

## Adding a Job Board Parser (Chrome Extension)

Add a new file `chrome-extension/src/content/yourboard.ts` with:

```typescript
export function detectYourBoard(): JobContext | null {
  // check hostname/URL pattern
  // extract company name + job title
  // return null if not a job page
}
```

Then import and call it in `chrome-extension/src/content/index.ts`.

## Pull Request Guidelines

- **One PR per concern** — don't mix unrelated changes
- **Tests required** — new sources need unit tests with mocked HTTP
- **CI must pass** — ruff, mypy, pytest all green
- **Describe the why** — explain what problem the PR solves

## Code Style

- Python: `ruff` for lint/format, `mypy --strict` for types
- TypeScript: standard TS strict mode
- No `print()` — use `logging.getLogger(__name__)`
- Async everywhere in Python sources — no blocking calls on the event loop
- Sources must never raise — catch exceptions and return `[]`

## Commit Messages

Follow conventional commits:

```
feat: add CommonCrawl email source
fix: web crawler regex misses JSON-embedded emails
docs: add API server endpoint reference
test: add SpiderFoot REST API mock tests
```

## License

By contributing you agree that your contributions will be licensed under the MIT License.
