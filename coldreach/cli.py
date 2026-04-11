"""
ColdReach CLI — entry point for all terminal commands.

Commands
--------
    coldreach verify <email>   — run basic verification pipeline
    coldreach version          — print version and exit

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


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 100}
)
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
    "--json", "output_json",
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
# find command (stub — implemented in Phase 2)
# ---------------------------------------------------------------------------


@main.command()
@click.option("--domain", "-d", default=None, help="Domain to search (e.g. stripe.com).")
@click.option("--company", "-c", default=None, help="Company name to look up.")
@click.option("--name", "-n", default=None, help="Person name to search for.")
@click.pass_context
def find(
    ctx: click.Context,
    domain: str | None,
    company: str | None,
    name: str | None,
) -> None:
    """Find email addresses for a domain or company.

    \b
    Examples:
      coldreach find --domain stripe.com
      coldreach find --company "Stripe" --name "Patrick Collison"

    \b
    Note: This command is implemented in Phase 2.
    Start with: coldreach verify <email>
    """
    if not domain and not company:
        err_console.print("[red]Error:[/red] Provide --domain or --company")
        raise click.UsageError("Provide at least --domain or --company")

    console.print(
        "[yellow]⚠[/yellow]  [bold]find[/bold] is coming in Phase 2.\n"
        "    Track progress: https://github.com/yourusername/coldreach\n\n"
        "    For now, try:\n"
        "      [dim]coldreach verify john@stripe.com[/dim]"
    )


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
