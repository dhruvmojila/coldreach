"""
ColdReach TUI — full-screen interactive terminal app.

Launch:  coldreach          (no args)
Exit:    q  or  Ctrl+C

Tabs:    f=Find  v=Verify  s=Status  c=Cache
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from coldreach.tui.screens.cache import CacheScreen
from coldreach.tui.screens.find import FindScreen
from coldreach.tui.screens.status import StatusScreen
from coldreach.tui.screens.verify import VerifyScreen
from coldreach.tui.widgets.help_modal import HelpModal

_CSS_PATH = Path(__file__).parent / "coldreach.tcss"


class StatusBar(Footer):
    """Persistent bottom bar — shows domain, email count, service dots."""

    pass


class ColdReachApp(App[None]):
    """The main TUI application."""

    CSS_PATH = _CSS_PATH
    TITLE = "ColdReach"
    SUB_TITLE = "open-source email finder"

    BINDINGS = [
        Binding("f", "switch_tab('find')", "Find", show=True),
        Binding("v", "switch_tab('verify')", "Verify", show=True),
        Binding("s", "switch_tab('status')", "Status", show=True),
        Binding("c", "switch_tab('cache')", "Cache", show=True),
        Binding("q,ctrl+c", "quit", "Quit", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with TabbedContent(id="main-tabs", initial="find"):
            with TabPane("⚡ Find", id="find"):
                yield FindScreen(id="find-screen")
            with TabPane("✓ Verify", id="verify"):
                yield VerifyScreen(id="verify-screen")
            with TabPane("● Status", id="status"):
                yield StatusScreen(id="status-screen")
            with TabPane("⊟ Cache", id="cache"):
                yield CacheScreen(id="cache-screen")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#main-tabs", TabbedContent).focus()

    # ── Tab navigation ────────────────────────────────────────────────────────

    def action_switch_tab(self, tab: str) -> None:
        self.query_one("#main-tabs", TabbedContent).active = tab

    def switch_to_find(self, domain: str = "") -> None:
        """Jump to Find tab, optionally pre-filling and starting a scan."""
        self.action_switch_tab("find")
        if domain:
            screen = self.query_one("#find-screen", FindScreen)
            screen.prefill_domain(domain)

    # ── Help overlay ──────────────────────────────────────────────────────────

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())

    # ── Cross-screen messages ─────────────────────────────────────────────────

    def on_find_screen_domain_changed(self, event: FindScreen.DomainChanged) -> None:
        self.sub_title = f"scanning {event.domain}"

    def on_find_screen_scan_finished(self, event: FindScreen.ScanFinished) -> None:
        self.sub_title = f"{event.count} emails found"

    def on_verify_screen_verify_done(self, event: VerifyScreen.VerifyDone) -> None:
        self.sub_title = f"{event.email} — score {event.score}/100"

    # ── Quit ─────────────────────────────────────────────────────────────────

    def action_quit(self) -> None:
        self.exit()


def run() -> None:
    """Entry point called from CLI."""
    import logging
    from pathlib import Path

    # Redirect ALL logging to file — prevents third-party libs (whois, httpx, etc.)
    # from writing to stderr and corrupting the terminal during TUI rendering.
    log_dir = Path.home() / ".coldreach"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=str(log_dir / "tui.log"),
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        force=True,
    )
    # Also silence the root logger's stderr handler if one exists
    for h in logging.root.handlers[:]:
        if isinstance(h, logging.StreamHandler) and h.stream.name in ("<stderr>", "<stdout>"):
            logging.root.removeHandler(h)

    ColdReachApp().run()
