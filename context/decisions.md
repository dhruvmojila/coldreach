# Decisions Log

Record decisions that affect architecture, tooling, workflow, or team conventions.

### [2026-04-25 09:45 UTC-4] File-based cross-agent context protocol

- Context:
  - Project work is split between Cursor and Claude Code due to usage limits.
  - Agent switching caused risk of stale or missing context.
- Decision:
  - Adopt a repo-committed protocol with mandatory files: `CONTEXT_MANAGEMENT.md`, `context/current-task.md`, `context/handoff.md`, `context/decisions.md`, plus graph outputs.
- Alternatives considered:
  - Rely on chat history only (rejected: non-portable and inconsistent).
  - Keep handoff docs outside repo (rejected: not visible to counterpart agent by default).
- Consequences:
  - Slight manual overhead each session.
  - Significant reduction in context drift when swapping agents or machines.
- Owner:
  - Repo maintainer

## Template

### [YYYY-MM-DD HH:MM TZ] Decision title

- Context:
- Decision:
- Alternatives considered:
- Consequences:
- Owner:


### [2026-04-25 09:42 EDT] Session close decisions

- Use scripts/session_close.py as mandatory end-of-session workflow for both agents

### [2026-04-25 10:13 EDT] Session close decisions

- Firecrawl is a separate-stack optional add-on — not in default docker-compose; status shows it separately from core services
- Reacher health check uses TCP probe (bash /dev/tcp) not HTTP GET — the service has no HTTP root endpoint by design
- scripts/setup.sh is now the canonical first-time setup path — handles prereqs, clone, build, wait-for-healthy, verify

### [2026-04-25 12:27 EDT] Session close decisions

- API defaults to quick=true for extension requests (10s target); SSE stream endpoint separate from blocking JSON endpoint
