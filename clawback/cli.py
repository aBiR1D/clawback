"""Clawback CLI — powered by Typer and Rich."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from clawback.analyzer import (
    calculate_savings,
    compare_to_market,
    extract_bill_items,
    find_overcharges,
)
from clawback.models import (
    BillAnalysis,
    MarketComparison,
    NegotiationEmail,
    Overcharge,
    SavingsReport,
)
from clawback.negotiator import draft_email, generate_strategy

app = typer.Typer(
    name="clawback",
    help="AI-powered bill analyzer — find every dollar you're overpaying.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = r"""
  ██████╗██╗      █████╗ ██╗    ██╗██████╗  █████╗  ██████╗██╗  ██╗
 ██╔════╝██║     ██╔══██╗██║    ██║██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
 ██║     ██║     ███████║██║ █╗ ██║██████╔╝███████║██║     █████╔╝
 ██║     ██║     ██╔══██║██║███╗██║██╔══██╗██╔══██║██║     ██╔═██╗
 ╚██████╗███████╗██║  ██║╚███╔███╔╝██████╔╝██║  ██║╚██████╗██║  ██╗
  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
"""


def _print_banner() -> None:
    console.print(Text(BANNER, style="bold green"))
    console.print(
        "[dim]Find every dollar you're overpaying.[/dim]\n",
        justify="center",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_input(text_or_file: str) -> str:
    """Return bill text from a file path or raw string."""
    path = Path(text_or_file)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return text_or_file


def _render_bill(analysis: BillAnalysis) -> None:
    table = Table(title=f"📄  Bill from {analysis.provider}", show_lines=True)
    table.add_column("Item", style="cyan", min_width=30)
    table.add_column("Amount", justify="right", style="bold")
    table.add_column("Category", style="dim")
    table.add_column("Recurring", justify="center")
    for item in analysis.items:
        table.add_row(
            item.description,
            f"${item.amount:.2f}",
            item.category.value,
            "✓" if item.is_recurring else "—",
        )
    table.add_row("[bold]TOTAL[/bold]", f"[bold]${analysis.total:.2f}[/bold]", "", "")
    console.print(table)


def _render_comparisons(comparisons: list[MarketComparison]) -> None:
    table = Table(title="📊  Market Comparison", show_lines=True)
    table.add_column("Item", style="cyan", min_width=25)
    table.add_column("Your Price", justify="right")
    table.add_column("Mkt Avg", justify="right")
    table.add_column("Mkt Low", justify="right")
    table.add_column("Savings", justify="right", style="bold green")
    for c in comparisons:
        table.add_row(
            c.item,
            f"${c.your_price:.2f}",
            f"${c.market_avg:.2f}",
            f"${c.market_low:.2f}",
            f"${c.savings_potential:.2f}",
        )
    console.print(table)


def _render_overcharges(overcharges: list[Overcharge]) -> None:
    if not overcharges:
        console.print("[green]✅ No overcharges detected![/green]")
        return
    table = Table(title="🚨  Overcharges Detected", show_lines=True)
    table.add_column("Item", style="cyan")
    table.add_column("Overpaid", justify="right", style="bold red")
    table.add_column("Severity", justify="center")
    table.add_column("Explanation")
    severity_colors = {"low": "yellow", "medium": "dark_orange", "high": "red", "critical": "bold red"}
    for o in overcharges:
        color = severity_colors.get(o.severity, "white")
        table.add_row(
            o.item,
            f"${o.amount_overpaid:.2f}",
            f"[{color}]{o.severity.upper()}[/{color}]",
            o.explanation,
        )
    console.print(table)


def _render_savings(report: SavingsReport) -> None:
    content = (
        f"[bold]Total Analyzed:[/bold]       ${report.total_analyzed:.2f}\n"
        f"[bold red]Total Overcharges:[/bold red]   ${report.total_overcharges:.2f}\n"
        f"[bold green]Potential Savings:[/bold green]   ${report.total_potential_savings:.2f}\n"
        f"[bold green]Savings %:[/bold green]           {report.savings_percentage}%"
    )
    console.print(Panel(content, title="💰  Savings Summary", border_style="green"))


def _render_email(email: NegotiationEmail) -> None:
    body = f"[bold]Subject:[/bold] {email.subject}\n\n{email.body}"
    if email.follow_up_date:
        body += f"\n\n[dim]Follow up by: {email.follow_up_date}[/dim]"
    console.print(Panel(body, title="✉️  Negotiation Email", border_style="blue"))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    text_or_file: str = typer.Argument(..., help="Bill text or path to a bill file"),
) -> None:
    """Analyze a bill — extract line items and identify savings."""
    _print_banner()
    bill_text = _read_input(text_or_file)

    with console.status("[bold green]Extracting bill items…"):
        analysis = extract_bill_items(bill_text)
    _render_bill(analysis)

    with console.status("[bold green]Comparing to market rates…"):
        comparisons = compare_to_market(analysis)
    _render_comparisons(comparisons)

    with console.status("[bold green]Detecting overcharges…"):
        overcharges = find_overcharges(analysis, comparisons)
    _render_overcharges(overcharges)

    report = calculate_savings(overcharges, total=analysis.total)
    _render_savings(report)


@app.command()
def negotiate(
    text_or_file: str = typer.Argument(..., help="Bill text or path to a bill file"),
) -> None:
    """Full pipeline — analyze a bill and generate a negotiation email."""
    _print_banner()
    bill_text = _read_input(text_or_file)

    with console.status("[bold green]Extracting bill items…"):
        analysis = extract_bill_items(bill_text)
    _render_bill(analysis)

    with console.status("[bold green]Comparing to market rates…"):
        comparisons = compare_to_market(analysis)
    _render_comparisons(comparisons)

    with console.status("[bold green]Detecting overcharges…"):
        overcharges = find_overcharges(analysis, comparisons)
    _render_overcharges(overcharges)

    report = calculate_savings(overcharges, total=analysis.total)
    _render_savings(report)

    if not overcharges:
        console.print("[green]Nothing to negotiate — your bill looks fair![/green]")
        return

    with console.status("[bold green]Generating negotiation strategy…"):
        strategy = generate_strategy(analysis, overcharges)

    console.print(Panel(
        "\n".join(f"• {tp}" for tp in strategy.talking_points),
        title="🎯  Negotiation Strategy",
        subtitle=f"Counter-offer: ${strategy.counter_offer:.2f}",
        border_style="yellow",
    ))

    with console.status("[bold green]Drafting negotiation email…"):
        email = draft_email(strategy, analysis.provider)
    _render_email(email)


@app.command()
def compare(
    text_or_file: str = typer.Argument(..., help="Bill text or path to a bill file"),
) -> None:
    """Compare bill line items to market rates."""
    _print_banner()
    bill_text = _read_input(text_or_file)

    with console.status("[bold green]Extracting bill items…"):
        analysis = extract_bill_items(bill_text)
    _render_bill(analysis)

    with console.status("[bold green]Comparing to market rates…"):
        comparisons = compare_to_market(analysis)
    _render_comparisons(comparisons)


# ---------------------------------------------------------------------------
# Module entry point (python -m clawback)
# ---------------------------------------------------------------------------

def _main() -> None:
    app()
