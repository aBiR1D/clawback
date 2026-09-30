"""Core bill analysis engine.

Provides functions for extracting bill items, comparing to market rates,
detecting overcharges, and calculating potential savings.
"""

from __future__ import annotations

from clawback.ai import llm_json
from clawback.models import (
    BillAnalysis,
    BillItem,
    MarketComparison,
    Overcharge,
    SavingsReport,
    Severity,
)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = """\
You are an expert financial analyst specialising in consumer bills and contracts.
Given raw bill text, extract every line item with its amount, category, and recurrence.

Return JSON matching this schema:
{
  "provider": "<string>",
  "total": <float>,
  "bill_type": "<category>",
  "billing_period": "<string or null>",
  "items": [
    {
      "description": "<string>",
      "amount": <float>,
      "category": "<telecom|internet|cable_tv|insurance|utilities|saas|subscription|medical|financial|other>",
      "is_recurring": <bool>,
      "frequency": "<monthly|quarterly|annual|one_time>"
    }
  ]
}
"""

_COMPARE_SYSTEM = """\
You are a market-rate research analyst.  Given a bill item and its price,
estimate the average and lowest market rates for the same service in the US.
Consider current promotions and competitor pricing.

Return a JSON array of objects:
[
  {
    "item": "<description>",
    "your_price": <float>,
    "market_avg": <float>,
    "market_low": <float>,
    "savings_potential": <float>,
    "source": "<where data comes from>"
  }
]
"""

_OVERCHARGE_SYSTEM = """\
You are a consumer-protection auditor.  Given a bill analysis and market
comparisons, identify overcharges, hidden fees, and unfair line items.
Classify severity as low / medium / high / critical.

Return a JSON array:
[
  {
    "item": "<description>",
    "amount_overpaid": <float>,
    "severity": "<low|medium|high|critical>",
    "explanation": "<why this is an overcharge>",
    "evidence": "<supporting data>"
  }
]
"""


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def extract_bill_items(text: str) -> BillAnalysis:
    """Parse raw bill text into a structured ``BillAnalysis``."""
    data = llm_json(_EXTRACT_SYSTEM, f"Analyze this bill:\n\n{text}")
    items = [BillItem(**item) for item in data.get("items", [])]
    return BillAnalysis(
        provider=data.get("provider", "Unknown"),
        total=data.get("total", 0),
        items=items,
        bill_type=data.get("bill_type", "other"),
        billing_period=data.get("billing_period"),
    )


def compare_to_market(analysis: BillAnalysis) -> list[MarketComparison]:
    """Compare each bill item to prevailing market rates."""
    items_text = "\n".join(
        f"- {item.description}: ${item.amount:.2f} ({item.category})"
        for item in analysis.items
    )
    prompt = (
        f"Provider: {analysis.provider}\n"
        f"Bill type: {analysis.bill_type}\n\n"
        f"Line items:\n{items_text}"
    )
    data = llm_json(_COMPARE_SYSTEM, prompt)
    if isinstance(data, dict):
        data = data.get("comparisons", [data])
    return [MarketComparison(**c) for c in data]


def find_overcharges(
    analysis: BillAnalysis,
    comparisons: list[MarketComparison],
) -> list[Overcharge]:
    """Identify overcharges by combining bill analysis and market data."""
    comp_text = "\n".join(
        f"- {c.item}: yours=${c.your_price:.2f}, avg=${c.market_avg:.2f}, "
        f"low=${c.market_low:.2f}"
        for c in comparisons
    )
    items_text = "\n".join(
        f"- {i.description}: ${i.amount:.2f}" for i in analysis.items
    )
    prompt = (
        f"Provider: {analysis.provider}\n\n"
        f"Bill items:\n{items_text}\n\n"
        f"Market comparisons:\n{comp_text}"
    )
    data = llm_json(_OVERCHARGE_SYSTEM, prompt)
    if isinstance(data, dict):
        data = data.get("overcharges", [data])
    return [Overcharge(**o) for o in data]


def calculate_savings(overcharges: list[Overcharge], total: float = 0) -> SavingsReport:
    """Roll up overcharges into a savings report."""
    total_overpaid = sum(o.amount_overpaid for o in overcharges)
    return SavingsReport(
        total_analyzed=total,
        total_overcharges=total_overpaid,
        total_potential_savings=total_overpaid,
        items=overcharges,
    )
