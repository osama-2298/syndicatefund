"""
Options data — put/call ratio, IV, unusual activity, max pain.

Wraps yahoo_finance options data with additional analysis.
"""

from __future__ import annotations

import structlog

from stocks.data.yahoo_finance import get_options_snapshot
from stocks.data.models import OptionsSnapshot

logger = structlog.get_logger()


def get_options_summary(symbol: str) -> OptionsSnapshot | None:
    """Get full options summary for a stock."""
    return get_options_snapshot(symbol)


def get_batch_options(symbols: list[str]) -> dict[str, OptionsSnapshot]:
    """Get options data for multiple stocks."""
    results = {}
    for symbol in symbols:
        try:
            snapshot = get_options_snapshot(symbol)
            if snapshot:
                results[symbol] = snapshot
        except Exception as e:
            logger.warning("options_batch_failed", symbol=symbol, error=str(e))
    return results
