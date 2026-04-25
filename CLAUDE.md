# Claude Code Instructions

Before any implementation work, read in order:

1. `CONTEXT_MANAGEMENT.md`
2. `context/current-task.md`
3. latest entry in `context/handoff.md`
4. `graphify-out/GRAPH_REPORT.md`
5. latest relevant section in `PROGRESS.md`

At session end, update:

- `context/current-task.md`
- `context/handoff.md`
- `context/decisions.md` (if a decision was made)
- `PROGRESS.md` (for significant changes)

If these files are not updated, handoff is considered incomplete.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## Session-Close Skill

At the end of each substantial session, run:

`python3 scripts/session_close.py --agent "Claude Code" --to-agent "Cursor" --summary "<summary>" --next-step "<next step>" --verification "<verification>" --graph update`

Skill reference:

- `skills/session-close/SKILL.md`
