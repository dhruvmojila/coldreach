"""Status screen — service health dashboard."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Label, Static


class ServiceCard(Static):
    """A single service health card."""

    DEFAULT_CSS = """
    ServiceCard {
        background: #1a1d27;
        border: round #2a2d3e;
        width: 1fr;
        height: 7;
        padding: 1 1;
        margin: 0 1;
    }
    """

    def __init__(self, name: str, role: str, port: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._name = name
        self._role = role
        self._port = port
        self.update(self._render_unknown())

    def _render_unknown(self) -> str:
        return (
            f"[bold]{self._name}[/]\n"
            f"[#6b7099]⟳ checking…[/]\n"
            f"[dim]:{self._port}[/]\n"
            f"[#6b7099]{self._role}[/]"
        )

    def set_online(self, latency_ms: int | None) -> None:
        lat = f"{latency_ms}ms" if latency_ms is not None else ""
        self.update(
            f"[bold]{self._name}[/]\n"
            f"[#34d399]● ONLINE[/]  [dim]{lat}[/]\n"
            f"[dim]:{self._port}[/]\n"
            f"[#6b7099]{self._role}[/]"
        )
        self.styles.border = ("round", "#134d31")

    def set_offline(self, detail: str = "") -> None:
        self.update(
            f"[bold]{self._name}[/]\n"
            f"[#f87171]○ OFFLINE[/]\n"
            f"[dim]:{self._port}  {detail}[/]\n"
            f"[#6b7099]{self._role}[/]"
        )
        self.styles.border = ("round", "#4d1515")


class StatusScreen(Widget):
    """Service health + optional packages status."""

    DEFAULT_CSS = """
    StatusScreen { height: 100%; padding: 2 2; }
    #cards-row { height: 8; margin-bottom: 2; }
    #section-label-services, #section-label-packages { color: #9aa0c0; text-style: bold; margin-bottom: 1; }
    #packages-area { margin-bottom: 2; }
    .pkg-row { height: 1; }
    .pkg-icon { width: 3; }
    .pkg-name { width: 16; }
    .pkg-status { color: #6b7099; }
    #refresh-hint { color: #6b7099; margin-top: 1; }
    """

    BINDINGS = [Binding("r", "refresh_status", "Refresh")]

    _CARDS = [
        ("SearXNG", "Metasearch 40+ engines", "8088"),
        ("Reacher", "SMTP verifier (Rust)", "8083"),
        ("SpiderFoot", "OSINT 200+ modules", "5001"),
        ("theHarvester", "Multi-source harvester", "5050"),
    ]

    _PACKAGES = [
        ("holehe", "holehe", "pip install coldreach[full]"),
        ("crawl4ai", "crawl4ai", "pip install crawl4ai && crawl4ai-setup"),
        ("dspy-ai", "dspy", "pip install coldreach[full]"),
    ]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Label("[bold]Service Health[/]", id="section-label-services")
        with Horizontal(id="cards-row"):
            for name, role, port in self._CARDS:
                yield ServiceCard(name, role, port, id=f"card-{name.lower().replace(' ', '')}")

        yield Label("[bold]Optional Packages[/]", id="section-label-packages")
        with Vertical(id="packages-area"):
            for pkg_name, import_name, install_hint in self._PACKAGES:
                with Horizontal(classes="pkg-row"):
                    yield Label("○", classes="pkg-icon", id=f"pkg-icon-{pkg_name}")
                    yield Label(pkg_name, classes="pkg-name")
                    yield Label(install_hint, classes="pkg-status", id=f"pkg-status-{pkg_name}")

        yield Label("[dim]Press [bold]r[/bold] to refresh[/]", id="refresh-hint")

    def on_mount(self) -> None:
        self._do_refresh()
        self._timer = self.set_interval(30, self._do_refresh)

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()

    @work(thread=False, name="status-worker", exclusive=True)
    async def _do_refresh(self) -> None:
        from coldreach import diagnostics

        report = await diagnostics.run()

        name_map = {
            "SearXNG": "searxng",
            "Reacher": "reacher",
            "SpiderFoot": "spiderfoot",
            "theHarvester": "theharvester",
        }
        for svc in report.services:
            card_id = f"card-{name_map.get(svc.name, svc.name.lower())}"
            try:
                card = self.query_one(f"#{card_id}", ServiceCard)
                if svc.online:
                    card.set_online(svc.latency_ms)
                else:
                    card.set_offline(svc.detail[:20])
            except Exception:
                pass

        import importlib.util

        for pkg_name, import_name, hint in self._PACKAGES:
            installed = importlib.util.find_spec(import_name) is not None
            try:
                icon = self.query_one(f"#pkg-icon-{pkg_name}", Label)
                status = self.query_one(f"#pkg-status-{pkg_name}", Label)
                if installed:
                    icon.update("[#34d399]✓[/]")
                    try:
                        import importlib.metadata

                        ver = importlib.metadata.version(pkg_name)
                        status.update(f"[#34d399]{ver}[/]")
                    except Exception:
                        status.update("[#34d399]installed[/]")
                else:
                    icon.update("[#6b7099]○[/]")
                    status.update(f"[dim]{hint}[/]")
            except Exception:
                pass

    def action_refresh_status(self) -> None:
        self._do_refresh()
        self.app.notify("Refreshing service status…", timeout=2)
