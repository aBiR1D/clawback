"""Tests for the analyzer module — uses mock LLM responses."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from clawback.analyzer import (
    calculate_savings,
    compare_to_market,
    extract_bill_items,
    find_overcharges,
)
from clawback.models import (
    BillAnalysis,
    BillCategory,
    BillItem,
    MarketComparison,
    Overcharge,
    Severity,
)

# ---------------------------------------------------------------------------
# Sample bills
# ---------------------------------------------------------------------------

SAMPLE_COMCAST_BILL = """\
Comcast / Xfinity
Account: 8491-2837-1029
Statement Period: Jan 1 – Jan 31, 2024

Internet – Performance Pro 200 Mbps        $89.99
Cable TV – Digital Preferred                $74.99
Regional Sports Fee                         $12.99
Broadcast TV Fee                            $21.00
HD Technology Fee                           $10.00
Equipment Rental – DVR                      $14.99
Equipment Rental – Modem                    $14.00
Taxes & Government Fees                      $8.50
                                           -------
Total Due                                  $246.46
"""

SAMPLE_SAAS_INVOICE = """\
Acme SaaS Corp
Invoice #INV-2024-0042
Date: February 1, 2024

Enterprise Plan (annual, billed monthly)    $499.00
Additional Users (12 × $25)                 $300.00
Premium Support Add-on                      $149.00
Data Storage Overage (50 GB × $2)           $100.00
API Rate Limit Increase                      $75.00
                                           -------
Total                                     $1,123.00
"""


# ---------------------------------------------------------------------------
# Mock LLM responses
# ---------------------------------------------------------------------------

MOCK_EXTRACT_COMCAST: dict[str, Any] = {
    "provider": "Comcast / Xfinity",
    "total": 246.46,
    "bill_type": "telecom",
    "billing_period": "2024-01-01 to 2024-01-31",
    "items": [
        {"description": "Internet – Performance Pro 200 Mbps", "amount": 89.99, "category": "internet", "is_recurring": True, "frequency": "monthly"},
        {"description": "Cable TV – Digital Preferred", "amount": 74.99, "category": "cable_tv", "is_recurring": True, "frequency": "monthly"},
        {"description": "Regional Sports Fee", "amount": 12.99, "category": "cable_tv", "is_recurring": True, "frequency": "monthly"},
        {"description": "Broadcast TV Fee", "amount": 21.00, "category": "cable_tv", "is_recurring": True, "frequency": "monthly"},
        {"description": "HD Technology Fee", "amount": 10.00, "category": "cable_tv", "is_recurring": True, "frequency": "monthly"},
        {"description": "Equipment Rental – DVR", "amount": 14.99, "category": "telecom", "is_recurring": True, "frequency": "monthly"},
        {"description": "Equipment Rental – Modem", "amount": 14.00, "category": "telecom", "is_recurring": True, "frequency": "monthly"},
        {"description": "Taxes & Government Fees", "amount": 8.50, "category": "other", "is_recurring": True, "frequency": "monthly"},
    ],
}

MOCK_COMPARE_COMCAST: list[dict[str, Any]] = [
    {"item": "Internet – Performance Pro 200 Mbps", "your_price": 89.99, "market_avg": 60.00, "market_low": 45.00, "savings_potential": 29.99, "source": "BroadbandNow 2024"},
    {"item": "Cable TV – Digital Preferred", "your_price": 74.99, "market_avg": 65.00, "market_low": 50.00, "savings_potential": 9.99, "source": "TV market analysis"},
    {"item": "Regional Sports Fee", "your_price": 12.99, "market_avg": 8.00, "market_low": 0.00, "savings_potential": 12.99, "source": "FCC data"},
    {"item": "Broadcast TV Fee", "your_price": 21.00, "market_avg": 14.00, "market_low": 8.99, "savings_potential": 7.00, "source": "FCC data"},
    {"item": "HD Technology Fee", "your_price": 10.00, "market_avg": 0.00, "market_low": 0.00, "savings_potential": 10.00, "source": "Industry standard"},
    {"item": "Equipment Rental – DVR", "your_price": 14.99, "market_avg": 10.00, "market_low": 0.00, "savings_potential": 14.99, "source": "Equipment analysis"},
    {"item": "Equipment Rental – Modem", "your_price": 14.00, "market_avg": 0.00, "market_low": 0.00, "savings_potential": 14.00, "source": "Buy your own modem"},
]

MOCK_OVERCHARGES_COMCAST: list[dict[str, Any]] = [
    {"item": "Regional Sports Fee", "amount_overpaid": 12.99, "severity": "high", "explanation": "Hidden fee that can be removed by switching plans", "evidence": "FCC consumer advisory 2023"},
    {"item": "HD Technology Fee", "amount_overpaid": 10.00, "severity": "critical", "explanation": "HD is standard; no competitor charges this", "evidence": "Industry comparison"},
    {"item": "Equipment Rental – Modem", "amount_overpaid": 14.00, "severity": "high", "explanation": "Buying a modem pays for itself in 6 months", "evidence": "Modem cost ~$80 one-time"},
    {"item": "Internet – Performance Pro 200 Mbps", "amount_overpaid": 29.99, "severity": "medium", "explanation": "Priced $30 above market average for 200 Mbps", "evidence": "BroadbandNow 2024"},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractBillItems:
    @patch("clawback.analyzer.llm_json", return_value=MOCK_EXTRACT_COMCAST)
    def test_comcast_extraction(self, mock_llm):
        analysis = extract_bill_items(SAMPLE_COMCAST_BILL)
        assert analysis.provider == "Comcast / Xfinity"
        assert analysis.total == 246.46
        assert len(analysis.items) == 8
        assert analysis.bill_type == BillCategory.TELECOM
        assert analysis.billing_period is not None
        mock_llm.assert_called_once()

    @patch("clawback.analyzer.llm_json", return_value={
        "provider": "Acme SaaS Corp",
        "total": 1123.00,
        "bill_type": "saas",
        "billing_period": "2024-02-01 to 2024-02-29",
        "items": [
            {"description": "Enterprise Plan", "amount": 499.00, "category": "saas", "is_recurring": True, "frequency": "monthly"},
            {"description": "Additional Users (12)", "amount": 300.00, "category": "saas", "is_recurring": True, "frequency": "monthly"},
            {"description": "Premium Support", "amount": 149.00, "category": "saas", "is_recurring": True, "frequency": "monthly"},
            {"description": "Data Storage Overage", "amount": 100.00, "category": "saas", "is_recurring": False, "frequency": "one_time"},
            {"description": "API Rate Limit Increase", "amount": 75.00, "category": "saas", "is_recurring": True, "frequency": "monthly"},
        ],
    })
    def test_saas_extraction(self, mock_llm):
        analysis = extract_bill_items(SAMPLE_SAAS_INVOICE)
        assert analysis.provider == "Acme SaaS Corp"
        assert analysis.total == 1123.00
        assert len(analysis.items) == 5
        assert analysis.bill_type == BillCategory.SAAS

    @patch("clawback.analyzer.llm_json", return_value={
        "provider": "Unknown",
        "total": 0,
        "bill_type": "other",
        "billing_period": None,
        "items": [],
    })
    def test_empty_bill(self, mock_llm):
        analysis = extract_bill_items("")
        assert analysis.provider == "Unknown"
        assert analysis.items == []


class TestCompareToMarket:
    @patch("clawback.analyzer.llm_json", return_value=MOCK_COMPARE_COMCAST)
    def test_market_comparison(self, mock_llm):
        analysis = BillAnalysis(
            provider="Comcast",
            total=246.46,
            items=[
                BillItem(description="Internet", amount=89.99, category=BillCategory.INTERNET),
            ],
            bill_type=BillCategory.TELECOM,
        )
        comparisons = compare_to_market(analysis)
        assert len(comparisons) == 7
        assert all(c.savings_potential >= 0 for c in comparisons)

    @patch("clawback.analyzer.llm_json", return_value=[])
    def test_empty_comparisons(self, mock_llm):
        analysis = BillAnalysis(provider="Test", total=0)
        comparisons = compare_to_market(analysis)
        assert comparisons == []


class TestFindOvercharges:
    @patch("clawback.analyzer.llm_json", return_value=MOCK_OVERCHARGES_COMCAST)
    def test_finds_overcharges(self, mock_llm):
        analysis = BillAnalysis(
            provider="Comcast",
            total=246.46,
            items=[
                BillItem(description="Regional Sports Fee", amount=12.99),
                BillItem(description="HD Technology Fee", amount=10.00),
            ],
        )
        comparisons = [
            MarketComparison(item="Regional Sports Fee", your_price=12.99, market_avg=8.0, market_low=0, savings_potential=12.99),
            MarketComparison(item="HD Technology Fee", your_price=10.0, market_avg=0, market_low=0, savings_potential=10.0),
        ]
        overcharges = find_overcharges(analysis, comparisons)
        assert len(overcharges) == 4
        assert any(o.severity == Severity.CRITICAL for o in overcharges)


class TestCalculateSavings:
    def test_basic_savings(self):
        overcharges = [
            Overcharge(item="A", amount_overpaid=10, explanation="x"),
            Overcharge(item="B", amount_overpaid=20, explanation="y"),
        ]
        report = calculate_savings(overcharges, total=200)
        assert report.total_analyzed == 200
        assert report.total_overcharges == 30
        assert report.total_potential_savings == 30
        assert report.savings_percentage == 15.0

    def test_no_overcharges(self):
        report = calculate_savings([], total=100)
        assert report.total_overcharges == 0
        assert report.total_potential_savings == 0
        assert report.savings_percentage == 0.0

    def test_items_included(self):
        overcharges = [
            Overcharge(item="Fee", amount_overpaid=5, explanation="test"),
        ]
        report = calculate_savings(overcharges, total=50)
        assert len(report.items) == 1
        assert report.items[0].item == "Fee"
