"""Find screen — domain scan with live streaming results."""

from __future__ import annotations

import asyncio
from typing import Any

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, ProgressBar, Static

from coldreach.tui.widgets.draft_panel import DraftPanel

# ── Source pill tracker ───────────────────────────────────────────────────────

_ICONS = {"waiting": "○", "running": "⟳", "done_found": "✓", "done_empty": "○", "error": "✗"}
_COLORS = {
    "waiting": "dim",
    "running": "#5b8cff",
    "done_found": "#34d399",
    "done_empty": "#6b7099",
    "error": "#f87171",
}


class SourcePanel(Static):
    """Left panel showing per-source status pills."""

    DEFAULT_CSS = """
    SourcePanel {
        width: 28;
        height: 100%;
        background: #1a1d27;
        border-right: solid #2a2d3e;
        padding: 1 1;
    }
    """

    ALL_SOURCES = [
        "web_crawler",
        "whois",
        "github",
        "reddit",
        "search_engine",
        "intelligent_search",
        "theharvester",
        "spiderfoot",
    ]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._states: dict[str, str] = dict.fromkeys(self.ALL_SOURCES, "waiting")
        self._counts: dict[str, int] = {}

    def on_mount(self) -> None:
        self._refresh_pills()

    def reset(self) -> None:
        self._states = dict.fromkeys(self.ALL_SOURCES, "waiting")
        self._counts = {}
        self._refresh_pills()

    def set_running(self, source: str) -> None:
        self._states[source] = "running"
        self._refresh_pills()

    def set_done(self, source: str, found: int) -> None:
        self._states[source] = "done_found" if found > 0 else "done_empty"
        self._counts[source] = found
        self._refresh_pills()

    def set_error(self, source: str) -> None:
        self._states[source] = "error"
        self._refresh_pills()

    def _refresh_pills(self) -> None:
        """Rebuild the source pill text and push it to Static.update()."""
        lines = ["[bold #9aa0c0]Sources[/]\n"]
        for src in self.ALL_SOURCES:
            state = self._states.get(src, "waiting")
            icon = _ICONS[state]
            color = _COLORS[state]
            label = src.replace("_", " ")
            count = self._counts.get(src, 0)
            suffix = f" [#34d399]+{count}[/]" if state == "done_found" else ""
            lines.append(f"[{color}]{icon}[/] [{color}]{label}[/]{suffix}")
        self.update("\n".join(lines))


# ── Results table ─────────────────────────────────────────────────────────────


class ResultsTable(DataTable):
    """Right panel — emails appear row-by-row as discovered."""

    DEFAULT_CSS = """
    ResultsTable {
        height: 100%;
    }
    """

    _STATUS_STYLE = {
        "valid": "#34d399",
        "catch_all": "#f59e0b",
        "unknown": "#6b7099",
        "unverified": "#6b7099",
        "likely": "#5b8cff",
        "undeliverable": "#f87171",
        "invalid": "#f87171",
        "risky": "#f59e0b",
        "pattern": "#9aa0c0",
    }

    @staticmethod
    def _conf_to_status(confidence: int, source: str) -> str:
        """Map confidence + source to a human-readable status label."""
        if source in ("pattern", "role"):
            return "pattern"
        if confidence >= 70:
            return "likely"
        return "unverified"

    def on_mount(self) -> None:
        self.add_columns("Email", "Conf", "Status", "Source")
        self.cursor_type = "row"

    def clear_results(self) -> None:
        self.clear()

    def add_email(self, email: str, confidence: int, status: str, source: str) -> None:
        src_short = source.split("/")[-1]
        # Use confidence-based status when caller passes raw "unknown"
        display_status = (
            status if status != "unknown" else self._conf_to_status(confidence, src_short)
        )
        color = self._STATUS_STYLE.get(display_status, "#6b7099")
        dot = "●" if display_status in ("valid", "likely") else "○"
        self.add_row(
            email,
            f"{confidence}",
            f"[{color}]{dot} {display_status}[/]",
            src_short,
            key=email,
        )
        # Auto-scroll to bottom unless user has scrolled up
        if self.scroll_y >= self.virtual_size.height - self.size.height - 3:
            self.scroll_end(animate=False)


# ── Find screen ───────────────────────────────────────────────────────────────


class FindScreen(Widget):
    """The main email discovery screen."""

    DEFAULT_CSS = """
    FindScreen { height: 100%; }

    #find-top {
        height: 5;
        background: #13151f;
        border-bottom: solid #3a3f5e;
        padding: 0 2;
        align: left middle;
    }
    #domain-input {
        width: 36;
        margin-right: 1;
        background: #1a1d2e;
        border: tall #5b8cff;
        color: #e0e4f7;
        padding: 0 1;
    }
    #domain-input:focus {
        border: tall #7aa6ff;
        background: #1c2040;
    }

    /* Mode buttons — use global Button style; variant switches to primary when active */
    #btn-quick, #btn-standard, #btn-full {
        min-width: 11;
        margin: 0 1 0 0;
    }

    #scan-btn { min-width: 10; margin-right: 1; }
    #stop-btn { display: none; min-width: 10; }

    #find-body { height: 1fr; }
    #results-panel { width: 1fr; height: 100%; padding: 0 1; }

    #progress-row {
        height: 3;
        background: #13151f;
        border-top: solid #2a2d3e;
        padding: 0 2;
        align: left middle;
    }
    #progress-bar { width: 28; margin-right: 2; }
    #progress-label { color: #c9cde8; }
    """

    BINDINGS = [
        Binding("r", "rescan", "Re-scan"),
        Binding("y", "yank_email", "Copy email"),
        Binding("d", "draft_email", "Draft"),
        Binding("e", "export_csv", "Export"),
    ]

    _email_count: reactive[int] = reactive(0)
    _scanning: reactive[bool] = reactive(False)
    _domain: str = ""
    _emails: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="find-top"):
            yield Input(
                placeholder="Type a domain and press Enter  (e.g. stripe.com)",
                id="domain-input",
            )
            yield Button("Quick", id="btn-quick", variant="default")
            yield Button("Standard", id="btn-standard", variant="default")
            yield Button("Full", id="btn-full", variant="default")
            yield Button("▶ Scan", id="scan-btn", variant="primary")
            yield Button("■ Stop", id="stop-btn", variant="error")

        with Horizontal(id="find-body"):
            yield SourcePanel(id="source-panel")
            with Vertical(id="results-panel"):
                yield Label("[dim]Type a domain and press Enter or click Scan[/]", id="empty-hint")
                yield ResultsTable(id="results-table")

        with Horizontal(id="progress-row"):
            yield ProgressBar(id="progress-bar", show_eta=False, show_percentage=False)
            yield Label("", id="progress-label")

    def on_mount(self) -> None:
        self._mode = "standard"
        self._stop_event: asyncio.Event = asyncio.Event()
        self.query_one("#results-table", ResultsTable).display = False
        self._set_mode("standard")  # apply visual state to buttons
        self.query_one("#domain-input", Input).focus()

    # ── Mode buttons ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-quick")
    def _mode_quick(self) -> None:
        self._set_mode("quick")

    @on(Button.Pressed, "#btn-standard")
    def _mode_standard(self) -> None:
        self._set_mode("standard")

    @on(Button.Pressed, "#btn-full")
    def _mode_full(self) -> None:
        self._set_mode("full")

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        for m in ("quick", "standard", "full"):
            btn = self.query_one(f"#btn-{m}", Button)
            if m == mode:
                btn.variant = "primary"
                btn.add_class("mode-selected")
            else:
                btn.variant = "default"
                btn.remove_class("mode-selected")

    # ── Scan trigger ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#scan-btn")
    def _start_from_button(self) -> None:
        domain = self.query_one("#domain-input", Input).value.strip()
        if domain:
            self._start_scan(domain)

    @on(Input.Submitted, "#domain-input")
    def _start_from_enter(self, event: Input.Submitted) -> None:
        domain = event.value.strip()
        if domain:
            self._start_scan(domain)

    @on(Button.Pressed, "#stop-btn")
    def _stop_scan(self) -> None:
        self._stop_event.set()

    def _start_scan(self, domain: str) -> None:
        domain = domain.lower().removeprefix("www.")
        self._domain = domain
        self._emails = []
        self._email_count = 0
        self._stop_event.clear()
        self._scanning = True

        self.query_one("#scan-btn", Button).display = False
        self.query_one("#stop-btn", Button).display = True
        self.query_one("#empty-hint", Label).display = False
        self.query_one("#results-table", ResultsTable).display = True
        self.query_one("#results-table", ResultsTable).clear_results()
        self.query_one("#source-panel", SourcePanel).reset()
        self.query_one("#progress-bar", ProgressBar).update(progress=0, total=100)
        self.query_one("#progress-label", Label).update(f"Scanning [bold]{domain}[/]…")

        # Notify app to update status bar domain
        self.app.post_message(self.DomainChanged(domain))

        self._do_scan(domain)

    class DomainChanged(Message):
        def __init__(self, domain: str) -> None:
            super().__init__()
            self.domain = domain

    class ScanFinished(Message):
        def __init__(self, count: int) -> None:
            super().__init__()
            self.count = count

    @work(thread=False, name="scan-worker", exclusive=True)
    async def _do_scan(self, domain: str) -> None:
        """Run the full discovery pipeline, updating UI as each source completes."""
        from coldreach.api import _build_sources
        from coldreach.core.finder import _SLOW_SOURCE_NAMES, FinderConfig
        from coldreach.sources.spiderfoot import SpiderFootSource

        quick = self._mode == "quick"
        full = self._mode == "full"

        cfg = FinderConfig(
            use_harvester=not quick,
            use_spiderfoot=not quick,
            use_intelligent_search=not quick,
            use_firecrawl=full,
            use_crawl4ai=False,
            use_cache=True,
            min_confidence=0,
        )

        all_sources = _build_sources(cfg)
        fast = [s for s in all_sources if s.name not in _SLOW_SOURCE_NAMES]
        slow = [s for s in all_sources if s.name in _SLOW_SOURCE_NAMES]
        total = len(all_sources)
        done_count = 0
        seen: set[str] = set()

        source_panel = self.query_one("#source-panel", SourcePanel)
        results_table = self.query_one("#results-table", ResultsTable)

        async def _run_one(src: object) -> None:
            nonlocal done_count
            name = getattr(src, "name", "unknown")
            source_panel.set_running(name)
            found = 0
            try:
                if isinstance(src, SpiderFootSource):
                    async for result in src.fetch_stream(domain):
                        if self._stop_event.is_set():
                            break
                        email = result.email.lower()
                        if email not in seen:
                            seen.add(email)
                            found += 1
                            conf = result.confidence_hint + 30
                            self._emails.append(
                                {
                                    "email": result.email,
                                    "confidence": conf,
                                    "source": result.source.value,
                                }
                            )
                            results_table.add_email(
                                result.email, conf, "unknown", result.source.value
                            )
                            self._email_count = len(seen)
                else:
                    results, _ = await src.run(domain)
                    for result in results:
                        if self._stop_event.is_set():
                            break
                        email = result.email.lower()
                        if email not in seen:
                            seen.add(email)
                            found += 1
                            conf = result.confidence_hint + 30
                            self._emails.append(
                                {
                                    "email": result.email,
                                    "confidence": conf,
                                    "source": result.source.value,
                                }
                            )
                            results_table.add_email(
                                result.email, conf, "unknown", result.source.value
                            )
                            self._email_count = len(seen)

                source_panel.set_done(name, found)
            except Exception as exc:
                source_panel.set_error(name)
                self.app.log.warning(f"Source {name} error: {exc}")
            finally:
                done_count += 1
                pct = int(done_count / total * 100) if total else 100
                self.query_one("#progress-bar", ProgressBar).update(progress=pct, total=100)
                self.query_one("#progress-label", Label).update(
                    f"[#9aa0c0]{done_count}/{total} sources  "
                    f"[bold #5b8cff]{len(seen)}[/] emails found[/]"
                )

        # Always add role emails
        from coldreach.generate.patterns import generate_role_emails

        for rp in generate_role_emails(domain):
            if rp.email not in seen:
                seen.add(rp.email)
                results_table.add_email(rp.email, 35, "pattern", "pattern")
                self._emails.append(
                    {"email": rp.email, "confidence": 35, "source": "generated/pattern"}
                )
        self._email_count = len(seen)

        # Fast sources concurrently
        await asyncio.gather(*[_run_one(s) for s in fast])

        # Slow sources (unless stopped)
        if not self._stop_event.is_set():
            await asyncio.gather(*[_run_one(s) for s in slow])

        # Save to cache if scan completed fully (not stopped)
        if not self._stop_event.is_set() and self._emails:
            try:
                from coldreach.core.models import (
                    DomainResult,
                    EmailRecord,
                    EmailSource,
                    SourceRecord,
                    VerificationStatus,
                )
                from coldreach.storage.cache import CacheStore

                records = []
                for item in self._emails:
                    try:
                        src_enum = EmailSource(item.get("source", "manual"))
                    except ValueError:
                        src_enum = EmailSource.MANUAL
                    records.append(
                        EmailRecord(
                            email=item["email"],
                            confidence=item.get("confidence", 35),
                            status=VerificationStatus.UNKNOWN,
                            sources=[SourceRecord(source=src_enum)],
                        )
                    )
                CacheStore(db_path="~/.coldreach/cache.db").set(
                    domain, DomainResult(domain=domain, emails=records)
                )
            except Exception as exc:
                self.app.log.warning(f"Cache save failed: {exc}")

        # Done
        self._scanning = False
        self.query_one("#scan-btn", Button).display = True
        self.query_one("#stop-btn", Button).display = False
        final_msg = (
            f"[#34d399]✓  Done — {len(seen)} emails found for {domain}[/]"
            if not self._stop_event.is_set()
            else f"[#f59e0b]■  Stopped — {len(seen)} emails found[/]"
        )
        self.query_one("#progress-label", Label).update(final_msg)
        self.post_message(self.ScanFinished(len(seen)))
        self.app.post_message(self.ScanFinished(len(seen)))

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_rescan(self) -> None:
        if self._domain:
            self._start_scan(self._domain)

    def action_yank_email(self) -> None:
        table = self.query_one("#results-table", ResultsTable)
        row = table.cursor_row
        if row < 0:
            return
        email = str(table.get_cell_at((row, 0)))
        import subprocess

        for cmd in [
            ["xclip", "-selection", "clipboard"],
            ["pbcopy"],
            ["xsel", "--clipboard", "--input"],
        ]:
            try:
                subprocess.run(cmd, input=email.encode(), check=True, capture_output=True)
                self.app.notify(f"Copied: {email}", timeout=2)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        self.app.notify(f"{email}", title="Email (copy manually)", timeout=5)

    def action_draft_email(self) -> None:
        table = self.query_one("#results-table", ResultsTable)
        row = table.cursor_row
        if row < 0:
            self.app.notify("Select an email first", severity="warning")
            return
        email = str(table.get_cell_at((row, 0)))
        results_panel = self.query_one("#results-panel")
        # Remove any existing panel first
        for panel in self.query(DraftPanel):
            panel.remove()
        results_panel.mount(DraftPanel(email, self._domain))
        self.app.notify(f"Draft panel opened for {email}", timeout=2)

    def action_export_csv(self) -> None:
        if not self._emails:
            self.app.notify("No emails to export", severity="warning")
            return
        import csv
        from pathlib import Path

        out = Path(f"~/{self._domain}-emails.csv").expanduser()
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["email"])
            w.writeheader()
            w.writerows(self._emails)
        self.app.notify(f"Exported to {out}", timeout=3)

    def prefill_domain(self, domain: str) -> None:
        self.query_one("#domain-input", Input).value = domain
        self._start_scan(domain)
