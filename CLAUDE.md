# Syndicate Fund — AI Crypto Hedge Fund

## What This Is
A production-grade multi-agent AI hedge fund that analyzes crypto markets every 4 hours and executes paper trades. 12 specialized agents across 5 disciplines, 4 executive agents, Bayesian signal aggregation, and full transparency via a Next.js dashboard.

## Architecture Overview
```
CEO (regime + directive)
  → COO (coin selection)
  → CRO (dynamic risk rules)
  → 5 Agent Teams × N coins (parallel)
      Technical (3 agents): Trend 1D → Signal 4H → Timing 1H
      Sentiment (3 agents): Social → Market → SmartMoney
      Fundamental (2 agents): Valuation → CyclePosition
      Macro (2 agents): CryptoMacro → ExternalMacro
      OnChain (2 agents): NetworkHealth → CapitalFlow
  → Signal Aggregator (Bayesian fusion, deterministic)
  → Risk Manager (enforces CRO rules)
  → Portfolio Manager (sector allocation)
  → Paper Trader (execution)
  → Trade Monitor (SL/TP/trailing)
  → CEO post-cycle review
```

## Key Directories
- `syndicate/` — Python backend (FastAPI + agents + data + execution)
- `syndicate/agents/` — 12 agents organized by team (technical/, sentiment/, fundamental/, macro/, onchain/)
- `syndicate/data/` — 11+ data sources (Binance, Reddit, F&G, CoinGecko, CoinPaprika, Blockchain, DeFiLlama, Polymarket, Whales, etc.)
- `syndicate/aggregator/` — Bayesian log-odds signal fusion (deterministic, no LLM)
- `syndicate/executive/` — CEO, COO, CRO agents + knowledge bases
- `syndicate/board/` — Board of Directors (CPO, CSO, CTO) governance
- `syndicate/risk/` — Risk manager + ATR-based trade parameter calculation
- `syndicate/execution/` — Paper trader, trade monitor, trade ledger
- `syndicate/backtest/` — Walk-forward backtesting engine
- `syndicate/research/` — Research agents (Head of Research, Quant, Strategy)
- `syndicate/api/` — FastAPI app with 15 route modules
- `syndicate/db/` — SQLAlchemy ORM (PostgreSQL, 13 tables)
- `syndicate/comms/` — Agent communication system + email
- `syndicate/moltbook/` — Agent social network integration
- `frontend/` — Next.js 14 React dashboard (19 pages)
- `data/` — Persistent state (portfolio, trades, whale history, etc.)

## Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async), PostgreSQL 16, Redis 7
- **LLMs**: Anthropic (primary), OpenAI, Google (multi-provider)
- **Data**: pandas, numpy, ta (technical analysis), scipy, scikit-learn, hmmlearn
- **Frontend**: Next.js 14, React 18, Tailwind CSS, Recharts, Framer Motion
- **Deploy**: Docker, Railway

## Critical Files
- `syndicate/main.py` — Pipeline orchestrator (80KB, the heart of the system)
- `syndicate/data/data_layer.py` — Unified data fetcher (11 sources → MarketSnapshot)
- `syndicate/aggregator/signal_aggregator.py` — Bayesian + meta-label signal fusion
- `syndicate/agents/base.py` — BaseAgent + SIGNAL_TOOL definition
- `syndicate/config.py` — Pydantic settings (env vars)
- `syndicate/db/models.py` — 13 SQLAlchemy tables
- `syndicate/api/app.py` — FastAPI app + background cycle loop

## Data Flow
1. `DataLayer.fetch_all()` pulls from all 11 sources → `MarketSnapshot`
2. Each team gets only relevant data via `for_technical()`, `for_sentiment()`, etc.
3. Agents produce `Signal` objects (action, confidence, reasoning)
4. Team managers synthesize into `TeamSignal` (direction, conviction 1-10)
5. `SignalAggregator` fuses via Bayesian log-odds → `AggregatedSignal`
6. `RiskManager` filters by CRO rules
7. `PortfolioManager` allocates by sector
8. `PaperTrader` executes → `TradeOrder`
9. `TradeMonitor` watches SL/TP/trailing between cycles

## Database
PostgreSQL with async SQLAlchemy. Key tables: contributors, teams, agents, cycles, signals, board_decisions, ceo_posts, research_reports, agent_comms.

## Running
```bash
# Backend
docker-compose up -d  # PostgreSQL + Redis
python -m syndicate.api.app  # FastAPI on :8000

# Frontend
cd frontend && npm run dev  # Next.js on :3000
```

## Coding Conventions
- Python: ruff (line-length 100), mypy strict, pytest with asyncio
- Use `structlog` for logging, `tenacity` for retries
- All data models in `syndicate/data/models.py` (Pydantic v2)
- DB models in `syndicate/db/models.py` (SQLAlchemy 2.0)
- Every agent inherits from `BaseAgent` in `syndicate/agents/base.py`
- Environment config via pydantic-settings (`.env` file)
- JSON fallback persistence for all pipeline data (never discard data)

## Important Rules
- **Never discard pipeline data** — persist everything to DB + JSON fallback
- **Don't build infrastructure around unproven strategies** — research → validate with real data → THEN build if numbers justify
- **Paper trading only** — `PAPER_TRADING=true` is the default
- **Agents only see their discipline's data** — enforced by data layer slicing
- **Signal aggregation is deterministic** — no LLM in the aggregator, pure math
