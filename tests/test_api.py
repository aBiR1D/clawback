"""Tests for the FastAPI endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from clawback.api.app import app
from clawback.models import (
    BillAnalysis,
    BillCategory,
    BillItem,
    MarketComparison,
    NegotiationEmail,
    NegotiationStrategy,
    Overcharge,
    SavingsReport,
    Tone,
)

client = TestClient(app)


class TestHealth:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAnalyzeEndpoint:
    @patch("clawback.api.app.find_overcharges")
    @patch("clawback.api.app.compare_to_market")
    @patch("clawback.api.app.extract_bill_items")
    def test_analyze(self, mock_extract, mock_compare, mock_overcharges):
        analysis = BillAnalysis(
            provider="TestCo",
            total=100.0,
            items=[BillItem(description="Service", amount=100.0)],
            bill_type=BillCategory.OTHER,
        )
        mock_extract.return_value = analysis
        mock_compare.return_value = [
            MarketComparison(
                item="Service", your_price=100, market_avg=80, market_low=60, savings_potential=20
            )
        ]
        mock_overcharges.return_value = [
            Overcharge(item="Service", amount_overpaid=20, explanation="Above market avg")
        ]

        response = client.post("/api/v1/analyze", json={"text": "TestCo bill: Service $100"})
        assert response.status_code == 200
        body = response.json()
        assert body["analysis"]["provider"] == "TestCo"
        assert len(body["overcharges"]) == 1
        assert body["savings"]["total_overcharges"] == 20.0

    def test_short_text_rejected(self):
        response = client.post("/api/v1/analyze", json={"text": "short"})
        assert response.status_code == 422
