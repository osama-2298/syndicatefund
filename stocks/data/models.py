"""
Stock-specific data models.

Extends the base Syndicate models with equity-specific structures:
fundamentals, earnings, short selling, options, institutional data, news.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════
#  Fundamentals
# ═══════════════════════════════════════════


class StockFundamentals(BaseModel):
    """Core fundamental data from Yahoo Finance."""

    symbol: str
    market_cap: float | None = None
    enterprise_value: float | None = None

    # Valuation ratios
    pe_trailing: float | None = None
    pe_forward: float | None = None
    peg_ratio: float | None = None
    price_to_sales: float | None = None
    price_to_book: float | None = None
    ev_to_ebitda: float | None = None

    # Profitability
    profit_margin: float | None = None
    operating_margin: float | None = None
    roe: float | None = None
    roa: float | None = None

    # Growth
    revenue_growth: float | None = None
    earnings_growth: float | None = None

    # Financial health
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    free_cash_flow: float | None = None

    # Dividends
    dividend_yield: float | None = None
    payout_ratio: float | None = None
    ex_dividend_date: str | None = None

    # Sector/Industry
    sector: str = ""
    industry: str = ""
    gics_sector: str = ""

    def to_summary(self) -> str:
        lines = [f"Fundamentals for {self.symbol}:"]
        if self.market_cap:
            lines.append(f"  Market Cap: ${self.market_cap:,.0f}")
        if self.pe_trailing:
            lines.append(f"  P/E (TTM): {self.pe_trailing:.1f}")
        if self.pe_forward:
            lines.append(f"  P/E (Fwd): {self.pe_forward:.1f}")
        if self.peg_ratio:
            lines.append(f"  PEG: {self.peg_ratio:.2f}")
        if self.ev_to_ebitda:
            lines.append(f"  EV/EBITDA: {self.ev_to_ebitda:.1f}")
        if self.roe:
            lines.append(f"  ROE: {self.roe:.1%}")
        if self.profit_margin:
            lines.append(f"  Profit Margin: {self.profit_margin:.1%}")
        if self.debt_to_equity:
            lines.append(f"  Debt/Equity: {self.debt_to_equity:.2f}")
        if self.dividend_yield:
            lines.append(f"  Dividend Yield: {self.dividend_yield:.2%}")
        if self.revenue_growth:
            lines.append(f"  Revenue Growth: {self.revenue_growth:.1%}")
        if self.sector:
            lines.append(f"  Sector: {self.sector}")
        return "\n".join(lines)


# ═══════════════════════════════════════════
#  Earnings
# ═══════════════════════════════════════════


class EarningsData(BaseModel):
    """Earnings calendar and history."""

    symbol: str
    next_earnings_date: str | None = None
    days_to_earnings: int | None = None
    in_blackout: bool = False

    # Historical earnings surprises (last 4 quarters)
    last_surprises: list[dict[str, Any]] = Field(default_factory=list)
    # e.g. [{"date": "2025-Q4", "expected_eps": 1.50, "actual_eps": 1.65, "surprise_pct": 10.0}]

    avg_surprise_pct: float | None = None
    beat_rate: float | None = None  # % of last 4 quarters that beat


# ═══════════════════════════════════════════
#  Short Selling
# ═══════════════════════════════════════════


class ShortSellingData(BaseModel):
    """Short selling and squeeze risk metrics."""

    symbol: str
    short_interest_pct: float | None = None  # Short interest as % of float
    short_ratio: float | None = None  # Days to cover
    short_pct_change: float | None = None  # MoM change in short interest

    # Borrow cost (estimated)
    borrow_cost_est: float | None = None  # Annual % (1% = normal, 10%+ = expensive)
    hard_to_borrow: bool = False

    # Short Sale Restriction (SSR / Rule 201)
    ssr_active: bool = False  # Price dropped >10% from prior close

    # Squeeze risk
    squeeze_risk: str = "LOW"  # LOW, MEDIUM, HIGH
    # HIGH if: SI% > 20%, short_ratio > 5, borrow_cost > 5%


# ═══════════════════════════════════════════
#  Options
# ═══════════════════════════════════════════


class OptionsSnapshot(BaseModel):
    """Options market summary for a stock."""

    symbol: str
    put_call_ratio: float | None = None
    implied_volatility: float | None = None  # Average IV across chains
    iv_rank: float | None = None  # IV percentile (0-100)

    # Unusual activity
    unusual_calls: int = 0
    unusual_puts: int = 0
    unusual_activity_flag: bool = False

    # Max pain
    max_pain: float | None = None


# ═══════════════════════════════════════════
#  Institutional
# ═══════════════════════════════════════════


class InstitutionalData(BaseModel):
    """Institutional ownership from SEC 13F filings."""

    symbol: str
    institutional_pct: float | None = None  # % held by institutions
    institutional_change_qoq: float | None = None  # QoQ change in institutional ownership
    top_holders: list[dict[str, Any]] = Field(default_factory=list)
    # e.g. [{"name": "Vanguard", "shares": 1000000, "pct": 8.5, "change": "+2%"}]

    # Insider transactions (Form 4)
    insider_buys_90d: int = 0
    insider_sells_90d: int = 0
    insider_net_shares: int = 0  # Net shares bought - sold
    notable_insiders: list[dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════
#  Market Indices
# ═══════════════════════════════════════════


class MarketIndicesSnapshot(BaseModel):
    """Broad market indices and macro indicators."""

    spy_price: float | None = None
    spy_change_pct: float | None = None
    qqq_price: float | None = None
    qqq_change_pct: float | None = None
    iwm_price: float | None = None  # Russell 2000
    iwm_change_pct: float | None = None

    vix: float | None = None
    vix_change: float | None = None

    # Rates & Dollar
    treasury_2y: float | None = None
    treasury_10y: float | None = None
    yield_curve_spread: float | None = None  # 10Y - 2Y
    dxy: float | None = None  # US Dollar Index

    # Commodities
    oil_price: float | None = None
    gold_price: float | None = None

    # CNN Fear & Greed
    cnn_fear_greed: int | None = None
    cnn_fear_greed_label: str | None = None

    # Market breadth
    advance_decline_ratio: float | None = None
    pct_above_200sma: float | None = None
    new_highs: int | None = None
    new_lows: int | None = None


# ═══════════════════════════════════════════
#  Sector Performance
# ═══════════════════════════════════════════


class SectorPerformance(BaseModel):
    """GICS sector ETF performance."""

    # GICS sectors mapped to ETFs
    sectors: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # e.g. {"Technology": {"etf": "XLK", "change_1d": 0.5, "change_5d": 2.1, "change_1m": -1.0}}

    hot_sectors: list[str] = Field(default_factory=list)  # Sectors with >2% 5d gain
    cold_sectors: list[str] = Field(default_factory=list)  # Sectors with <-2% 5d loss


# ═══════════════════════════════════════════
#  News
# ═══════════════════════════════════════════


class NewsItem(BaseModel):
    """A single news article."""

    headline: str
    source: str = ""
    url: str = ""
    published: str = ""
    symbol: str = ""
    category: str = ""  # earnings, m_and_a, regulatory, analyst, fed, geopolitical
    sentiment: str = ""  # positive, negative, neutral
    impact_score: float = 0.0  # 0-1 estimated impact magnitude


# ═══════════════════════════════════════════
#  Stock Selection (mirrors CoinScore/CoinSelection)
# ═══════════════════════════════════════════


class StockScore(BaseModel):
    """Scoring of a single stock for selection."""

    symbol: str
    volume_score: float = Field(ge=0.0, le=1.0, default=0.0)
    volatility_score: float = Field(ge=0.0, le=1.0, default=0.0)
    momentum_score: float = Field(ge=-1.0, le=1.0, default=0.0)
    fundamental_score: float = Field(ge=0.0, le=1.0, default=0.0)
    composite_score: float = 0.0


class StockSelection(BaseModel):
    """Output of the COO agent — which stocks to analyze this cycle."""

    selected_stocks: list[str]
    scores: list[StockScore]
    reasoning: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
