## Summary

<!-- What does this PR do? Why? -->

## Type of change

- [ ] Bug fix
- [ ] New feature / source
- [ ] Performance improvement
- [ ] Documentation
- [ ] Refactoring
- [ ] Chrome extension

## Testing

- [ ] Unit tests added / updated (`uv run pytest tests/unit -v`)
- [ ] All tests pass (`uv run pytest tests/`)
- [ ] Lint passes (`uv run ruff check coldreach tests`)
- [ ] Format passes (`uv run ruff format --check coldreach tests`)
- [ ] Type check passes (`uv run mypy coldreach`)

## For new email sources

- [ ] Subclasses `BaseSource`, implements `fetch()`
- [ ] Never raises — catches all exceptions, returns `[]`
- [ ] Tested with mocked HTTP (no real network calls in tests)
- [ ] Registered in `finder.py` `_build_sources()`
- [ ] Documented in `docs/sources.md`
- [ ] Added to `_SLOW_SOURCE_NAMES` if > 60s

## Screenshots / output

<!-- Paste example output if relevant -->

## Related issues

Closes #
