"""Inline Groq draft panel — used in the Find screen and Outreach screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Static

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
        max-height: 32;
        padding: 1 2;
        margin: 1 0;
    }
    DraftPanel #context-bar {
        color: #9aa0c0;
        height: 1;
        background: #13151f;
        padding: 0 1;
        margin-bottom: 1;
    }
    /* Row 1: name | intent */
    DraftPanel #inputs-row    { height: 3; align: left middle; margin-bottom: 1; }
    DraftPanel #sender-name   { width: 26; margin-right: 1; }
    DraftPanel #sender-intent { width: 1fr; }
    /* Row 2: type toggle buttons | model toggle */
    DraftPanel #type-model-row { height: 3; align: left middle; margin-bottom: 1; }
    DraftPanel .type-btn  { min-width: 10; margin: 0 1 0 0; }
    DraftPanel .type-btn.type-selected { background: #1a2850; color: #7aa6ff; border: tall #5b8cff; text-style: bold; }
    DraftPanel #btn-model-sep { width: 2; color: #2a2d3e; }
    DraftPanel #btn-fast      { min-width: 18; margin-right: 1; }
    DraftPanel #btn-quality   { min-width: 24; }
    /* Row 3: generate | regen */
    DraftPanel #action-row    { height: 3; align: left middle; margin-bottom: 1; }
    DraftPanel #btn-generate  { min-width: 18; margin-right: 1; }
    DraftPanel #btn-regen     { min-width: 14; }
    DraftPanel #draft-status  { color: #5b8cff; height: 1; margin-bottom: 1; }
    /* Results: subjects + body label + body text */
    DraftPanel #subjects-box {
        background: #13151f;
        border: tall #2a2d3e;
        padding: 1 1;
        height: 7;
        overflow-y: auto;
        margin-bottom: 1;
    }
    DraftPanel #body-label { color: #5b8cff; text-style: bold; height: 1; }
    DraftPanel #draft-body-box {
        background: #13151f;
        border: tall #2a2d3e;
        padding: 1 1;
        height: 6;
        overflow-y: auto;
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
        self._email_type: str = "auto"
        self._model: str = _FAST_MODEL

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal
        from textual.widgets import Label

        yield Static("Fetching company info…", id="context-bar")
        # Row 1: name | intent
        with Horizontal(id="inputs-row"):
            yield Input(placeholder="Your name", id="sender-name", value=self._recall_name())
            yield Input(placeholder="What you want — one sentence", id="sender-intent")
        # Row 2: type toggle buttons (no Select overlay issues) + model toggle
        with Horizontal(id="type-model-row"):
            yield Button("Auto", id="type-auto", classes="type-btn type-selected")
            yield Button("Partner", id="type-partner", classes="type-btn")
            yield Button("Job", id="type-job", classes="type-btn")
            yield Button("Sales", id="type-sales", classes="type-btn")
            yield Button("Intro", id="type-intro", classes="type-btn")
            yield Static("  ·  ", id="btn-model-sep")
            yield Button("Fast (llama-3.1-8b)", id="btn-fast", variant="primary")
            yield Button("Quality (llama-3.3-70b)", id="btn-quality", variant="default")
        # Row 3: generate | regenerate
        with Horizontal(id="action-row"):
            yield Button("▶  Generate draft", id="btn-generate", variant="primary")
            yield Button("↺  Regenerate", id="btn-regen", variant="default")
        yield Static("", id="draft-status")
        yield Static("", id="subjects-box")
        yield Label("Body", id="body-label")
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
            # height: 1 — show company summary on one line, skip long description
            line = f"[bold #9aa0c0]{summary}[/]"
            if desc:
                line += f"  [dim]{desc[:60]}…[/]" if len(desc) > 60 else f"  [dim]{desc}[/]"
            self.query_one("#context-bar", Static).update(line)
            self._ctx = ctx
        except Exception:
            if not self.is_attached:
                return
            self.query_one("#context-bar", Static).update(
                f"[#9aa0c0]{self.domain}[/]  [dim #f59e0b]· could not fetch company info[/]"
            )
            self._ctx = None

    # ── Model toggle ──────────────────────────────────────────────────────────

    _TYPE_MAP = {
        "type-auto": "auto",
        "type-partner": "partnership",
        "type-job": "job_application",
        "type-sales": "sales",
        "type-intro": "introduction",
    }

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid in ("btn-generate", "btn-regen"):
            self._generate()
        elif bid == "btn-fast":
            self._set_model(_FAST_MODEL)
        elif bid == "btn-quality":
            self._set_model(_QUALITY_MODEL)
        elif bid in self._TYPE_MAP:
            self._set_email_type(bid)

    def _set_email_type(self, btn_id: str) -> None:
        self._email_type = self._TYPE_MAP[btn_id]
        for tid in self._TYPE_MAP:
            btn = self.query_one(f"#{tid}", Button)
            if tid == btn_id:
                btn.add_class("type-selected")
            else:
                btn.remove_class("type-selected")

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
        etype = self._email_type
        self.query_one("#draft-status", Static).update(
            "[#5b8cff]Reading company site… writing draft…[/]"
        )
        self.query_one("#subjects-box", Static).update("")
        self.query_one("#draft-body-box", Static).update("")
        self._subjects = []
        self._current_draft = ""
        # thread=True: runs completely off the event loop so UI stays responsive
        # during the Groq API call (which can take 2-8 seconds).
        # Use partial to avoid collision between sender `name` var and
        # run_worker's own `name=` keyword argument.
        import functools

        self.run_worker(
            functools.partial(self._run_draft, name, intent, etype),
            name="draft-worker",
            exclusive=True,
            thread=True,
        )

    def _run_draft(self, name: str, intent: str, etype: str) -> None:
        """Blocking draft generation — runs in a thread worker off the event loop."""
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._run_draft_async(name, intent, etype))
        finally:
            loop.close()

    async def _run_draft_async(self, name: str, intent: str, etype: str) -> None:
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
            # UI updates must go through call_from_thread when in a thread worker
            self.app.call_from_thread(self._rebuild_draft)
            self.app.call_from_thread(
                self._save_to_outreach, draft.subjects[0], draft.body, str(draft.email_type)
            )
            self.app.call_from_thread(
                self.query_one("#draft-status", Static).update,
                "[#34d399]Done — press [bold]1/2/3[/] to pick subject, [bold]y[/] to copy[/]",
            )
        except ValueError as exc:
            msg = str(exc)
            if "Groq API key" in msg:
                self.app.call_from_thread(self._render_template_mode, etype)
            else:
                from rich.markup import escape

                self.app.call_from_thread(
                    self.query_one("#draft-status", Static).update,
                    f"[#f87171]{escape(msg)}[/]",
                )
        except Exception as exc:
            from rich.markup import escape

            self.app.call_from_thread(
                self.query_one("#draft-status", Static).update,
                f"[#f87171]Draft failed: {escape(str(exc))}[/]",
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
        # Body label is a separate widget — body box gets plain escaped text only
        self.query_one("#draft-body-box", Static).update(body_safe)
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

    def copy_draft(self) -> str:
        """Copy current draft to clipboard (safe to call from any thread).

        Returns 'clipboard' on success, 'file' if saved to fallback file, 'empty' if no draft.
        """
        draft = self._current_draft
        if not draft:
            return "empty"
        import subprocess

        data = draft.encode()
        for cmd in [
            ["xclip", "-selection", "clipboard"],
            ["wl-copy"],
            ["pbcopy"],
            ["xsel", "--clipboard", "--input"],
        ]:
            try:
                subprocess.run(
                    cmd,
                    input=data,
                    check=True,
                    capture_output=True,
                    timeout=3,
                )
                return "clipboard"
            except (
                FileNotFoundError,
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                OSError,
            ):
                continue
        # Clipboard unavailable (headless/SSH) — write to file as fallback
        try:
            from pathlib import Path

            out = Path("~/.coldreach/last-draft.txt").expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(draft)
            return "file"
        except Exception:
            return "failed"

    def action_copy_draft(self) -> None:
        """Run clipboard in a thread so xclip can never freeze the event loop."""
        if not self._current_draft:
            self.app.notify("Generate a draft first", severity="warning", timeout=2)
            return
        self.app.notify("Copying…", timeout=1)
        import functools

        self.run_worker(
            functools.partial(self._do_copy_in_thread),
            name="copy-draft",
            thread=True,
        )

    def _do_copy_in_thread(self) -> None:
        result = self.copy_draft()
        if not self.is_attached:
            return
        if result == "clipboard":
            msg, sev = "Draft copied to clipboard", "information"
        elif result == "file":
            msg, sev = "Saved to ~/.coldreach/last-draft.txt", "warning"
        else:
            msg, sev = "Copy failed — no clipboard tool found", "error"
        self.app.call_from_thread(self.app.notify, msg, severity=sev, timeout=3)

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
