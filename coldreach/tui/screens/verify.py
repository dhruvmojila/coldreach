"""Verify screen — runs the full pipeline on a single email."""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static


class VerifyScreen(Widget):
    """Single-email verification pipeline display."""

    DEFAULT_CSS = """
    VerifyScreen { height: 100%; padding: 1 2; }
    #verify-top { height: 3; align: left middle; margin-bottom: 1; }
    #email-input { width: 50; margin-right: 1; }
    #score-display {
        color: #5b8cff;
        text-style: bold;
        height: 1;
        margin: 1 0 1 0;
    }
    #checks-container { height: auto; margin-left: 2; }
    .check-row { height: 1; margin: 0; }
    .check-icon { width: 3; }
    .check-name { width: 16; color: #9aa0c0; }
    .check-detail { color: #6b7099; }
    #verify-actions { margin-top: 1; height: 3; }
    #verify-hint { color: #6b7099; height: 1; margin-top: 1; }
    """

    BINDINGS = [
        Binding("h", "run_holehe", "Holehe check"),
        Binding("f", "goto_find", "Find domain"),
        Binding("y", "yank_email", "Copy email"),
    ]

    _STEPS = ["syntax", "disposable", "dns", "reacher"]
    _STEP_LABELS = {
        "syntax": "Syntax",
        "disposable": "Disposable",
        "dns": "DNS / MX",
        "reacher": "SMTP (Reacher)",
    }

    def __init__(self, prefill: str = "", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._prefill = prefill
        self._current_email = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="verify-top"):
            yield Input(placeholder="email@company.com", id="email-input", value=self._prefill)
            yield Button("▶  Verify", id="btn-verify", variant="primary")

        yield Static("", id="score-display")

        with Vertical(id="checks-container"):
            for step in self._STEPS:
                with Horizontal(classes="check-row", id=f"row-{step}"):
                    yield Label("○", classes="check-icon", id=f"icon-{step}")
                    yield Label(self._STEP_LABELS[step], classes="check-name")
                    yield Label("—", classes="check-detail", id=f"detail-{step}")

            # Holehe row (hidden by default)
            with Horizontal(classes="check-row", id="row-holehe"):
                yield Label("○", classes="check-icon", id="icon-holehe")
                yield Label("Holehe", classes="check-name")
                yield Label("press h to run", classes="check-detail", id="detail-holehe")

        with Horizontal(id="verify-actions"):
            yield Button("h: Holehe check", id="btn-holehe", variant="default")
            yield Button("f: Find domain", id="btn-find", variant="default")
            yield Button("y: Copy email", id="btn-yank", variant="default")

        yield Label("", id="verify-hint")

    def on_mount(self) -> None:
        if self._prefill:
            self._run_verify(self._prefill)

    @on(Button.Pressed, "#btn-verify")
    def _on_verify(self) -> None:
        email = self.query_one("#email-input", Input).value.strip()
        if email:
            self._run_verify(email)

    @on(Input.Submitted, "#email-input")
    def _on_submit(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self._run_verify(event.value.strip())

    @on(Button.Pressed, "#btn-holehe")
    def _on_holehe_btn(self) -> None:
        self.action_run_holehe()

    @on(Button.Pressed, "#btn-find")
    def _on_find_btn(self) -> None:
        self.action_goto_find()

    @on(Button.Pressed, "#btn-yank")
    def _on_yank_btn(self) -> None:
        self.action_yank_email()

    def _reset_ui(self) -> None:
        self.query_one("#score-display", Static).update("")
        for step in self._STEPS:
            self.query_one(f"#icon-{step}", Label).update("○")
            self.query_one(f"#icon-{step}").styles.color = "#6b7099"
            self.query_one(f"#detail-{step}", Label).update("—")
        self.query_one("#icon-holehe", Label).update("○")
        self.query_one("#detail-holehe", Label).update("press h to run")

    @work(thread=False, name="verify-worker", exclusive=True)
    async def _run_verify(self, email: str) -> None:
        self._current_email = email
        self._reset_ui()
        self.query_one("#verify-hint", Label).update(f"[dim]Verifying [bold]{email}[/]…[/]")

        # Animate — show running state per step
        for step in self._STEPS:
            self.query_one(f"#icon-{step}", Label).update("⟳")
            self.query_one(f"#icon-{step}").styles.color = "#5b8cff"

        from coldreach.config import get_settings
        from coldreach.verify.pipeline import run_basic_pipeline

        cfg = get_settings()
        result = await run_basic_pipeline(
            email,
            reacher_url=cfg.reacher_url if cfg else None,
            run_holehe=False,
        )

        _color = {"pass": "#34d399", "fail": "#f87171", "warn": "#f59e0b", "skip": "#6b7099"}
        _icon = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "○"}

        for step in self._STEPS:
            check = result.checks.get(step)
            if check is None:
                self.query_one(f"#icon-{step}", Label).update("○")
                self.query_one(f"#icon-{step}").styles.color = "#6b7099"
                self.query_one(f"#detail-{step}", Label).update("not run")
                continue
            s = check.status.value
            icon = _icon.get(s, "○")
            color = _color.get(s, "#6b7099")
            self.query_one(f"#icon-{step}", Label).update(icon)
            self.query_one(f"#icon-{step}").styles.color = color
            self.query_one(f"#detail-{step}", Label).update(check.reason or check.status.value)

        score = result.score
        score_color = "#34d399" if score >= 70 else "#f59e0b" if score >= 40 else "#f87171"
        self.query_one("#score-display", Static).update(f"[{score_color}]{score}[/] [dim]/ 100[/]")

        domain = email.split("@")[1] if "@" in email else ""
        self.query_one("#verify-hint", Label).update(
            f"[dim]MX: {', '.join(result.mx_records[:2]) or 'none found'}[/]"
        )
        self.app.post_message(self.VerifyDone(email, score))

    @work(thread=False, name="holehe-worker", exclusive=True)
    async def _run_holehe(self) -> None:
        email = self._current_email
        if not email:
            return
        self.query_one("#icon-holehe", Label).update("⟳")
        self.query_one("#icon-holehe").styles.color = "#5b8cff"
        self.query_one("#detail-holehe", Label).update("checking…")

        from coldreach.verify.holehe import check_holehe

        result = await check_holehe(email)
        platforms = result.metadata.get("platforms", [])
        if result.status.value == "pass" and platforms:
            self.query_one("#icon-holehe", Label).update("✓")
            self.query_one("#icon-holehe").styles.color = "#34d399"
            self.query_one("#detail-holehe", Label).update(
                f"Found on {len(platforms)} platform(s): {', '.join(platforms[:3])}"
            )
        elif result.status.value == "skip":
            self.query_one("#icon-holehe", Label).update("○")
            self.query_one("#icon-holehe").styles.color = "#6b7099"
            self.query_one("#detail-holehe", Label).update(result.reason)
        else:
            self.query_one("#icon-holehe", Label).update("○")
            self.query_one("#icon-holehe").styles.color = "#6b7099"
            self.query_one("#detail-holehe", Label).update("not registered on known platforms")

    class VerifyDone(Message):
        def __init__(self, email: str, score: int) -> None:
            super().__init__()
            self.email = email
            self.score = score

    def action_run_holehe(self) -> None:
        if self._current_email:
            self._run_holehe()
        else:
            self.app.notify("Run a verification first", severity="warning")

    def action_goto_find(self) -> None:
        domain = ""
        if "@" in self._current_email:
            domain = self._current_email.split("@")[1]
        self.app.switch_to_find(domain)

    def action_yank_email(self) -> None:
        if not self._current_email:
            return
        import subprocess

        e = self._current_email
        for cmd in [["xclip", "-selection", "clipboard"], ["pbcopy"]]:
            try:
                subprocess.run(cmd, input=e.encode(), check=True, capture_output=True)
                self.app.notify(f"Copied: {e}", timeout=2)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        self.app.notify(e, title="Email (copy manually)", timeout=5)
