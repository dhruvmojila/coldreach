from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpModal(ModalScreen):
    """Keyboard shortcuts overlay — press ? to toggle."""

    BINDINGS = [Binding("escape,question_mark", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Static(
            """\
[bold #5b8cff]⚡ ColdReach — Keyboard Shortcuts[/]

[bold #9aa0c0]Navigation[/]          [bold #9aa0c0]Find[/]
  [bold]f[/]  Find tab              [bold]Enter[/]  Start scan
  [bold]v[/]  Verify tab            [bold]r[/]      Re-scan domain
  [bold]s[/]  Status tab            [bold]y[/]      Copy email / draft
  [bold]c[/]  Cache tab             [bold]d[/]      Draft email (Groq)
  [bold]o[/]  Outreach tab          [bold]e[/]      Export CSV
  [bold]q[/]  Quit                  [bold]↑↓[/]     Navigate results
  [bold]?[/]  Toggle this help      [bold]Enter[/]  Open in Verify

[bold #9aa0c0]Draft panel (d)[/]      [bold #9aa0c0]Verify[/]
  [bold]1/2/3[/]  Pick subject       [bold]Enter[/]  Run verify
  [bold]y[/]      Copy full draft    [bold]h[/]      Run Holehe
  [bold]Esc[/]    Close panel        [bold]f[/]      Find domain

[bold #9aa0c0]Outreach (o)[/]         [bold #9aa0c0]Cache[/]
  [bold]d[/]  Draft selected         [bold]f[/]  Open domain in Find
  [bold]s[/]  Mark sent              [bold]x[/]  Delete selected
  [bold]R[/]  Mark replied           [bold]X[/]  Clear all (confirm)
  [bold]x[/]  Remove contact
  [bold]y[/]  Copy draft

[bold #9aa0c0]Status[/]
  [bold]r[/]  Refresh services

[dim]Press [bold]Esc[/] or [bold]?[/] to close[/]""",
            id="help-content",
        )

    def on_mount(self) -> None:
        self.query_one("#help-content").styles.padding = (1, 3)
        self.query_one("#help-content").styles.border = ("round", "#2a2d3e")
        self.query_one("#help-content").styles.background = "#1a1d27"
        self.query_one("#help-content").styles.width = 64
        self.query_one("#help-content").styles.height = "auto"
