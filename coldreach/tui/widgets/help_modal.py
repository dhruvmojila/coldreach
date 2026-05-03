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
  [bold]s[/]  Status tab            [bold]y[/]      Copy selected email
  [bold]c[/]  Cache tab             [bold]d[/]      Draft email (Groq)
  [bold]q[/]  Quit                  [bold]e[/]      Export CSV
  [bold]?[/]  Toggle this help      [bold]↑↓[/]     Navigate results
                               [bold]Enter[/]  Open in Verify

[bold #9aa0c0]Verify[/]               [bold #9aa0c0]Cache[/]
  [bold]Enter[/]  Run verify         [bold]f[/]  Open domain in Find
  [bold]h[/]      Run Holehe         [bold]x[/]  Delete selected
  [bold]f[/]      Find domain        [bold]X[/]  Clear all (confirm)

[bold #9aa0c0]Status[/]
  [bold]r[/]  Refresh services

[dim]Press [bold]Esc[/] or [bold]?[/] to close[/]""",
            id="help-content",
        )

    def on_mount(self) -> None:
        self.query_one("#help-content").styles.padding = (1, 3)
        self.query_one("#help-content").styles.border = ("round", "#2a2d3e")
        self.query_one("#help-content").styles.background = "#1a1d27"
        self.query_one("#help-content").styles.width = 60
        self.query_one("#help-content").styles.height = "auto"
