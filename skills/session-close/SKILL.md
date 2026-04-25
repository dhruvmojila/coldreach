# Skill: session-close

Automate end-of-session context synchronization and handoff for this repo.

## Trigger

Use this at the end of any substantial implementation/review session, especially before switching between Cursor and Claude Code.

## Command

```bash
python3 scripts/session_close.py \
  --agent "<Cursor|Claude Code>" \
  --to-agent "<receiver>" \
  --summary "<one-line summary>" \
  --next-step "<single concrete next action>" \
  --verification "<tests/lint/manual checks summary>" \
  --decision "<optional decision 1>" \
  --decision "<optional decision 2>" \
  --graph update
```

## What It Automates

- Updates `context/current-task.md`
- Appends `context/handoff.md`
- Appends `context/decisions.md` (if `--decision` is provided)
- Appends `PROGRESS.md`
- Runs `graphify update .` by default
- Stages context + graph files with `git add`

## Notes

- Use `--graph full` if a full rebuild is needed; this records intent but still requires assistant `/graphify .` command.
- Use `--graph skip` only for docs-only handoff where graph refresh is intentionally deferred.
- Use `--no-stage` if you explicitly do not want automatic staging.

