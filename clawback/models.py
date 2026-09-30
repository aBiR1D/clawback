"""Pydantic models for bill analysis, market comparison, and negotiation."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BillCategory(StrEnum):
    TELECOM = "telecom"
    INTERNET = "internet"
    CABLE_TV = "cable_tv"
    INSURANCE = "insurance"
    UTILITIES = "utilities"
    SAAS = "saas"
    SUBSCRIPTION = "subscription"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    OTHER = "other"


class Frequency(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Tone(StrEnum):
    PROFESSIONAL = "professional"
    FIRM = "firm"
    FRIENDLY = "friendly"
    ESCALATION = "escalation"


# ---------------------------------------------------------------------------
# Bill models
# ---------------------------------------------------------------------------

class BillItem(BaseModel):
    """A single line item on a bill."""

    description: str = Field(..., description="Human-readable description of the charge")
    amount: float = Field(..., ge=0, description="Dollar amount for this line item")
    category: BillCategory = Field(default=BillCategory.OTHER)
    is_recurring: bool = Field(default=True)
    frequency: Frequency = Field(default=Frequency.MONTHLY)


class BillAnalysis(BaseModel):
    """Structured representation of an entire bill."""

    provider: str = Field(..., description="Service provider name")
    total: float = Field(..., ge=0, description="Total bill amount")
    items: list[BillItem] = Field(default_factory=list)
    bill_type: BillCategory = Field(default=BillCategory.OTHER)
    billing_period: Optional[str] = Field(
        default=None, description="e.g. '2024-01-01 to 2024-01-31'"
    )
    currency: str = Field(default="USD")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Market comparison
# ---------------------------------------------------------------------------

class MarketComparison(BaseModel):
    """Compares a single bill item to known market rates."""

    item: str = Field(..., description="Description of the bill item")
    your_price: float = Field(..., ge=0)
    market_avg: float = Field(..., ge=0, description="Average market price")
    market_low: float = Field(..., ge=0, description="Lowest known market price")
    savings_potential: float = Field(..., ge=0, description="How much you could save")
    source: str = Field(
        default="AI market knowledge",
        description="Where the market data comes from",
    )


# ---------------------------------------------------------------------------
# Overcharge detection
# ---------------------------------------------------------------------------

class Overcharge(BaseModel):
    """A detected overcharge or hidden fee."""

    item: str
    amount_overpaid: float = Field(..., ge=0)
    severity: Severity = Field(default=Severity.MEDIUM)
    explanation: str = Field(..., description="Why this is an overcharge")
    evidence: str = Field(
        default="", description="Supporting evidence or market data"
    )


# ---------------------------------------------------------------------------
# Negotiation
# ---------------------------------------------------------------------------

class NegotiationStrategy(BaseModel):
    """High-level negotiation plan."""

    approach: str = Field(..., description="Recommended negotiation approach")
    talking_points: list[str] = Field(default_factory=list)
    counter_offer: float = Field(..., ge=0, description="Suggested counter-offer amount")
    walk_away_price: float = Field(
        ..., ge=0, description="Max price before switching providers"
    )


class NegotiationEmail(BaseModel):
    """A ready-to-send negotiation email."""

    subject: str
    body: str
    tone: Tone = Field(default=Tone.PROFESSIONAL)
    follow_up_date: Optional[date] = Field(
        default=None, description="Suggested follow-up date"
    )


# ---------------------------------------------------------------------------
# Savings report
# ---------------------------------------------------------------------------

class SavingsReport(BaseModel):
    """Summary of all identified savings opportunities."""

    total_analyzed: float = Field(..., ge=0, description="Total amount on the bill")
    total_overcharges: float = Field(..., ge=0)
    total_potential_savings: float = Field(..., ge=0)
    items: list[Overcharge] = Field(default_factory=list)
    report_date: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def savings_percentage(self) -> float:
        if self.total_analyzed == 0:
            return 0.0
        return round(self.total_overcharges / self.total_analyzed * 100, 1)
