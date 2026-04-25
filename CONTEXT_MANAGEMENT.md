# Context Management (Cursor + Claude Code)

This repository uses a shared, file-based context protocol so you can switch between Cursor and Claude Code without knowledge gaps.

## Why This Exists

- Avoid "agent memory reset" when switching tools.
- Keep architecture and decision context persistent in git.
- Make onboarding reproducible for a new repo or new teammate.

## Required Files

- `graphify-out/GRAPH_REPORT.md` - high-level map of system communities.
- `graphify-out/graph.json` - detailed graph data for targeted queries.
- `context/current-task.md` - what is in progress right now.
- `context/decisions.md` - architectural and process decisions.
- `context/handoff.md` - latest transfer notes between agents.
- `PROGRESS.md` - chronological change log.

## Agent Startup Protocol (Both Cursor and Claude Code)

On every fresh session, do this in order:

1. Read `context/current-task.md`.
2. Read latest section of `context/handoff.md`.
3. Read `graphify-out/GRAPH_REPORT.md` for architecture orientation.
4. Read latest entries in `PROGRESS.md`.
5. Only then start edits.

If any file is missing or stale, update it before coding.

## Session-End Protocol (Mandatory)

Before ending any substantial session, run this first:

`python3 scripts/session_close.py --agent "<Cursor|Claude Code>" --to-agent "<receiver>" --summary "<summary>" --next-step "<next step>" --verification "<verification>" --graph update`

Then verify output and fill any missing nuance manually if needed.

Legacy manual checklist (covered by the command above):

1. Update `context/current-task.md`:
   - what was done
   - what is next
   - blockers
2. Append one entry to `context/handoff.md`:
   - timestamp
   - branch
   - changed files
   - verification done / not done
   - exact next action
3. Append key decisions to `context/decisions.md`.
4. Add a summary entry to `PROGRESS.md` for major changes.
5. Refresh graph context:
   - run `graphify update .` for code updates
   - run full `/graphify .` in assistant when docs/architecture changed significantly

## Automatic vs Manual

### Automatic

- Cursor always-on graph reminder via `.cursor/rules/graphify.mdc`.
- Git hooks (`post-commit`, `post-checkout`) installed by `graphify hook install`.
- Graphify cache reuse under `graphify-out/cache/`.
- Shared graph artifacts in git when committed (`GRAPH_REPORT.md`, `graph.json`, optional `graph.html`).

### Manual (You Must Do)

- Keep `context/current-task.md`, `context/decisions.md`, and `context/handoff.md` updated.
- Rebuild/update graph when context becomes stale.
- Ensure both agents read the protocol files at session start.
- Commit context changes with code changes (do not leave handoff files local-only).

## Fresh Repo Setup Checklist (Linux)

1. Install graphify:
   - `python3 -m pip install --upgrade graphifyy`
2. Install Cursor integration in repo root:
   - `graphify cursor install`
3. Install Claude Code integration in repo root:
   - `graphify claude install`
4. Create `.graphifyignore` suited for the project.
5. Build initial graph using assistant command:
   - `/graphify .`
6. Install hooks:
   - `graphify hook install`
7. Create `context/` files from templates in this repo.
8. Commit baseline context files + graph outputs.

## Operating Model for Two Agents

- Cursor handles implementation-heavy coding loops.
- Claude Code handles large-scale analysis, doc synthesis, and second-opinion reviews.
- Both must write to the same `context/` files after each session.

Never assume the counterpart agent "knows what happened." If it is not written in the context files, it does not exist.

## Quick Commands

- Refresh code graph quickly: `graphify update .`
- Check shortest path in graph: `graphify path "NodeA" "NodeB" --graph graphify-out/graph.json`
- Query graph: `graphify query "show auth flow" --graph graphify-out/graph.json`
- Check hooks: `graphify hook status`

