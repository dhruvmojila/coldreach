"""Outreach screen — track drafted, sent, and replied contacts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import DataTable, Label

from coldreach.tui.widgets.draft_panel import DraftPanel


class OutreachScreen(Widget):
    """Browse and manage outreach contacts — draft, sent, replied."""

    DEFAULT_CSS = """
    OutreachScreen { height: 100%; padding: 1 2; }
    #outreach-stats { color: #9aa0c0; height: 1; margin-bottom: 1; }
    #outreach-table { height: 1fr; }
    #outreach-hint { color: #6b7099; height: 1; margin-top: 1; }
    """

    BINDINGS = [
        Binding("d", "draft_selected", "Draft"),
        Binding("s", "mark_sent", "Mark sent"),
        Binding("R", "mark_replied", "Mark replied"),
        Binding("x", "remove_contact", "Remove"),
        Binding("y", "copy_draft", "Copy draft"),
        Binding("f", "open_in_find", "Find domain"),
        Binding("r", "refresh", "Refresh"),
    ]

    _STATUS_ICON = {
        "new": "○",
        "draft": "●",
        "sent": "→",
        "replied": "✓",
        "bounced": "✗",
    }
    _STATUS_COLOR = {
        "new": "#6b7099",
        "draft": "#5b8cff",
        "sent": "#f59e0b",
        "replied": "#34d399",
        "bounced": "#f87171",
    }

    def compose(self) -> ComposeResult:
        yield Label("", id="outreach-stats")
        yield DataTable(id="outreach-table", cursor_type="row")
        yield Label(
            "[dim]d: Draft  s: Sent  R: Replied  x: Remove  y: Copy  f: Find domain[/]",
            id="outreach-hint",
        )

    def on_mount(self) -> None:
        table = self.query_one("#outreach-table", DataTable)
        table.add_columns("Email", "Domain", "Status", "Subject", "Sent At")
        self._refresh_table()

    def _refresh_table(self) -> None:
        from coldreach.outreach.tracker import OutreachTracker

        tracker = OutreachTracker()
        contacts = tracker.list_contacts()
        stats = tracker.stats()

        table = self.query_one("#outreach-table", DataTable)
        table.clear()

        replied = stats["replied"]
        sent = stats["sent"]
        draft = stats["draft"]
        total = stats["total"]

        self.query_one("#outreach-stats", Label).update(
            f"[bold]{total}[/] contacts  ·  "
            f"[#34d399]{replied} replied[/]  ·  "
            f"[#f59e0b]{sent} sent[/]  ·  "
            f"[#5b8cff]{draft} draft[/]"
        )

        for c in contacts:
            icon = self._STATUS_ICON.get(c.status, "○")
            color = self._STATUS_COLOR.get(c.status, "#6b7099")
            status_cell = f"[{color}]{icon} {c.status}[/]"
            subj = (c.subject or "—")[:50]
            sent_at = c.sent_at.strftime("%b %d") if c.sent_at else "—"
            table.add_row(c.email, c.domain, status_cell, subj, sent_at, key=c.email)

        if not contacts:
            self.query_one("#outreach-stats", Label).update(
                "[dim]No contacts yet — press d on an email in the Find tab to start[/]"
            )

    def _selected_email(self) -> str | None:
        table = self.query_one("#outreach-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= table.row_count:
            return None
        return str(table.get_cell_at((row, 0)))

    def _selected_domain(self) -> str | None:
        table = self.query_one("#outreach-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= table.row_count:
            return None
        return str(table.get_cell_at((row, 1)))

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_draft_selected(self) -> None:
        email = self._selected_email()
        domain = self._selected_domain()
        if not email or not domain:
            self.app.notify("Select a contact first", severity="warning")
            return
        for panel in self.query(DraftPanel):
            panel.remove()
        self.mount(DraftPanel(email, domain))

    def action_mark_sent(self) -> None:
        email = self._selected_email()
        if not email:
            self.app.notify("Select a contact first", severity="warning")
            return
        from coldreach.outreach.tracker import OutreachTracker

        OutreachTracker().mark_sent(email)
        self.app.notify(f"Marked as sent: {email}", timeout=2)
        self._refresh_table()

    def action_mark_replied(self) -> None:
        email = self._selected_email()
        if not email:
            self.app.notify("Select a contact first", severity="warning")
            return
        from coldreach.outreach.tracker import OutreachTracker

        OutreachTracker().mark_replied(email)
        self.app.notify(f"Marked as replied: {email}", timeout=2)
        self._refresh_table()

    def action_remove_contact(self) -> None:
        email = self._selected_email()
        if not email:
            self.app.notify("Select a contact first", severity="warning")
            return
        # Two-step confirmation: first press arms, second press within 3s deletes
        if getattr(self, "_pending_delete", None) == email:
            from coldreach.outreach.tracker import OutreachTracker

            OutreachTracker().remove(email)
            self._pending_delete = None
            self.app.notify(f"Removed {email}", timeout=2)
            self._refresh_table()
        else:
            self._pending_delete = email
            self.app.notify(
                f"Press x again to delete {email}",
                severity="warning",
                timeout=3,
            )
            self.set_timer(3, self._clear_pending_delete)

    def _clear_pending_delete(self) -> None:
        self._pending_delete = None

    def action_copy_draft(self) -> None:
        panels = list(self.query(DraftPanel))
        if panels and panels[0].copy_draft():
            self.app.notify("Draft copied to clipboard", timeout=2)
            return
        # No open panel — copy from stored draft
        email = self._selected_email()
        if not email:
            self.app.notify("Select a contact first", severity="warning")
            return
        from coldreach.outreach.tracker import OutreachTracker

        contacts = OutreachTracker().list_contacts()
        contact = next((c for c in contacts if c.email == email.lower()), None)
        if not contact or not contact.subject or not contact.body:
            self.app.notify("No draft saved — press d to generate one", severity="warning")
            return
        draft = f"Subject: {contact.subject}\n\n{contact.body}"
        import subprocess

        for cmd in [
            ["xclip", "-selection", "clipboard"],
            ["pbcopy"],
            ["xsel", "--clipboard", "--input"],
        ]:
            try:
                subprocess.run(cmd, input=draft.encode(), check=True, capture_output=True)
                self.app.notify("Draft copied to clipboard", timeout=2)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        self.app.notify(f"Subject: {contact.subject}", title="Copy manually", timeout=5)

    def action_open_in_find(self) -> None:
        domain = self._selected_domain()
        if not domain:
            self.app.notify("Select a contact first", severity="warning")
            return
        self.app.switch_to_find(domain)

    def action_refresh(self) -> None:
        self._refresh_table()
