# Agent Instructions

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

## Session-Close Skill

At the end of each substantial session, run:

`python3 scripts/session_close.py --agent "Cursor" --to-agent "Claude Code" --summary "<summary>" --next-step "<next step>" --verification "<verification>" --graph update`

Skill reference:

- `skills/session-close/SKILL.md`

