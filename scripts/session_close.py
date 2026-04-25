#!/usr/bin/env python3
"""Automate end-of-session context updates for multi-agent handoff."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_DIR = ROOT / "context"
CURRENT_TASK = CONTEXT_DIR / "current-task.md"
HANDOFF = CONTEXT_DIR / "handoff.md"
DECISIONS = CONTEXT_DIR / "decisions.md"
PROGRESS = ROOT / "PROGRESS.md"


def now_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")


def git_branch() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def run_graph_update(mode: str) -> str:
    if mode == "skip":
        return "skipped"
    if mode == "full":
        return "requested_full_rebuild_use_assistant_command_/graphify_._manually"
    try:
        subprocess.check_call(["graphify", "update", "."], cwd=ROOT)
        return "graphify_update_ok"
    except Exception:
        return "graphify_update_failed_run_manually"


def write_current_task(agent: str, summary: str, next_step: str, verification: str) -> None:
    content = f"""# Current Task

## Now

- Owner agent: {agent}
- Branch: `{git_branch()}`
- Objective: {summary}

## In Progress

- [ ] {next_step}

## Done In This Session

- {summary}

## Next Action (Single Concrete Step)

- {next_step}

## Blockers

- None noted by automation. Update manually if needed.

## Verification Status

- {verification}
"""
    CURRENT_TASK.write_text(content, encoding="utf-8")


def append_handoff(agent: str, to_agent: str, summary: str, next_step: str, verification: str, graph_status: str) -> None:
    entry = f"""
### [{now_stamp()}] From {agent} to {to_agent}

- Branch: `{git_branch()}`
- Commit(s): pending
- Files changed:
  - update manually before commit
- What was completed:
  - {summary}
- What was attempted but not finished:
  - none noted
- Open risks/blockers:
  - update manually if any
- Verification performed:
  - {verification}
- Graph refresh:
  - {graph_status}
- Exact next step for receiver:
  - {next_step}
"""
    existing = HANDOFF.read_text(encoding="utf-8") if HANDOFF.exists() else "# Agent Handoff Log\n"
    HANDOFF.write_text(existing.rstrip() + "\n" + entry + "\n", encoding="utf-8")


def append_decisions(decisions: list[str]) -> None:
    if not decisions:
        return
    lines = [f"\n### [{now_stamp()}] Session close decisions\n"]
    for d in decisions:
        lines.append(f"- {d}")
    with DECISIONS.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def append_progress(agent: str, summary: str, next_step: str, graph_status: str) -> None:
    entry = f"""
## [{now_stamp()}] — Session close ({agent})

### What Was Done
- {summary}
- Context files were synchronized for cross-agent handoff.
- Graph refresh status: `{graph_status}`

### Next
- {next_step}
"""
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")


def stage_files() -> None:
    candidates = [
        "context/current-task.md",
        "context/handoff.md",
        "context/decisions.md",
        "PROGRESS.md",
        "graphify-out/GRAPH_REPORT.md",
        "graphify-out/graph.json",
    ]
    subprocess.call(["git", "add", *candidates], cwd=ROOT)


def ensure_context_files() -> None:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    for p in [CURRENT_TASK, HANDOFF, DECISIONS]:
        if not p.exists():
            p.write_text("", encoding="utf-8")
    if not PROGRESS.exists():
        PROGRESS.write_text("# Project Progress Log\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate session-end context updates.")
    parser.add_argument("--agent", required=True, help="Current agent name, e.g. Cursor or Claude Code")
    parser.add_argument("--to-agent", default="counterpart-agent", help="Handoff receiver")
    parser.add_argument("--summary", required=True, help="One-line session summary")
    parser.add_argument("--next-step", required=True, help="Single next action for receiver")
    parser.add_argument(
        "--verification",
        default="manual verification pending",
        help="Verification summary",
    )
    parser.add_argument(
        "--decision",
        action="append",
        default=[],
        help="Optional decision entry (can be repeated).",
    )
    parser.add_argument(
        "--graph",
        choices=["update", "full", "skip"],
        default="update",
        help="Graph refresh mode.",
    )
    parser.add_argument(
        "--no-stage",
        action="store_true",
        help="Do not run git add on context files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_context_files()
    graph_status = run_graph_update(args.graph)
    write_current_task(args.agent, args.summary, args.next_step, args.verification)
    append_handoff(
        args.agent,
        args.to_agent,
        args.summary,
        args.next_step,
        args.verification,
        graph_status,
    )
    append_decisions(args.decision)
    append_progress(args.agent, args.summary, args.next_step, graph_status)
    if not args.no_stage:
        stage_files()
    print("session_close: complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

