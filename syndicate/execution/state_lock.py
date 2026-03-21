"""
Shared lock for coordinating file access between the price monitor and pipeline.

Both _price_monitor (app.py) and run_pipeline (main.py) read/write the same
JSON files (portfolio_state, open_trades, trade_ledger).  Without coordination
the price monitor can overwrite changes the pipeline just made.

Usage:
    from syndicate.execution.state_lock import execution_lock

    with execution_lock:
        paper_trader = PaperTrader.load(...)
        # ... modify ...
        paper_trader.save(...)
"""

from __future__ import annotations

import threading

# Module-level singleton — both the async price monitor (via run_in_executor
# or thread-pool) and the pipeline thread share the same process, so a
# threading.Lock is sufficient.
execution_lock = threading.Lock()
