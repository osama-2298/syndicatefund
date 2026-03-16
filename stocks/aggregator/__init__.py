"""
Stock Aggregator — imports SignalAggregator from syndicate directly.
The aggregator handles any TeamType generically.
"""

from syndicate.aggregator.signal_aggregator import SignalAggregator

__all__ = ["SignalAggregator"]
