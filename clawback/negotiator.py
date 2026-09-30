"""Negotiation engine — generates strategies, emails, and phone scripts."""

from __future__ import annotations

from datetime import date, timedelta

from clawback.ai import llm_call, llm_json
from clawback.models import (
    BillAnalysis,
    NegotiationEmail,
    NegotiationStrategy,
    Overcharge,
    Tone,
)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_STRATEGY_SYSTEM = """\
You are an expert consumer negotiation coach.
Given a bill analysis and identified overcharges, devise a negotiation strategy.

Return JSON:
{
  "approach": "<brief strategy description>",
  "talking_points": ["<point1>", "<point2>", ...],
  "counter_offer": <float>,
  "walk_away_price": <float>
}
"""

_EMAIL_SYSTEM = """\
You are a professional copywriter specialising in consumer bill negotiation.
Write a concise, persuasive email that the customer can send to the provider's
billing department.  Be polite but firm.  Reference specific overcharges.

Return JSON:
{
  "subject": "<email subject>",
  "body": "<full email body>",
  "tone": "<professional|firm|friendly|escalation>",
  "follow_up_date": "<YYYY-MM-DD>"
}
"""

_PHONE_SYSTEM = """\
You are a negotiation coach.  Write a phone script the customer can follow
when calling the provider.  Include:
1. Opening line
2. How to state the issue
3. Key talking points (reference specific overcharges)
4. Responses to common objections
5. Closing / next-steps

Return the script as plain text, not JSON.
"""

_CANCEL_SYSTEM = """\
You are a consumer rights advisor.  Draft a cancellation notice email
that is polite, professional, and references the specific reason for leaving.
Include any legally useful language about cancellation rights.

Return JSON:
{
  "subject": "<email subject>",
  "body": "<full email body>",
  "tone": "firm",
  "follow_up_date": "<YYYY-MM-DD>"
}
"""


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def generate_strategy(
    analysis: BillAnalysis,
    overcharges: list[Overcharge],
) -> NegotiationStrategy:
    """Build a negotiation strategy from bill analysis and overcharges."""
    overcharge_text = "\n".join(
        f"- {o.item}: ${o.amount_overpaid:.2f} overpaid ({o.severity}) — {o.explanation}"
        for o in overcharges
    )
    items_text = "\n".join(
        f"- {i.description}: ${i.amount:.2f}" for i in analysis.items
    )
    prompt = (
        f"Provider: {analysis.provider}\n"
        f"Total bill: ${analysis.total:.2f}\n\n"
        f"Line items:\n{items_text}\n\n"
        f"Overcharges:\n{overcharge_text}"
    )
    data = llm_json(_STRATEGY_SYSTEM, prompt)
    return NegotiationStrategy(**data)


def draft_email(
    strategy: NegotiationStrategy,
    provider: str,
) -> NegotiationEmail:
    """Draft a negotiation email using the strategy."""
    prompt = (
        f"Provider: {provider}\n"
        f"Strategy: {strategy.approach}\n"
        f"Talking points:\n"
        + "\n".join(f"- {tp}" for tp in strategy.talking_points)
        + f"\nCounter-offer: ${strategy.counter_offer:.2f}\n"
        f"Walk-away price: ${strategy.walk_away_price:.2f}"
    )
    data = llm_json(_EMAIL_SYSTEM, prompt)
    if "follow_up_date" not in data or not data["follow_up_date"]:
        data["follow_up_date"] = (date.today() + timedelta(days=7)).isoformat()
    return NegotiationEmail(**data)


def draft_phone_script(strategy: NegotiationStrategy) -> str:
    """Generate a phone negotiation script."""
    prompt = (
        f"Strategy: {strategy.approach}\n"
        f"Talking points:\n"
        + "\n".join(f"- {tp}" for tp in strategy.talking_points)
        + f"\nCounter-offer: ${strategy.counter_offer:.2f}\n"
        f"Walk-away price: ${strategy.walk_away_price:.2f}"
    )
    return llm_call(_PHONE_SYSTEM, prompt)


def draft_cancellation(provider: str, reason: str) -> NegotiationEmail:
    """Draft a cancellation email for a provider."""
    prompt = f"Provider: {provider}\nReason for cancellation: {reason}"
    data = llm_json(_CANCEL_SYSTEM, prompt)
    if "follow_up_date" not in data or not data["follow_up_date"]:
        data["follow_up_date"] = (date.today() + timedelta(days=14)).isoformat()
    return NegotiationEmail(**data)
