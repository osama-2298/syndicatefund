"""
Trade Ledger — Complete trade history with lifetime statistics.

Records every trade entry, exit, and outcome. Persists across cycles.
Provides the full picture: win rate, P&L, best/worst trades, per-team attribution,
per-tier performance, streaks, Sharpe-like metrics.

This is the fund's accounting book. The CEO and all agents can reference it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class LedgerEntry:
    """A single trade record in the ledger."""

    def __init__(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        entry_time: str,
        exit_time: str,
        exit_reason: str,
        pnl_pct: float,
        pnl_usd: float,
        holding_hours: float,
        asset_tier: str,
        risk_amount: float = 0,
        stop_loss: float = 0,
        take_profit_1: float = 0,
    ) -> None:
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.quantity = quantity
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.exit_reason = exit_reason
        self.pnl_pct = pnl_pct
        self.pnl_usd = pnl_usd
        self.holding_hours = holding_hours
        self.asset_tier = asset_tier
        self.risk_amount = risk_amount
        self.stop_loss = stop_loss
        self.take_profit_1 = take_profit_1

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> LedgerEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__init__.__code__.co_varnames})


class TradeLedger:
    """
    Persistent trade history with full statistics.
    """

    def __init__(self, storage_path: str = "data/trade_ledger.json") -> None:
        self._path = Path(storage_path)
        self.entries: list[LedgerEntry] = []
        self._load()

    def record_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        asset_tier: str = "",
        risk_amount: float = 0,
        stop_loss: float = 0,
        take_profit_1: float = 0,
    ) -> None:
        """Record a trade entry (no exit yet — will be updated when closed)."""
        self.entries.append(LedgerEntry(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            exit_price=0,
            quantity=quantity,
            entry_time=datetime.now(timezone.utc).isoformat(),
            exit_time="",
            exit_reason="OPEN",
            pnl_pct=0,
            pnl_usd=0,
            holding_hours=0,
            asset_tier=asset_tier,
            risk_amount=risk_amount,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
        ))
        self._save()

    def record_exit(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        pnl_pct: float,
        pnl_usd: float,
        holding_hours: float,
        quantity: float = 0,
    ) -> None:
        """
        Record a trade exit. For partial exits (TP1, TP2), each partial is a
        separate ledger entry so stats correctly reflect each exit.
        """
        # Find the most recent OPEN entry for this symbol to get context
        source_entry = None
        for entry in reversed(self.entries):
            if entry.symbol == symbol and entry.exit_reason == "OPEN":
                source_entry = entry
                break

        if source_entry:
            # First partial exit: update the open entry
            source_entry.exit_price = exit_price
            source_entry.exit_time = datetime.now(timezone.utc).isoformat()
            source_entry.exit_reason = exit_reason
            source_entry.pnl_pct = pnl_pct
            source_entry.pnl_usd = pnl_usd
            source_entry.holding_hours = holding_hours
            if quantity > 0:
                source_entry.quantity = quantity
            self._save()
        else:
            # Partial exit from an already-closed position (TP2, trailing after TP1)
            # Find the original entry for context (any recent entry for this symbol)
            ref = None
            for entry in reversed(self.entries):
                if entry.symbol == symbol:
                    ref = entry
                    break

            self.entries.append(LedgerEntry(
                symbol=symbol,
                side=ref.side if ref else "",
                entry_price=ref.entry_price if ref else 0,
                exit_price=exit_price,
                quantity=quantity,
                entry_time=ref.entry_time if ref else "",
                exit_time=datetime.now(timezone.utc).isoformat(),
                exit_reason=exit_reason,
                pnl_pct=pnl_pct,
                pnl_usd=pnl_usd,
                holding_hours=holding_hours,
                asset_tier=ref.asset_tier if ref else "",
                risk_amount=ref.risk_amount if ref else 0,
                stop_loss=ref.stop_loss if ref else 0,
                take_profit_1=ref.take_profit_1 if ref else 0,
            ))
            self._save()

    def record_outcome(self, outcome) -> None:
        """Record a TradeOutcome from the trade monitor."""
        self.record_exit(
            symbol=outcome.symbol,
            exit_price=outcome.exit_price,
            exit_reason=outcome.exit_reason,
            pnl_pct=outcome.pnl_pct,
            pnl_usd=outcome.pnl_usd,
            holding_hours=outcome.holding_hours,
            quantity=outcome.quantity_exited,
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Compute comprehensive trading statistics.
        This is the full fund performance report.
        """
        closed = [e for e in self.entries if e.exit_reason != "OPEN"]
        open_trades = [e for e in self.entries if e.exit_reason == "OPEN"]

        if not closed:
            return {
                "total_trades": 0,
                "open_trades": len(open_trades),
                "closed_trades": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "win_rate": 0,
                "total_pnl_usd": 0,
                "avg_pnl_pct": 0,
                "avg_pnl_usd": 0,
                "avg_win_pct": 0,
                "avg_loss_pct": 0,
                "best_trade": None,
                "worst_trade": None,
                "profit_factor": 0,
                "avg_holding_hours": 0,
                "by_exit_reason": {},
                "by_tier": {},
                "by_symbol": {},
                "current_streak": 0,
                "max_win_streak": 0,
                "max_loss_streak": 0,
            }

        wins = [e for e in closed if e.pnl_pct > 0.001]
        losses = [e for e in closed if e.pnl_pct < -0.001]
        breakeven = [e for e in closed if -0.001 <= e.pnl_pct <= 0.001]

        total_pnl = sum(e.pnl_usd for e in closed)
        gross_profit = sum(e.pnl_usd for e in wins) if wins else 0
        gross_loss = abs(sum(e.pnl_usd for e in losses)) if losses else 0

        # Win/loss averages
        avg_win_pct = sum(e.pnl_pct for e in wins) / len(wins) if wins else 0
        avg_loss_pct = sum(e.pnl_pct for e in losses) / len(losses) if losses else 0
        avg_win_usd = sum(e.pnl_usd for e in wins) / len(wins) if wins else 0
        avg_loss_usd = sum(e.pnl_usd for e in losses) / len(losses) if losses else 0

        # Best/worst trades
        best = max(closed, key=lambda e: e.pnl_pct)
        worst = min(closed, key=lambda e: e.pnl_pct)

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0

        # Expectancy (average $ gained per trade)
        expectancy = total_pnl / len(closed)

        # Risk/reward ratio
        risk_reward = abs(avg_win_pct / avg_loss_pct) if avg_loss_pct != 0 else 0

        # Average holding time
        avg_hours = sum(e.holding_hours for e in closed) / len(closed)

        # Streaks
        streaks = self._compute_streaks(closed)

        # By exit reason
        by_reason: dict[str, dict] = {}
        for e in closed:
            r = e.exit_reason
            if r not in by_reason:
                by_reason[r] = {"count": 0, "pnl_usd": 0, "avg_pnl_pct": 0, "pnl_pcts": []}
            by_reason[r]["count"] += 1
            by_reason[r]["pnl_usd"] += e.pnl_usd
            by_reason[r]["pnl_pcts"].append(e.pnl_pct)
        for r in by_reason:
            pcts = by_reason[r].pop("pnl_pcts")
            by_reason[r]["avg_pnl_pct"] = round(sum(pcts) / len(pcts) * 100, 2) if pcts else 0
            by_reason[r]["pnl_usd"] = round(by_reason[r]["pnl_usd"], 2)

        # By tier
        by_tier: dict[str, dict] = {}
        for e in closed:
            t = e.asset_tier or "unknown"
            if t not in by_tier:
                by_tier[t] = {"count": 0, "wins": 0, "pnl_usd": 0}
            by_tier[t]["count"] += 1
            if e.pnl_pct > 0.001:
                by_tier[t]["wins"] += 1
            by_tier[t]["pnl_usd"] += e.pnl_usd
        for t in by_tier:
            cnt = by_tier[t]["count"]
            by_tier[t]["win_rate"] = round(by_tier[t]["wins"] / cnt * 100, 1) if cnt > 0 else 0
            by_tier[t]["pnl_usd"] = round(by_tier[t]["pnl_usd"], 2)

        # By symbol
        by_symbol: dict[str, dict] = {}
        for e in closed:
            s = e.symbol
            if s not in by_symbol:
                by_symbol[s] = {"count": 0, "wins": 0, "pnl_usd": 0}
            by_symbol[s]["count"] += 1
            if e.pnl_pct > 0.001:
                by_symbol[s]["wins"] += 1
            by_symbol[s]["pnl_usd"] += e.pnl_usd
        for s in by_symbol:
            cnt = by_symbol[s]["count"]
            by_symbol[s]["win_rate"] = round(by_symbol[s]["wins"] / cnt * 100, 1) if cnt > 0 else 0
            by_symbol[s]["pnl_usd"] = round(by_symbol[s]["pnl_usd"], 2)
        by_symbol = dict(sorted(by_symbol.items(), key=lambda x: -x[1]["pnl_usd"]))

        return {
            "total_trades": len(self.entries),
            "open_trades": len(open_trades),
            "closed_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "breakeven": len(breakeven),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
            "total_pnl_usd": round(total_pnl, 2),
            "avg_pnl_pct": round(sum(e.pnl_pct for e in closed) / len(closed) * 100, 2),
            "avg_pnl_usd": round(expectancy, 2),
            "avg_win_pct": round(avg_win_pct * 100, 2),
            "avg_loss_pct": round(avg_loss_pct * 100, 2),
            "avg_win_usd": round(avg_win_usd, 2),
            "avg_loss_usd": round(avg_loss_usd, 2),
            "best_trade": {
                "symbol": best.symbol, "pnl_pct": round(best.pnl_pct * 100, 2),
                "pnl_usd": round(best.pnl_usd, 2), "reason": best.exit_reason,
            },
            "worst_trade": {
                "symbol": worst.symbol, "pnl_pct": round(worst.pnl_pct * 100, 2),
                "pnl_usd": round(worst.pnl_usd, 2), "reason": worst.exit_reason,
            },
            "profit_factor": round(profit_factor, 2),
            "risk_reward": round(risk_reward, 2),
            "avg_holding_hours": round(avg_hours, 1),
            "by_exit_reason": by_reason,
            "by_tier": by_tier,
            "by_symbol": by_symbol,
            "current_streak": streaks["current"],
            "max_win_streak": streaks["max_win"],
            "max_loss_streak": streaks["max_loss"],
        }

    def get_calibration(self) -> dict[str, Any]:
        """
        Compute actual win rate per conviction level.
        This is the LEARNING LOOP — it tells us if conviction 7 really wins 70%.

        Returns:
            {
                "by_conviction": {7: {"count": 10, "wins": 6, "win_rate": 60.0}, ...},
                "calibration_gap": float,  # avg |predicted - actual| win rate
                "recommendation": str,
            }
        """
        closed = [e for e in self.entries if e.exit_reason != "OPEN"]
        if len(closed) < 10:
            return {"by_conviction": {}, "calibration_gap": 0, "recommendation": "Insufficient data (<10 closed trades)"}

        # Group by conviction level (rounded to nearest integer)
        by_conv: dict[int, dict] = {}
        for e in closed:
            # Infer conviction from confidence (confidence = conviction / 10)
            conv = max(1, min(10, round(e.pnl_pct * 10 + 5)))  # rough proxy
            # Better: use the stop_loss to estimate original conviction
            # For now, use a simple proxy from the entry data
            if e.stop_loss > 0 and e.entry_price > 0:
                # Risk amount relative to position = original confidence proxy
                stop_dist_pct = abs(e.entry_price - e.stop_loss) / e.entry_price
                # Map back: wider stop = lower tier = lower conviction (rough)
                if stop_dist_pct < 0.05:
                    conv = 8
                elif stop_dist_pct < 0.10:
                    conv = 7
                elif stop_dist_pct < 0.15:
                    conv = 6
                elif stop_dist_pct < 0.25:
                    conv = 5
                else:
                    conv = 4

            if conv not in by_conv:
                by_conv[conv] = {"count": 0, "wins": 0}
            by_conv[conv]["count"] += 1
            if e.pnl_pct > 0.001:
                by_conv[conv]["wins"] += 1

        # Compute win rates
        for conv in by_conv:
            cnt = by_conv[conv]["count"]
            by_conv[conv]["win_rate"] = round(by_conv[conv]["wins"] / cnt * 100, 1) if cnt > 0 else 0
            by_conv[conv]["expected_wr"] = conv * 10  # What we THINK it should be
            by_conv[conv]["gap"] = round(by_conv[conv]["expected_wr"] - by_conv[conv]["win_rate"], 1)

        # Average calibration gap
        gaps = [abs(d["gap"]) for d in by_conv.values() if d["count"] >= 3]
        avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else 0

        # Recommendation
        if avg_gap > 20:
            recommendation = "SEVERELY miscalibrated. Conviction scores are much higher than actual win rates."
        elif avg_gap > 10:
            recommendation = "Moderately miscalibrated. Consider adjusting agent prompts to anchor lower."
        elif avg_gap > 5:
            recommendation = "Slightly miscalibrated. Normal for early-stage system."
        else:
            recommendation = "Well calibrated."

        return {
            "by_conviction": dict(sorted(by_conv.items())),
            "calibration_gap": avg_gap,
            "recommendation": recommendation,
        }

    def _compute_streaks(self, closed: list[LedgerEntry]) -> dict:
        """Compute win/loss streaks."""
        if not closed:
            return {"current": 0, "max_win": 0, "max_loss": 0}

        max_win = 0
        max_loss = 0
        current = 0

        for e in closed:
            if e.pnl_pct > 0.001:
                if current > 0:
                    current += 1
                else:
                    current = 1
                max_win = max(max_win, current)
            elif e.pnl_pct < -0.001:
                if current < 0:
                    current -= 1
                else:
                    current = -1
                max_loss = max(max_loss, abs(current))
            else:
                current = 0

        return {"current": current, "max_win": max_win, "max_loss": max_loss}

    def format_summary(self) -> str:
        """Format a human-readable summary for terminal display."""
        s = self.get_stats()

        if s["closed_trades"] == 0:
            open_n = s["open_trades"]
            if open_n > 0:
                return f"No closed trades yet. {open_n} open positions being monitored."
            return "No trades executed yet."

        lines = []
        lines.append(
            f"{s['closed_trades']} trades  |  "
            f"{s['wins']}W / {s['losses']}L / {s['breakeven']}BE  |  "
            f"Win rate: {s['win_rate']}%"
        )
        lines.append(
            f"Total P&L: ${s['total_pnl_usd']:+,.2f}  |  "
            f"Avg: ${s['avg_pnl_usd']:+,.2f}/trade  |  "
            f"Profit factor: {s['profit_factor']}"
        )
        lines.append(
            f"Avg win: {s['avg_win_pct']:+.2f}% (${s['avg_win_usd']:+,.2f})  |  "
            f"Avg loss: {s['avg_loss_pct']:+.2f}% (${s['avg_loss_usd']:+,.2f})  |  "
            f"R:R {s['risk_reward']:.1f}"
        )

        best = s["best_trade"]
        worst = s["worst_trade"]
        if best:
            lines.append(
                f"Best: {best['symbol']} {best['pnl_pct']:+.1f}% (${best['pnl_usd']:+,.2f}) {best['reason']}  |  "
                f"Worst: {worst['symbol']} {worst['pnl_pct']:+.1f}% (${worst['pnl_usd']:+,.2f}) {worst['reason']}"
            )

        lines.append(f"Avg hold: {s['avg_holding_hours']:.0f}h  |  Streak: {s['current_streak']:+d}")

        # By tier
        if s["by_tier"]:
            tier_parts = []
            for tier, data in s["by_tier"].items():
                tier_parts.append(f"{tier}: {data['win_rate']}%W ${data['pnl_usd']:+,.0f}")
            lines.append("By tier: " + "  |  ".join(tier_parts))

        # By exit reason
        if s["by_exit_reason"]:
            reason_parts = []
            for reason, data in s["by_exit_reason"].items():
                reason_parts.append(f"{reason}: {data['count']}x avg {data['avg_pnl_pct']:+.1f}%")
            lines.append("Exits: " + "  |  ".join(reason_parts))

        return "\n".join(lines)

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self.entries = [LedgerEntry.from_dict(d) for d in data]
        except Exception as e:
            logger.error("ledger_load_failed", error=str(e))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self.entries]
        self._path.write_text(json.dumps(data, indent=2, default=str))
