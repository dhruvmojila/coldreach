"""Inline Groq draft panel — used in the Find screen."""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static


class DraftPanel(Widget):
    """Slides in below a selected email row to generate a Groq draft."""

    DEFAULT_CSS = """
    DraftPanel {
        background: #1a1d27;
        border: round #3a3f5e;
        height: auto;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    DraftPanel #draft-title { color: #5b8cff; text-style: bold; }
    DraftPanel #draft-error { color: #f87171; }
    DraftPanel #draft-body-box {
        background: #13151f;
        border: round #2a2d3e;
        padding: 1 1;
        height: auto;
        color: #c9cde8;
    }
    DraftPanel #draft-subject { color: #5b8cff; text-style: bold; margin-bottom: 1; }
    DraftPanel #draft-status { color: #5b8cff; }
    """

    email: reactive[str] = reactive("")
    domain: reactive[str] = reactive("")

    BINDINGS = [Binding("escape", "close_panel", "Close")]

    def __init__(self, email: str, domain: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.email = email
        self.domain = domain
        self._stop: asyncio.Event | None = None

    def compose(self) -> ComposeResult:
        yield Label(f"✏️  Draft for [bold]{self.email}[/bold]", id="draft-title")
        yield Input(
            placeholder="Your name",
            id="sender-name",
            value=self._recall_name(),
        )
        yield Input(
            placeholder="What you want — one sentence",
            id="sender-intent",
        )
        yield Select(
            [
                ("🤖  Auto-detect", "auto"),
                ("🤝  Partnership", "partnership"),
                ("💼  Job application", "job_application"),
                ("💰  Sales outreach", "sales"),
                ("👋  Introduction", "introduction"),
            ],
            id="email-type",
            value="auto",
            allow_blank=False,
        )
        yield Button("✨  Generate draft", id="btn-generate", variant="primary")
        yield Static("", id="draft-status")
        yield Static("", id="draft-body-box")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate":
            self._generate()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._generate()

    def _generate(self) -> None:
        name = str(self.query_one("#sender-name", Input).value).strip()
        intent = str(self.query_one("#sender-intent", Input).value).strip()
        if not name or not intent:
            self.query_one("#draft-status", Static).update(
                "[#f87171]Fill in your name and intent first.[/]"
            )
            return
        self._save_name(name)
        etype = str(self.query_one("#email-type", Select).value)
        self.query_one("#draft-status", Static).update(
            "[#5b8cff]Reading company site… writing draft…[/]"
        )
        self.query_one("#draft-body-box", Static).update("")
        self.run_worker(
            self._run_draft(name, intent, etype),
            name="draft-worker",
            exclusive=True,
        )

    async def _run_draft(self, name: str, intent: str, etype: str) -> None:
        try:
            from coldreach.outreach.context import get_company_context
            from coldreach.outreach.draft import draft_email
            from coldreach.outreach.templates import EmailType, auto_detect_type

            context = await get_company_context(self.domain)
            resolved_type = auto_detect_type(intent) if etype == "auto" else EmailType(etype)
            draft = await draft_email(
                email=self.email,
                context=context,
                sender_name=name,
                sender_intent=intent,
                email_type=resolved_type,
            )
            self.query_one("#draft-status", Static).update(
                "[#34d399]✓  Draft ready — press [bold]y[/bold] to copy[/]"
            )
            self.query_one("#draft-body-box", Static).update(
                f"[bold #5b8cff]Subject[/bold]\n{draft.subject}\n\n"
                f"[bold #5b8cff]Body[/bold]\n{draft.body}\n\n"
                f"[dim]Best,\n{name}[/dim]"
            )
            # Store draft for copy action
            self._current_draft = f"Subject: {draft.subject}\n\n{draft.body}\n\nBest,\n{name}"
        except ValueError as exc:
            self.query_one("#draft-status", Static).update(f"[#f87171]{exc}[/]")
        except Exception as exc:
            self.query_one("#draft-status", Static).update(f"[#f87171]Draft failed: {exc}[/]")

    def copy_draft(self) -> bool:
        """Copy current draft to clipboard. Returns True if content was available."""
        draft = getattr(self, "_current_draft", "")
        if not draft:
            return False
        import subprocess

        for cmd in [
            ["xclip", "-selection", "clipboard"],
            ["pbcopy"],
            ["xsel", "--clipboard", "--input"],
        ]:
            try:
                subprocess.run(cmd, input=draft.encode(), check=True, capture_output=True)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        return False

    def action_close_panel(self) -> None:
        self.remove()

    @staticmethod
    def _recall_name() -> str:
        try:
            import json
            from pathlib import Path

            p = Path("~/.coldreach/tui_prefs.json").expanduser()
            if p.exists():
                return json.loads(p.read_text()).get("sender_name", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _save_name(name: str) -> None:
        try:
            import json
            from pathlib import Path

            p = Path("~/.coldreach/tui_prefs.json").expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if p.exists():
                data = json.loads(p.read_text())
            data["sender_name"] = name
            p.write_text(json.dumps(data))
        except Exception:
            pass
