"""
ColdReach CLI — entry point for all terminal commands.

Commands
--------
    coldreach verify <email>       — run basic verification pipeline
    coldreach find --domain ...    — discover emails for a domain
    coldreach cache list           — show all cached domains
    coldreach cache clear          — clear cache (all or one domain)
    coldreach cache stats          — show cache size and TTL info
    coldreach version              — print version and exit

Rich is used for all styled output. Pass ``--no-color`` to disable.
Pass ``--json`` to any command that supports it for machine-readable output.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import click
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from coldreach import __version__
from coldreach.core.finder import FinderConfig, find_emails
from coldreach.core.models import DomainResult
from coldreach.export import export_results
from coldreach.resolve import resolve_domain
from coldreach.storage.cache import CacheStore
from coldreach.verify._types import CheckStatus
from coldreach.verify.pipeline import PipelineResult, run_basic_pipeline

# One stdout console, one stderr console for errors.
console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 100})
@click.version_option(__version__, "-V", "--version", prog_name="coldreach")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """ColdReach — open-source email finder and lead discovery tool.

    \b
    Free alternative to Hunter.io and Apollo.io.
    All data stays on your machine. Zero paid API keys required.

    \b
    Quick start:
      coldreach verify john@acme.com
      coldreach find --domain acme.com
      coldreach find --company "Acme Corp" --name "John Smith"

    \b
    Start backend services (Docker required for full features):
      docker compose up -d
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _configure_logging(verbose)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

_BANNER_LINES = [
    " ██████╗ ██████╗ ██╗     ██████╗ ██████╗ ███████╗ █████╗  ██████╗██╗  ██╗",
    "██╔════╝██╔═══██╗██║     ██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝██║  ██║",
    "██║     ██║   ██║██║     ██║  ██║██████╔╝█████╗  ███████║██║     ███████║",
    "██║     ██║   ██║██║     ██║  ██║██╔══██╗██╔══╝  ██╔══██║██║     ██╔══██║",
    "╚██████╗╚██████╔╝███████╗██████╔╝██║  ██║███████╗██║  ██║╚██████╗██║  ██║",
    " ╚═════╝ ╚═════╝ ╚══════╝╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝",
]

# Vertical gradient: blue → indigo → violet → magenta
_BANNER_COLORS = [
    "#5b8cff",
    "#7b78ff",
    "#9b64ff",
    "#bb50ff",
    "#d83cff",
    "#e040fb",
]


def _banner() -> Panel:
    art = Text()
    for line, color in zip(_BANNER_LINES, _BANNER_COLORS, strict=True):
        art.append(line + "\n", style=f"bold {color}")
    subtitle = Text(
        f"v{__version__}  ·  Open-source email discovery  ·  Free alternative to Hunter.io",
        style="dim",
        justify="center",
    )
    content = Text.assemble(art, "\n", subtitle)
    return Panel(
        Align.center(content),
        border_style="#5b8cff",
        padding=(0, 2),
    )


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check which services are running and which packages are installed.

    \b
    Pings all Docker services (SearXNG, Reacher, SpiderFoot, theHarvester,
    Firecrawl) and checks optional Python packages (holehe, crawl4ai,
    firecrawl-py).

    \b
    Start all services:
      docker compose up -d
    """
    from coldreach import diagnostics

    console.print(_banner())
    console.print()

    checking = Spinner("dots2", text="[bold cyan]Pinging services…[/bold cyan]")

    with Live(Align.center(checking), refresh_per_second=12, transient=True):
        report = asyncio.run(diagnostics.run())

    # ── Core services table ───────────────────────────────────────────────────
    core = [s for s in report.services if not s.separate_stack]
    svc_table = Table(
        show_header=True,
        header_style="bold dim",
        border_style="dim",
        box=None,
        padding=(0, 2),
        expand=False,
    )
    svc_table.add_column("Service", style="bold", min_width=16)
    svc_table.add_column("Status", min_width=12)
    svc_table.add_column("Latency", justify="right", min_width=8)
    svc_table.add_column("Port", style="dim", min_width=6)
    svc_table.add_column("Role", style="dim")

    for svc in core:
        port = svc.url.split(":")[-1].split("/")[0]
        if svc.online:
            status_cell = Text("● ONLINE", style="bold green")
            latency_cell = Text(f"{svc.latency_ms}ms", style="green")
        else:
            status_cell = Text("○ OFFLINE", style="bold red")
            latency_cell = Text(f"({svc.detail})", style="dim red")
        svc_table.add_row(svc.name, status_cell, latency_cell, port, svc.role)

    online_count = sum(1 for s in core if s.online)
    total_core = len(core)
    svc_color = "green" if online_count == total_core else ("yellow" if online_count > 0 else "red")

    console.print(
        Panel(
            svc_table,
            title=(
                f"[bold]Docker Services[/bold]  "
                f"[{svc_color}]{online_count}/{total_core} online[/{svc_color}]"
            ),
            title_align="left",
            border_style="dim",
            padding=(0, 1),
        )
    )
    console.print()

    # ── Packages table ────────────────────────────────────────────────────────
    pkg_table = Table(
        show_header=True,
        header_style="bold dim",
        border_style="dim",
        box=None,
        padding=(0, 2),
        expand=False,
    )
    pkg_table.add_column("Package", style="bold", min_width=14)
    pkg_table.add_column("Status", min_width=14)
    pkg_table.add_column("Version", style="dim", min_width=10)
    pkg_table.add_column("Install", style="dim")

    for pkg in report.packages:
        if pkg.installed:
            status_cell = Text("● installed", style="bold green")
            ver_cell = Text(pkg.version or "—", style="dim")
        else:
            status_cell = Text("○ not installed", style="dim")
            ver_cell = Text("—", style="dim")
        pkg_table.add_row(pkg.name, status_cell, ver_cell, pkg.install_hint)

    pkg_count = report.packages_installed
    total_pkg = len(report.packages)

    console.print(
        Panel(
            pkg_table,
            title=(
                f"[bold]Optional Packages[/bold]  "
                f"[dim]{pkg_count}/{total_pkg} installed — "
                f"unlock additional discovery sources[/dim]"
            ),
            title_align="left",
            border_style="dim",
            padding=(0, 1),
        )
    )

    # Separate-stack services note
    extras = [s for s in report.services if s.separate_stack]
    if extras:
        extra_parts = []
        for s in extras:
            dot = "[green]●[/green]" if s.online else "[dim]○[/dim]"
            extra_parts.append(f"{dot} [dim]{s.name}[/dim]")
        console.print()
        console.print(f"  [dim]Optional add-ons (separate setup):[/dim]  {'  '.join(extra_parts)}")
        console.print("  [dim]└─ See https://github.com/mendableai/firecrawl for Firecrawl[/dim]")

    console.print()

    # ── Summary + hints ───────────────────────────────────────────────────────
    core_svc_map = {
        "SearXNG": "searxng",
        "Reacher": "reacher",
        "SpiderFoot": "spiderfoot",
        "theHarvester": "theharvester",
    }
    offline_core = [s for s in core if not s.online]
    if not offline_core:
        console.print(
            "  [bold green]✓[/bold green]  All services online — ready for full discovery.\n"
        )
        console.print("    [dim]coldreach find --domain stripe.com --quick[/dim]\n")
    else:
        console.print(
            f"  [yellow]{len(offline_core)} service(s) offline.[/yellow]  Start everything with:\n"
        )
        console.print("    [bold]docker compose up -d[/bold]\n")
        console.print("  Or restart just the offline ones:\n")
        for svc in offline_core:
            cmd = core_svc_map.get(svc.name, svc.name.lower())
            console.print(f"    [bold]docker compose up -d {cmd}[/bold]")
        console.print()
        console.print(
            "  [dim]Tip: run [bold]make setup[/bold]"
            " to build and start everything in one step.[/dim]\n"
        )


# ---------------------------------------------------------------------------
# verify command
# ---------------------------------------------------------------------------


@main.command()
@click.argument("email")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Print raw JSON result instead of styled output.",
)
@click.option(
    "--dns-timeout",
    type=float,
    default=5.0,
    show_default=True,
    metavar="SECONDS",
    help="DNS resolution timeout.",
)
@click.pass_context
def verify(ctx: click.Context, email: str, output_json: bool, dns_timeout: float) -> None:
    """Verify a single email address.

    Runs: syntax → disposable domain → DNS/MX checks.

    \b
    Exit codes:
      0 — all checks passed
      1 — one or more checks failed

    \b
    Examples:
      coldreach verify john@stripe.com
      coldreach verify test@mailinator.com
      coldreach verify ceo@unknown-domain.xyz --json
    """
    result = asyncio.run(run_basic_pipeline(email, dns_timeout=dns_timeout))

    if output_json:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _render_verify(result)

    sys.exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# find command
# ---------------------------------------------------------------------------


@main.command()
@click.option("--domain", "-d", default=None, help="Domain to search (e.g. stripe.com).")
@click.option("--company", "-c", default=None, help="Company name (used as domain hint).")
@click.option("--name", "-n", default=None, help="Person full name (narrows search).")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Print raw JSON result instead of styled output.",
)
@click.option(
    "--min-confidence",
    type=int,
    default=0,
    show_default=True,
    help="Hide results below this confidence score.",
)
@click.option("--no-web", is_flag=True, default=False, help="Skip website crawler.")
@click.option("--no-whois", is_flag=True, default=False, help="Skip WHOIS lookup.")
@click.option("--no-github", is_flag=True, default=False, help="Skip GitHub mining.")
@click.option("--no-reddit", is_flag=True, default=False, help="Skip Reddit search.")
@click.option("--no-search", is_flag=True, default=False, help="Skip SearXNG/DDG search.")
@click.option("--no-harvester", is_flag=True, default=False, help="Skip theHarvester.")
@click.option("--no-spiderfoot", is_flag=True, default=False, help="Skip SpiderFoot.")
@click.option(
    "--firecrawl",
    "use_firecrawl",
    is_flag=True,
    default=False,
    help="Enable Firecrawl JS scraping (requires firecrawl-py + self-hosted server).",
)
@click.option(
    "--crawl4ai",
    "use_crawl4ai",
    is_flag=True,
    default=False,
    help="Enable crawl4ai Playwright scraping (requires: pip install crawl4ai && crawl4ai-setup).",
)
@click.option(
    "--no-reacher",
    is_flag=True,
    default=False,
    help="Skip SMTP verification via Reacher.",
)
@click.option(
    "--holehe",
    "use_holehe",
    is_flag=True,
    default=False,
    help="Enable platform-presence check via holehe (slow, ~30s per email).",
)
@click.option("--no-cache", is_flag=True, default=False, help="Skip cache read and write.")
@click.option(
    "--refresh",
    is_flag=True,
    default=False,
    help="Ignore cached result but overwrite cache with fresh data.",
)
@click.option(
    "--quick",
    is_flag=True,
    default=False,
    help="Quick mode: skip slow OSINT tools (theHarvester + SpiderFoot). ~10s vs ~5min.",
)
@click.option(
    "--full",
    "use_full",
    is_flag=True,
    default=False,
    help="Full mode: use all sources including theHarvester with every available source.",
)
@click.option(
    "--timeout",
    type=float,
    default=10.0,
    show_default=True,
    metavar="SECONDS",
    help="Per-source request timeout.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    metavar="FILE",
    help="Export results to FILE (.csv or .json). Inferred from extension.",
)
@click.pass_context
def find(
    ctx: click.Context,
    domain: str | None,
    company: str | None,
    name: str | None,
    output_json: bool,
    min_confidence: int,
    no_web: bool,
    no_whois: bool,
    no_github: bool,
    no_reddit: bool,
    no_search: bool,
    no_harvester: bool,
    no_spiderfoot: bool,
    use_firecrawl: bool,
    use_crawl4ai: bool,
    no_reacher: bool,
    use_holehe: bool,
    no_cache: bool,
    refresh: bool,
    quick: bool,
    use_full: bool,
    timeout: float,
    output: str | None,
) -> None:
    """Find email addresses for a domain or company.

    \b
    Speed presets:
      --quick   ~10s  — web, WHOIS, GitHub, Reddit, SearXNG only
      (default) ~2min — above + theHarvester (free sources)
      --full    ~5min — all sources + theHarvester with every available source

    \b
    Examples:
      coldreach find --domain stripe.com --quick
      coldreach find --company "Stripe" --name "Patrick Collison"
      coldreach find --domain acme.com --output leads.csv
      coldreach find --domain acme.com --output leads.json
      coldreach find --domain acme.com --name "John Smith"
      coldreach find --domain acme.com --no-github --json
      coldreach find --domain acme.com --min-confidence 40
    """
    if not domain and not company:
        err_console.print("[red]Error:[/red] Provide --domain or --company")
        raise click.UsageError("Provide at least --domain or --company")

    # Validate --output extension early so we fail fast before the slow find
    if output:
        from pathlib import Path

        ext = Path(output).suffix.lower()
        if ext not in (".csv", ".json"):
            err_console.print(f"[red]Error:[/red] --output must end in .csv or .json (got {ext!r})")
            raise click.UsageError("--output must end in .csv or .json")

    # Resolve company name → domain when --domain is not given
    target_domain = domain or ""
    if not domain and company:
        if not output_json:
            console.print(f"\n  [dim]Resolving domain for '{company}'…[/dim]")
        resolved = asyncio.run(resolve_domain(company))
        if not resolved:
            err_console.print(
                f"[red]Error:[/red] Could not resolve a domain for '{company}'. "
                "Try passing --domain directly."
            )
            raise click.Abort()
        target_domain = resolved
        if not output_json:
            console.print(f"  [dim]→ {resolved}[/dim]\n")

    # --quick skips slow CLI-based OSINT tools
    if quick:
        no_harvester = True
        no_spiderfoot = True

    cfg = FinderConfig(
        use_web_crawler=not no_web,
        use_whois=not no_whois,
        use_github=not no_github,
        use_reddit=not no_reddit,
        use_search_engine=not no_search,
        use_harvester=not no_harvester,
        use_spiderfoot=not no_spiderfoot,
        use_firecrawl=use_firecrawl,
        use_crawl4ai=use_crawl4ai,
        harvester_sources="all" if use_full else None,
        use_reacher=not no_reacher,
        use_holehe=use_holehe,
        use_cache=not no_cache,
        refresh_cache=refresh,
        min_confidence=min_confidence,
        request_timeout=timeout,
    )

    if not output_json:
        from coldreach import diagnostics

        # ── Service status bar (core services only) ───────────────────────────
        # quick_service_check only pings core services (not separate-stack ones
        # like Firecrawl which is never in the default compose stack).
        svc_status = asyncio.run(diagnostics.quick_service_check(timeout=3.0))

        # Source name → Docker service name (core services only)
        _SOURCE_SERVICE: dict[str, str] = {
            "search": "SearXNG",
            "harvester": "theHarvester",
            "spiderfoot": "SpiderFoot",
            "reacher": "Reacher",
        }

        status_parts: list[str] = []
        for svc_name, svc_online in svc_status.items():
            dot = "[green]●[/green]" if svc_online else "[red]○[/red]"
            status_parts.append(f"{dot} [dim]{svc_name}[/dim]")

        console.print()
        console.print(
            Panel(
                "  ".join(status_parts),
                title="[dim]Services[/dim]",
                title_align="left",
                border_style="dim",
                padding=(0, 2),
            )
        )

        # Warn only about core services the user requested that are offline
        _source_enabled: dict[str, bool] = {
            "search": not no_search,
            "harvester": not no_harvester,
            "spiderfoot": not no_spiderfoot,
            "reacher": not no_reacher,
        }
        warnings: list[str] = []
        for src, svc in _SOURCE_SERVICE.items():
            if _source_enabled.get(src, False) and not svc_status.get(svc, False):
                compose_name = svc.lower().replace("theharvester", "theharvester")
                warnings.append(
                    f"  [yellow]⚠[/yellow]  [bold]{svc}[/bold] is offline"
                    f" — run [bold]docker compose up -d {compose_name}[/bold]"
                )
        for w in warnings:
            console.print(w)
        if warnings:
            console.print()

        # ── Source + mode line ────────────────────────────────────────────────
        active_sources = [
            s
            for s, enabled in [
                ("web", not no_web),
                ("whois", not no_whois),
                ("github", not no_github),
                ("reddit", not no_reddit),
                ("search", not no_search),
                ("harvester", not no_harvester),
                ("spiderfoot", not no_spiderfoot),
                ("firecrawl", use_firecrawl),
                ("crawl4ai", use_crawl4ai),
                ("reacher", not no_reacher),
                ("holehe", use_holehe),
            ]
            if enabled
        ]
        if quick:
            mode_tag = " [yellow](quick)[/yellow]"
        elif use_full:
            mode_tag = " [cyan](full)[/cyan]"
        else:
            mode_tag = ""
        console.print(
            f"  [dim]Searching [bold]{target_domain}[/bold] "
            f"via {', '.join(active_sources)}…[/dim]{mode_tag}\n"
        )

    result = asyncio.run(find_emails(target_domain, person_name=name, config=cfg))

    if output_json:
        click.echo(json.dumps(_domain_result_to_dict(result), indent=2))
    else:
        _render_find(result)

    if output:
        try:
            written = export_results(result, output)
            if not output_json:
                console.print(
                    f"  [dim]Exported {len(result.emails)} email(s) → "
                    f"[bold]{written}[/bold][/dim]\n"
                )
        except (ValueError, OSError) as exc:
            err_console.print(f"[red]Export failed:[/red] {exc}")
            sys.exit(2)

    sys.exit(0 if result.emails else 1)


# ---------------------------------------------------------------------------
# Rich rendering helpers
# ---------------------------------------------------------------------------


def _render_verify(result: PipelineResult) -> None:
    """Print a styled verification report to stdout."""
    passed = result.passed
    icon = "✓" if passed else "✗"
    colour = "green" if passed else "red"

    console.print()
    console.print(
        f"  [{colour}]{icon}[/{colour}]  "
        f"[bold]{result.normalized_email}[/bold]  "
        f"[dim]confidence {result.score}/100[/dim]"
    )
    console.print()

    table = Table(
        show_header=True,
        header_style="bold dim",
        box=None,
        padding=(0, 2),
        show_edge=False,
    )
    table.add_column("Check", style="dim", width=14, no_wrap=True)
    table.add_column("Status", width=8, no_wrap=True)
    table.add_column("Detail")

    _status_label = {
        CheckStatus.PASS: "[green]pass[/green]",
        CheckStatus.FAIL: "[red]fail[/red]",
        CheckStatus.WARN: "[yellow]warn[/yellow]",
        CheckStatus.SKIP: "[dim]skip[/dim]",
    }

    for check_name, check_result in result.checks.items():
        table.add_row(
            check_name,
            _status_label.get(check_result.status, check_result.status.value),
            check_result.reason,
        )

    console.print(table)

    if result.mx_records:
        mx_display = ", ".join(result.mx_records[:3])
        if len(result.mx_records) > 3:
            mx_display += f" (+{len(result.mx_records) - 3} more)"
        console.print(f"\n  [dim]MX:[/dim] {mx_display}")

    if not passed and result.failure_reason:
        console.print(f"\n  [red dim]Reason:[/red dim] {result.failure_reason}")

    console.print()


def _render_find(result: DomainResult) -> None:
    """Print a styled email discovery report to stdout."""
    if not result.emails:
        console.print(f"  [yellow]No emails found for [bold]{result.domain}[/bold][/yellow]\n")
        return

    console.print(
        f"  Found [bold green]{len(result.emails)}[/bold green] email(s) "
        f"for [bold]{result.domain}[/bold]\n"
    )

    table = Table(
        show_header=True,
        header_style="bold dim",
        box=None,
        padding=(0, 2),
        show_edge=False,
    )
    table.add_column("Email", min_width=30)
    table.add_column("Score", width=6, justify="right")
    table.add_column("Source(s)", min_width=22)
    table.add_column("Status", width=12)

    _status_colour = {
        "valid": "green",
        "invalid": "red",
        "risky": "yellow",
        "unknown": "dim",
        "catch_all": "dim",
        "disposable": "red",
        "undeliverable": "red",
    }

    for record in result.emails:
        colour = _status_colour.get(record.status.value, "dim")
        score_colour = (
            "green" if record.confidence >= 60 else ("yellow" if record.confidence >= 30 else "red")
        )
        table.add_row(
            f"[bold]{record.email}[/bold]",
            f"[{score_colour}]{record.confidence}[/{score_colour}]",
            ", ".join(record.source_names[:2]),
            f"[{colour}]{record.status.value}[/{colour}]",
        )

    console.print(table)
    console.print()


def _domain_result_to_dict(result: DomainResult) -> dict[str, object]:
    """Serialise DomainResult to a plain dict for JSON output."""
    return {
        "domain": result.domain,
        "company_name": result.company_name,
        "total": len(result.emails),
        "emails": [r.to_dict() for r in result.emails],
    }


# ---------------------------------------------------------------------------
# cache subcommand group
# ---------------------------------------------------------------------------

_CACHE_DB = "~/.coldreach/cache.db"


@main.group()
def cache() -> None:
    """Manage the local result cache.

    \b
    Examples:
      coldreach cache list
      coldreach cache stats
      coldreach cache clear
      coldreach cache clear --domain stripe.com
    """


@cache.command(name="list")
def cache_list() -> None:
    """List all cached domains."""
    store = CacheStore(db_path=_CACHE_DB)
    domains = store.list_domains()
    if not domains:
        console.print("  [dim]Cache is empty.[/dim]")
        return

    table = Table(
        show_header=True, header_style="bold dim", box=None, padding=(0, 2), show_edge=False
    )
    table.add_column("Domain", min_width=30)
    table.add_column("Cached at (UTC)", width=22)
    table.add_column("Status", width=10)

    for domain, cached_at, expired in domains:
        status = "[red]expired[/red]" if expired else "[green]valid[/green]"
        table.add_row(domain, cached_at.strftime("%Y-%m-%d %H:%M"), status)

    console.print()
    console.print(table)
    console.print()


@cache.command(name="clear")
@click.option("--domain", "-d", default=None, help="Clear only this domain.")
def cache_clear(domain: str | None) -> None:
    """Clear cached results (all or a specific domain)."""
    store = CacheStore(db_path=_CACHE_DB)
    deleted = store.clear(domain=domain)
    if domain:
        console.print(f"  Cleared cache for [bold]{domain}[/bold] ({deleted} record(s))")
    else:
        console.print(f"  Cleared entire cache ({deleted} record(s))")


@cache.command(name="stats")
def cache_stats() -> None:
    """Show cache statistics."""
    store = CacheStore(db_path=_CACHE_DB)
    s = store.stats()
    console.print()
    console.print(f"  [bold]Cache:[/bold] {_CACHE_DB}")
    console.print(f"  Total entries : [bold]{s['total']}[/bold]")
    console.print(f"  Valid (fresh)  : [green]{s['valid']}[/green]")
    console.print(f"  Expired        : [dim]{s['expired']}[/dim]")
    console.print()
