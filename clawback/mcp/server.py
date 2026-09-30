"""MCP server exposing Clawback tools via FastMCP."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from clawback.analyzer import (
    calculate_savings,
    compare_to_market,
    extract_bill_items,
    find_overcharges,
)
from clawback.negotiator import draft_email, generate_strategy

mcp = FastMCP("clawback", instructions="AI-powered bill analyzer and negotiation tool.")


@mcp.tool()
def analyze_bill(bill_text: str) -> dict:
    """Parse and analyze a bill — extract line items, compare to market rates,
    and identify overcharges.

    Args:
        bill_text: The raw text of a bill or contract.

    Returns:
        A dictionary containing the bill analysis, market comparisons,
        overcharges, and a savings report.
    """
    analysis = extract_bill_items(bill_text)
    comparisons = compare_to_market(analysis)
    overcharges = find_overcharges(analysis, comparisons)
    savings = calculate_savings(overcharges, total=analysis.total)
    return {
        "analysis": analysis.model_dump(mode="json"),
        "comparisons": [c.model_dump(mode="json") for c in comparisons],
        "overcharges": [o.model_dump(mode="json") for o in overcharges],
        "savings": savings.model_dump(mode="json"),
    }


@mcp.tool()
def negotiate_bill(bill_text: str) -> dict:
    """Full analysis pipeline plus negotiation email generation.

    Args:
        bill_text: The raw text of a bill or contract.

    Returns:
        A dictionary with the analysis, savings, negotiation strategy,
        and a ready-to-send negotiation email.
    """
    analysis = extract_bill_items(bill_text)
    comparisons = compare_to_market(analysis)
    overcharges = find_overcharges(analysis, comparisons)
    savings = calculate_savings(overcharges, total=analysis.total)
    strategy = generate_strategy(analysis, overcharges)
    email = draft_email(strategy, analysis.provider)
    return {
        "analysis": analysis.model_dump(mode="json"),
        "savings": savings.model_dump(mode="json"),
        "strategy": strategy.model_dump(mode="json"),
        "email": email.model_dump(mode="json"),
    }


@mcp.tool()
def find_savings(bill_text: str) -> dict:
    """Quick savings estimate — parse a bill and return potential savings.

    Args:
        bill_text: The raw text of a bill or contract.

    Returns:
        A concise savings report dictionary.
    """
    analysis = extract_bill_items(bill_text)
    comparisons = compare_to_market(analysis)
    overcharges = find_overcharges(analysis, comparisons)
    savings = calculate_savings(overcharges, total=analysis.total)
    return savings.model_dump(mode="json")
