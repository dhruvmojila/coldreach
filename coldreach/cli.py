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
from rich.console import Console
from rich.table import Table

from coldreach import __version__
from coldreach.core.finder import FinderConfig, find_emails
from coldreach.core.models import DomainResult
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
    no_reacher: bool,
    use_holehe: bool,
    no_cache: bool,
    refresh: bool,
    quick: bool,
    use_full: bool,
    timeout: float,
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
      coldreach find --domain acme.com --full
      coldreach find --domain acme.com --name "John Smith"
      coldreach find --domain acme.com --no-github --json
      coldreach find --domain acme.com --min-confidence 40
    """
    if not domain and not company:
        err_console.print("[red]Error:[/red] Provide --domain or --company")
        raise click.UsageError("Provide at least --domain or --company")

    target_domain = domain or company or ""

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
        harvester_sources="all" if use_full else None,
        use_reacher=not no_reacher,
        use_holehe=use_holehe,
        use_cache=not no_cache,
        refresh_cache=refresh,
        min_confidence=min_confidence,
        request_timeout=timeout,
    )

    if not output_json:
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
            f"\n  [dim]Searching [bold]{target_domain}[/bold] "
            f"via {', '.join(active_sources)}…[/dim]{mode_tag}\n"
        )

    result = asyncio.run(find_emails(target_domain, person_name=name, config=cfg))

    if output_json:
        click.echo(json.dumps(_domain_result_to_dict(result), indent=2))
    else:
        _render_find(result)

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
