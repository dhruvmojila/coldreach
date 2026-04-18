# Cache & Storage API

Two-layer cache: SQLite (always-on) + Redis (optional). Results are stored as JSON-serialized `DomainResult` objects with a configurable TTL.

---

## Cache store

::: coldreach.storage.cache

---

## Finder config & orchestration

::: coldreach.core.finder
