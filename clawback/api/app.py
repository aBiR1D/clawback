"""FastAPI application — REST endpoints for Clawback."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
    NegotiationStrategy,
    Overcharge,
    SavingsReport,
)
from clawback.negotiator import draft_email, generate_strategy

app = FastAPI(
    title="Clawback API",
    description="AI-powered bill analysis and negotiation",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class BillTextRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Raw bill text to analyse")


class AnalyzeResponse(BaseModel):
    analysis: BillAnalysis
    comparisons: list[MarketComparison]
    overcharges: list[Overcharge]
    savings: SavingsReport


class NegotiateResponse(BaseModel):
    analysis: BillAnalysis
    overcharges: list[Overcharge]
    savings: SavingsReport
    strategy: NegotiationStrategy
    email: NegotiationEmail


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_bill(request: BillTextRequest) -> AnalyzeResponse:
    """Analyze bill text — extract items, compare to market, find overcharges."""
    try:
        analysis = extract_bill_items(request.text)
        comparisons = compare_to_market(analysis)
        overcharges = find_overcharges(analysis, comparisons)
        savings = calculate_savings(overcharges, total=analysis.total)
        return AnalyzeResponse(
            analysis=analysis,
            comparisons=comparisons,
            overcharges=overcharges,
            savings=savings,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/negotiate", response_model=NegotiateResponse)
async def negotiate_bill(request: BillTextRequest) -> NegotiateResponse:
    """Full pipeline — analyze, find overcharges, generate negotiation email."""
    try:
        analysis = extract_bill_items(request.text)
        comparisons = compare_to_market(analysis)
        overcharges = find_overcharges(analysis, comparisons)
        savings = calculate_savings(overcharges, total=analysis.total)
        strat = generate_strategy(analysis, overcharges)
        email = draft_email(strat, analysis.provider)
        return NegotiateResponse(
            analysis=analysis,
            overcharges=overcharges,
            savings=savings,
            strategy=strat,
            email=email,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
