"""Inline Groq draft panel — used in the Find screen and Outreach screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static

_FAST_MODEL = "groq/llama-3.1-8b-instant"
_QUALITY_MODEL = "groq/llama-3.3-70b-versatile"


class DraftPanel(Widget):
    """Slides in below a selected email row to generate a Groq draft.

    Features:
    - Company context preview (fetched on mount)
    - 3 subject line variants — press 1/2/3 to pick
    - Fast (8b) vs Quality (70b) model toggle
    - Regenerate without closing
    - Auto-saves to OutreachTracker on success
    - No-key fallback: shows template skeleton
    """

    DEFAULT_CSS = """
    DraftPanel {
        background: #1a1d27;
        border: tall #3a3f5e;
        height: auto;
        max-height: 24;
        padding: 1 2;
        margin: 1 0;
        overflow-y: auto;
    }
    DraftPanel #context-bar {
        color: #9aa0c0;
        height: 2;
        margin-bottom: 1;
        background: #13151f;
        padding: 0 1;
    }
    DraftPanel #draft-title { color: #5b8cff; text-style: bold; height: 1; }
    DraftPanel #form-row { height: 3; align: left middle; margin-bottom: 1; }
    DraftPanel #model-row { height: 3; align: left middle; margin-bottom: 1; }
    DraftPanel #btn-fast { min-width: 22; margin-right: 1; }
    DraftPanel #btn-quality { min-width: 28; }
    DraftPanel #btn-generate { min-width: 18; margin-right: 1; }
    DraftPanel #btn-regen { min-width: 16; }
    DraftPanel #draft-status { color: #5b8cff; height: 1; margin-bottom: 1; }
    DraftPanel #subjects-box {
        background: #13151f;
        border: tall #2a2d3e;
        padding: 1 1;
        height: auto;
        margin-bottom: 1;
    }
    DraftPanel #draft-body-box {
        background: #13151f;
        border: tall #2a2d3e;
        padding: 1 1;
        height: auto;
        color: #c9cde8;
    }
    """

    BINDINGS = [
        Binding("1", "pick_subject('0')", "Subject A", show=False),
        Binding("2", "pick_subject('1')", "Subject B", show=False),
        Binding("3", "pick_subject('2')", "Subject C", show=False),
        Binding("y", "copy_draft", "Copy draft"),
        Binding("escape", "close_panel", "Close"),
    ]

    email: reactive[str] = reactive("")
    domain: reactive[str] = reactive("")

    def __init__(self, email: str, domain: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.email = email
        self.domain = domain
        self._current_draft: str = ""
        self._subjects: list[str] = []
        self._subjects_safe: list[str] = []
        self._selected_subject_idx: int = 0
        self._body: str = ""
        self._body_safe: str = ""
        self._sender_name: str = ""
        self._model: str = _FAST_MODEL

    def compose(self) -> ComposeResult:
        yield Label(f"Draft for [bold]{self.email}[/bold]", id="draft-title")
        yield Static("Fetching company info…", id="context-bar")
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
                ("Auto-detect", "auto"),
                ("Partnership", "partnership"),
                ("Job application", "job_application"),
                ("Sales outreach", "sales"),
                ("Introduction", "introduction"),
            ],
            id="email-type",
            value="auto",
            allow_blank=False,
        )
        from textual.containers import Horizontal

        with Horizontal(id="model-row"):
            yield Button("Fast (llama-3.1-8b)", id="btn-fast", variant="primary")
            yield Button("Quality (llama-3.3-70b)", id="btn-quality", variant="default")
        with Horizontal(id="form-row"):
            yield Button("Generate draft", id="btn-generate", variant="primary")
            yield Button("Regenerate", id="btn-regen", variant="default")
        yield Static("", id="draft-status")
        yield Static("", id="subjects-box")
        yield Static("", id="draft-body-box")

    def on_mount(self) -> None:
        self.run_worker(self._fetch_context(), name="context-fetch", exclusive=False)

    async def _fetch_context(self) -> None:
        """Fetch company context immediately on mount — shown before user generates."""
        try:
            from coldreach.outreach.context import get_company_context

            ctx = await get_company_context(self.domain)
            from rich.markup import escape

            parts = [p for p in [ctx.name, ctx.industry, ctx.location] if p]
            summary = escape("  ·  ".join(parts) if parts else self.domain)
            desc = escape((ctx.description or "")[:100])
            if not self.is_attached:
                return
            self.query_one("#context-bar", Static).update(
                f"[bold #9aa0c0]{summary}[/]\n[dim]{desc}[/]"
                if desc
                else f"[bold #9aa0c0]{summary}[/]"
            )
            self._ctx = ctx
        except Exception:
            if not self.is_attached:
                return
            self.query_one("#context-bar", Static).update(
                f"[#9aa0c0]{self.domain}[/]  [dim #f59e0b]· could not fetch company info[/]"
            )
            self._ctx = None

    # ── Model toggle ──────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-generate", "btn-regen"):
            self._generate()
        elif event.button.id == "btn-fast":
            self._set_model(_FAST_MODEL)
        elif event.button.id == "btn-quality":
            self._set_model(_QUALITY_MODEL)

    def _set_model(self, model: str) -> None:
        self._model = model
        fast = self.query_one("#btn-fast", Button)
        quality = self.query_one("#btn-quality", Button)
        if model == _FAST_MODEL:
            fast.variant = "primary"
            quality.variant = "default"
        else:
            fast.variant = "default"
            quality.variant = "primary"

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._generate()

    # ── Generation ────────────────────────────────────────────────────────────

    def _generate(self) -> None:
        name = str(self.query_one("#sender-name", Input).value).strip()
        intent = str(self.query_one("#sender-intent", Input).value).strip()
        if not name or not intent:
            self.query_one("#draft-status", Static).update(
                "[#f87171]Fill in your name and intent first.[/]"
            )
            return
        self._sender_name = name
        self._save_name(name)
        etype = str(self.query_one("#email-type", Select).value)
        self.query_one("#draft-status", Static).update(
            "[#5b8cff]Reading company site… writing draft…[/]"
        )
        self.query_one("#subjects-box", Static).update("")
        self.query_one("#draft-body-box", Static).update("")
        self._subjects = []
        self._current_draft = ""
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

            ctx = getattr(self, "_ctx", None) or await get_company_context(self.domain)
            resolved_type = auto_detect_type(intent) if etype == "auto" else EmailType(etype)
            draft = await draft_email(
                email=self.email,
                context=ctx,
                sender_name=name,
                sender_intent=intent,
                email_type=resolved_type,
                model=self._model,
            )
            from rich.markup import escape as _esc

            # Store originals for clipboard; store escaped for display
            self._subjects = draft.subjects
            self._subjects_safe = [_esc(s) for s in draft.subjects]
            self._body = draft.body
            self._body_safe = _esc(draft.body)
            self._selected_subject_idx = 0
            self._rebuild_draft()
            self._save_to_outreach(draft.subjects[0], draft.body, str(draft.email_type))
            self.query_one("#draft-status", Static).update(
                "[#34d399]Done — press [bold]1/2/3[/] to pick subject, [bold]y[/] to copy[/]"
            )
        except ValueError as exc:
            msg = str(exc)
            if "Groq API key" in msg:
                self._render_template_mode(etype)
            else:
                from rich.markup import escape
                self.query_one("#draft-status", Static).update(f"[#f87171]{escape(msg)}[/]")
        except Exception as exc:
            from rich.markup import escape
            self.query_one("#draft-status", Static).update(
                f"[#f87171]Draft failed: {escape(str(exc))}[/]"
            )

    def _rebuild_draft(self) -> None:
        """Refresh subjects display and current_draft from stored state."""
        if not self._subjects:
            return
        # Use pre-escaped strings stored at generation time — never re-escape
        subjects_safe = getattr(self, "_subjects_safe", self._subjects)
        body_safe = getattr(self, "_body_safe", self._body)

        labels = ["A", "B", "C"]
        lines = []
        for i, (label, safe) in enumerate(zip(labels, subjects_safe, strict=False)):
            if i == self._selected_subject_idx:
                lines.append(f"[bold #5b8cff]{label}: {safe}[/]  ← selected")
            else:
                lines.append(f"[dim]{label}: {safe}[/]  [dim](press {i + 1})[/]")
        self.query_one("#subjects-box", Static).update("\n".join(lines))
        # Use [/] not [/bold] — compound styles need [/] to close cleanly
        self.query_one("#draft-body-box", Static).update(
            f"[bold #5b8cff]Body[/]\n{body_safe}"
        )
        selected = self._subjects[self._selected_subject_idx]
        self._current_draft = f"Subject: {selected}\n\n{self._body}\n\nBest,\n{self._sender_name}"

    def _render_template_mode(self, etype: str) -> None:
        """Show template skeleton when Groq key is missing."""
        templates = {
            "partnership": (
                "Partnership opportunity with [COMPANY]",
                "Hi [NAME], I came across [COMPANY] and think there's a natural fit "
                "between your work and [WHAT YOU DO]. Would you be open to a quick chat "
                "about [SPECIFIC GOAL]?\n\n[YOUR NAME]",
            ),
            "job_application": (
                "Interested in [ROLE] at [COMPANY]",
                "Hi [NAME], I've been following [COMPANY]'s work on [SPECIFIC THING] "
                "and would love to bring my [SKILL] to your team. "
                "Would you have 15 minutes to connect?\n\n[YOUR NAME]",
            ),
            "sales": (
                "[COMPANY] — quick question",
                "Hi [NAME], I help companies like [COMPANY] with [PROBLEM]. "
                "Have you run into [PAIN POINT] recently? "
                "Happy to share how we solved it for [SIMILAR COMPANY].\n\n[YOUR NAME]",
            ),
            "introduction": (
                "Quick intro — [YOUR NAME]",
                "Hi [NAME], I'm [YOUR NAME] and I [WHAT YOU DO]. "
                "I came across [COMPANY] and wanted to say hello "
                "— I think we might have some overlap worth exploring.\n\n[YOUR NAME]",
            ),
        }
        subj, body = templates.get(etype, templates["introduction"])
        self._subjects = [subj]
        self._body = body
        self._selected_subject_idx = 0
        self._rebuild_draft()
        self.query_one("#draft-status", Static).update(
            "[#f59e0b]No Groq key — showing template. "
            "Set COLDREACH_GROQ_API_KEY in .env for AI drafts.[/]"
        )

    def _save_to_outreach(self, subject: str, body: str, email_type: str) -> None:
        try:
            from coldreach.outreach.tracker import OutreachTracker

            OutreachTracker().save_draft(
                email=self.email,
                domain=self.domain,
                subject=subject,
                body=body,
                email_type=email_type,
            )
        except Exception:
            pass

    # ── Subject picking ───────────────────────────────────────────────────────

    def action_pick_subject(self, idx_str: str) -> None:
        idx = int(idx_str)
        if idx < len(self._subjects):
            self._selected_subject_idx = idx
            self._rebuild_draft()

    # ── Copy & close ─────────────────────────────────────────────────────────

    def copy_draft(self) -> bool:
        """Copy current draft to clipboard. Returns True if content was available."""
        draft = self._current_draft
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

    def action_copy_draft(self) -> None:
        if self.copy_draft():
            self.app.notify("Draft copied to clipboard", timeout=2)
        else:
            self.app.notify("Generate a draft first", severity="warning", timeout=2)

    def action_close_panel(self) -> None:
        self.remove()

    # ── Persistence ───────────────────────────────────────────────────────────

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
