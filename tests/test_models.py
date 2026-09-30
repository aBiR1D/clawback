"""Tests for all Pydantic models."""

from datetime import date, datetime

import pytest

from clawback.models import (
    BillAnalysis,
    BillCategory,
    BillItem,
    Frequency,
    MarketComparison,
    NegotiationEmail,
    NegotiationStrategy,
    Overcharge,
    SavingsReport,
    Severity,
    Tone,
)


# ---------------------------------------------------------------------------
# BillItem
# ---------------------------------------------------------------------------

class TestBillItem:
    def test_basic_creation(self):
        item = BillItem(description="Internet Service", amount=79.99)
        assert item.description == "Internet Service"
        assert item.amount == 79.99
        assert item.category == BillCategory.OTHER
        assert item.is_recurring is True
        assert item.frequency == Frequency.MONTHLY

    def test_full_creation(self):
        item = BillItem(
            description="Cable TV",
            amount=120.00,
            category=BillCategory.CABLE_TV,
            is_recurring=True,
            frequency=Frequency.MONTHLY,
        )
        assert item.category == BillCategory.CABLE_TV
        assert item.frequency == Frequency.MONTHLY

    def test_one_time_charge(self):
        item = BillItem(
            description="Installation Fee",
            amount=99.00,
            is_recurring=False,
            frequency=Frequency.ONE_TIME,
        )
        assert item.is_recurring is False
        assert item.frequency == Frequency.ONE_TIME

    def test_negative_amount_rejected(self):
        with pytest.raises(Exception):
            BillItem(description="Bad", amount=-10)

    def test_serialization_roundtrip(self):
        item = BillItem(description="Test", amount=50.0, category=BillCategory.SAAS)
        data = item.model_dump()
        restored = BillItem(**data)
        assert restored == item


# ---------------------------------------------------------------------------
# BillAnalysis
# ---------------------------------------------------------------------------

class TestBillAnalysis:
    def test_creation(self):
        analysis = BillAnalysis(
            provider="Comcast",
            total=189.99,
            items=[
                BillItem(description="Internet", amount=89.99, category=BillCategory.INTERNET),
                BillItem(description="Cable TV", amount=100.00, category=BillCategory.CABLE_TV),
            ],
            bill_type=BillCategory.TELECOM,
            billing_period="2024-01-01 to 2024-01-31",
        )
        assert analysis.provider == "Comcast"
        assert analysis.total == 189.99
        assert len(analysis.items) == 2
        assert analysis.currency == "USD"

    def test_defaults(self):
        analysis = BillAnalysis(provider="Test", total=0)
        assert analysis.items == []
        assert analysis.bill_type == BillCategory.OTHER
        assert analysis.billing_period is None
        assert isinstance(analysis.analyzed_at, datetime)

    def test_serialization(self):
        analysis = BillAnalysis(provider="X", total=10)
        data = analysis.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["provider"] == "X"


# ---------------------------------------------------------------------------
# MarketComparison
# ---------------------------------------------------------------------------

class TestMarketComparison:
    def test_creation(self):
        comp = MarketComparison(
            item="Internet 200Mbps",
            your_price=89.99,
            market_avg=65.00,
            market_low=49.99,
            savings_potential=24.99,
        )
        assert comp.savings_potential == 24.99
        assert comp.source == "AI market knowledge"

    def test_custom_source(self):
        comp = MarketComparison(
            item="TV",
            your_price=100,
            market_avg=80,
            market_low=60,
            savings_potential=20,
            source="BroadbandNow 2024",
        )
        assert comp.source == "BroadbandNow 2024"


# ---------------------------------------------------------------------------
# Overcharge
# ---------------------------------------------------------------------------

class TestOvercharge:
    def test_creation(self):
        o = Overcharge(
            item="Regional Sports Fee",
            amount_overpaid=12.99,
            severity=Severity.HIGH,
            explanation="This is a pass-through fee not required by regulation",
            evidence="FCC ruling 2023",
        )
        assert o.severity == Severity.HIGH
        assert o.amount_overpaid == 12.99

    def test_defaults(self):
        o = Overcharge(item="Fee", amount_overpaid=5.0, explanation="test")
        assert o.severity == Severity.MEDIUM
        assert o.evidence == ""


# ---------------------------------------------------------------------------
# NegotiationStrategy
# ---------------------------------------------------------------------------

class TestNegotiationStrategy:
    def test_creation(self):
        ns = NegotiationStrategy(
            approach="Competitor comparison",
            talking_points=["AT&T offers same plan for $60", "Loyal customer 3 years"],
            counter_offer=65.00,
            walk_away_price=75.00,
        )
        assert len(ns.talking_points) == 2
        assert ns.counter_offer == 65.00

    def test_empty_talking_points(self):
        ns = NegotiationStrategy(
            approach="Direct", talking_points=[], counter_offer=50, walk_away_price=70
        )
        assert ns.talking_points == []


# ---------------------------------------------------------------------------
# NegotiationEmail
# ---------------------------------------------------------------------------

class TestNegotiationEmail:
    def test_creation(self):
        email = NegotiationEmail(
            subject="Billing Concern — Account #12345",
            body="Dear Comcast Billing Team,\n\nI'd like to discuss…",
            tone=Tone.PROFESSIONAL,
            follow_up_date=date(2024, 2, 15),
        )
        assert email.tone == Tone.PROFESSIONAL
        assert email.follow_up_date == date(2024, 2, 15)

    def test_defaults(self):
        email = NegotiationEmail(subject="Test", body="Body")
        assert email.tone == Tone.PROFESSIONAL
        assert email.follow_up_date is None


# ---------------------------------------------------------------------------
# SavingsReport
# ---------------------------------------------------------------------------

class TestSavingsReport:
    def test_creation(self):
        overcharges = [
            Overcharge(item="Fee A", amount_overpaid=10, explanation="x"),
            Overcharge(item="Fee B", amount_overpaid=15, explanation="y"),
        ]
        report = SavingsReport(
            total_analyzed=200.0,
            total_overcharges=25.0,
            total_potential_savings=25.0,
            items=overcharges,
        )
        assert report.total_overcharges == 25.0
        assert report.savings_percentage == 12.5

    def test_zero_total(self):
        report = SavingsReport(
            total_analyzed=0, total_overcharges=0, total_potential_savings=0
        )
        assert report.savings_percentage == 0.0

    def test_report_date_auto(self):
        report = SavingsReport(
            total_analyzed=100, total_overcharges=10, total_potential_savings=10
        )
        assert isinstance(report.report_date, datetime)
