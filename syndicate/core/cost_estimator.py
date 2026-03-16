"""Cost estimation for contributor agent usage."""

from decimal import Decimal

# Per 1M tokens pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-opus-4-6": {"input_per_m": 15.0, "output_per_m": 75.0},
    "claude-sonnet-4-6": {"input_per_m": 3.0, "output_per_m": 15.0},
    "claude-haiku-4-5-20251001": {"input_per_m": 0.80, "output_per_m": 4.0},
    # OpenAI
    "gpt-4o": {"input_per_m": 2.50, "output_per_m": 10.0},
    "gpt-4o-mini": {"input_per_m": 0.15, "output_per_m": 0.60},
    # Google
    "gemini-2.0-flash": {"input_per_m": 0.10, "output_per_m": 0.40},
}

# Average tokens per agent call (estimated)
AVG_INPUT_TOKENS = 2000
AVG_OUTPUT_TOKENS = 500

# Cycles per day (every 4 hours)
CYCLES_PER_DAY = 6

# Average coins per cycle
AVG_COINS_PER_CYCLE = 8


def estimate_monthly_cost(
    model: str,
    num_agents: int,
) -> Decimal:
    """Estimate monthly USD cost for N agents on a given model."""
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        pricing = MODEL_PRICING["claude-sonnet-4-6"]  # Default fallback

    input_cost_per_call = (AVG_INPUT_TOKENS / 1_000_000) * pricing["input_per_m"]
    output_cost_per_call = (AVG_OUTPUT_TOKENS / 1_000_000) * pricing["output_per_m"]
    cost_per_call = input_cost_per_call + output_cost_per_call

    # Each agent runs once per coin per cycle
    calls_per_day = num_agents * AVG_COINS_PER_CYCLE * CYCLES_PER_DAY
    monthly_cost = cost_per_call * calls_per_day * 30

    return Decimal(str(round(monthly_cost, 2)))


def compute_call_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    """Compute actual cost of a single LLM call from token counts."""
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        pricing = MODEL_PRICING["claude-sonnet-4-6"]

    input_cost = (input_tokens / 1_000_000) * pricing["input_per_m"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_m"]

    return Decimal(str(round(input_cost + output_cost, 6)))
