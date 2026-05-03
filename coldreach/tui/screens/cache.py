"""Cache screen — browse and manage cached domains."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label


class CacheScreen(Widget):
    """Browse, navigate, and delete cached domain results."""

    DEFAULT_CSS = """
    CacheScreen { height: 100%; padding: 1 2; }
    #cache-stats { color: #9aa0c0; height: 1; margin-bottom: 1; }
    #cache-actions {
        height: 3;
        align: left middle;
        margin-bottom: 1;
    }
    #cache-table { height: 1fr; }
    #cache-hint { color: #6b7099; height: 1; margin-top: 1; }
    """

    BINDINGS = [
        Binding("f", "open_in_find", "Open in Find"),
        Binding("x", "delete_entry", "Delete"),
        Binding("X", "clear_all", "Clear all"),
        Binding("r", "refresh_cache", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("", id="cache-stats")
        with Horizontal(id="cache-actions"):
            yield Button("f: Open in Find", id="btn-find", variant="default")
            yield Button("x: Delete", id="btn-delete", variant="default")
            yield Button("X: Clear all", id="btn-clear", variant="error")
            yield Button("r: Refresh", id="btn-refresh", variant="default")
        yield DataTable(id="cache-table", cursor_type="row")
        yield Label(
            "[dim]↑↓ Navigate  ·  f Open in Find  ·  x Delete  ·  X Clear all[/]", id="cache-hint"
        )

    def on_mount(self) -> None:
        table = self.query_one("#cache-table", DataTable)
        table.add_columns("Domain", "Cached At", "Status")
        self._refresh()

    def _refresh(self) -> None:
        from coldreach.storage.cache import CacheStore

        store = CacheStore(db_path="~/.coldreach/cache.db")
        rows = store.list_domains()
        stats = store.stats()

        table = self.query_one("#cache-table", DataTable)
        table.clear()

        total_emails = stats.get("total", 0)
        self.query_one("#cache-stats", Label).update(
            f"[bold]{len(rows)}[/] domains cached  ·  "
            f"[bold #5b8cff]{stats.get('valid', 0)}[/] valid entries  ·  "
            f"[dim]~/.coldreach/cache.db[/]"
        )

        for domain, cached_at, expired in rows:
            when = cached_at.strftime("%Y-%m-%d %H:%M") if cached_at else "—"
            if expired:
                status = "[#f87171]✗ expired[/]"
            else:
                status = "[#34d399]● fresh[/]"
            table.add_row(domain, when, status, key=domain)

    # ── Button handlers ───────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-find")
    def _btn_find(self) -> None:
        self.action_open_in_find()

    @on(Button.Pressed, "#btn-delete")
    def _btn_delete(self) -> None:
        self.action_delete_entry()

    @on(Button.Pressed, "#btn-clear")
    def _btn_clear(self) -> None:
        self.action_clear_all()

    @on(Button.Pressed, "#btn-refresh")
    def _btn_refresh(self) -> None:
        self.action_refresh_cache()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_open_in_find(self) -> None:
        table = self.query_one("#cache-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= table.row_count:
            self.app.notify("No domain selected", severity="warning")
            return
        domain = str(table.get_cell_at((row, 0)))
        self.app.switch_to_find(domain)

    def action_delete_entry(self) -> None:
        table = self.query_one("#cache-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= table.row_count:
            self.app.notify("No domain selected", severity="warning")
            return
        domain = str(table.get_cell_at((row, 0)))
        from coldreach.storage.cache import CacheStore

        CacheStore(db_path="~/.coldreach/cache.db").clear(domain=domain)
        self.app.notify(f"Deleted cache for {domain}", timeout=2)
        self._refresh()

    def action_clear_all(self) -> None:
        from coldreach.storage.cache import CacheStore

        CacheStore(db_path="~/.coldreach/cache.db").clear()
        self.app.notify("Cache cleared", timeout=2)
        self._refresh()

    def action_refresh_cache(self) -> None:
        self._refresh()
