'use client';

import { useEffect, useState, useRef } from 'react';
import {
  TrendingUp, TrendingDown, Activity,
  Target, Zap, Trophy, ArrowRight,
  DollarSign, BarChart3, Clock, Shield,
  ChevronDown, ChevronUp,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';

/* ── Types ── */

interface PortfolioState {
  cash: number;
  positions: PositionEntry[];
  total_realized_pnl: number;
  peak_value: number;
  timestamp: string;
}

interface PositionEntry {
  symbol: string;
  side: string;
  entry_price: number;
  quantity: number;
  entry_time: string;
  current_price: number;
}

interface TeamPerf {
  [team: string]: {
    total_signals: number;
    signal_accuracy: number;
    correct: number;
    incorrect: number;
    pending: number;
    current_weight: number;
  };
}

interface TradeEntry {
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl_pct: number;
  pnl_usd: number;
  exit_reason: string;
  holding_hours: number;
  exit_time: string;
  entry_time: string;
  asset_tier: string;
  conviction: number;
  confidence: number;
  stop_loss: number;
  take_profit_1: number;
  regime: string;
  direction: string;
}

interface TradeStats {
  total_trades: number;
  open_trades: number;
  closed_trades: number;
  wins: number;
  losses: number;
  breakeven: number;
  win_rate: number;
  total_pnl_usd: number;
  avg_pnl_pct: number;
  avg_pnl_usd: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  best_trade: { symbol: string; pnl_pct: number; pnl_usd: number; reason: string } | null;
  worst_trade: { symbol: string; pnl_pct: number; pnl_usd: number; reason: string } | null;
  profit_factor: number;
  risk_reward: number;
  avg_holding_hours: number;
  by_exit_reason: Record<string, { count: number; pnl_usd: number; avg_pnl_pct: number }>;
  by_symbol: Record<string, { count: number; wins: number; pnl_usd: number; win_rate: number }>;
  by_tier: Record<string, { count: number; wins: number; pnl_usd: number; win_rate: number }>;
  current_streak: number;
  max_win_streak: number;
  max_loss_streak: number;
}

/* ── Stat Card ── */

function StatCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string; sub?: string;
  icon: any; color: 'green' | 'red' | 'blue' | 'amber' | 'purple' | 'white';
}) {
  const colors = {
    green: 'text-emerald-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
    amber: 'text-amber-400',
    purple: 'text-violet-400',
    white: 'text-white/70',
  };
  return (
    <div className="bg-syn-surface border border-syn-border rounded-lg px-4 py-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={12} className="text-white/20" />
        <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted">{label}</span>
      </div>
      <p className={`text-lg font-bold tabular-nums ${colors[color]}`}>{value}</p>
      {sub && <p className="text-[10px] text-white/25 mt-0.5">{sub}</p>}
    </div>
  );
}

/* ── Helpers ── */

function fmtUsd(n: number): string {
  if (Math.abs(n) >= 1000) return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function fmtPct(n: number): string {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

function fmtHours(h: number): string {
  if (h < 1) return `${Math.round(h * 60)}m`;
  if (h < 24) return `${Math.round(h)}h`;
  return `${(h / 24).toFixed(1)}d`;
}

function exitReasonLabel(reason: string): string {
  const map: Record<string, string> = {
    STOP_LOSS: 'Stop Loss',
    TAKE_PROFIT_1: 'TP1',
    TAKE_PROFIT_2: 'TP2',
    TRAILING_STOP: 'Trail',
    BREAKEVEN_STOP: 'BE Stop',
    TIME_STOP: 'Time',
    OPEN: 'Open',
  };
  return map[reason] || reason;
}

/* ── Main Page ── */

export default function ResultsPage() {
  const [portfolio, setPortfolio] = useState<PortfolioState | null>(null);
  const [teamPerf, setTeamPerf] = useState<TeamPerf | null>(null);
  const [trades, setTrades] = useState<TradeEntry[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAllTrades, setShowAllTrades] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/portfolio`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/portfolio/team-performance`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/portfolio/trades`).then(r => r.json()).catch(() => ({ trades: [], stats: {} })),
    ]).then(([pf, tp, tr]) => {
      setPortfolio(pf);
      setTeamPerf(tp);
      const rawTrades = tr?.trades ?? (Array.isArray(tr) ? tr : []);
      // Sort: open trades first, then closed by exit_time desc
      const sorted = (Array.isArray(rawTrades) ? rawTrades : []).sort((a: TradeEntry, b: TradeEntry) => {
        if (a.exit_reason === 'OPEN' && b.exit_reason !== 'OPEN') return -1;
        if (a.exit_reason !== 'OPEN' && b.exit_reason === 'OPEN') return 1;
        return (b.exit_time ?? b.entry_time ?? '').localeCompare(a.exit_time ?? a.entry_time ?? '');
      });
      setTrades(sorted);
      if (tr?.stats && Object.keys(tr.stats).length > 0) {
        setStats(tr.stats);
      }
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-syn-accent/30 border-t-syn-accent rounded-full animate-spin" />
          <p className="text-sm text-white/30">Loading results...</p>
        </div>
      </div>
    );
  }

  // Compute portfolio metrics
  const positions = portfolio?.positions ?? [];
  const cash = portfolio?.cash ?? 100_000;
  const positionsValue = positions.reduce((acc, p) => acc + p.quantity * p.current_price, 0);
  const totalValue = cash + positionsValue;
  const initialCapital = 100_000;
  const returnPct = ((totalValue / initialCapital) - 1) * 100;
  const peakValue = portfolio?.peak_value ?? totalValue;
  const drawdownPct = peakValue > 0 ? ((peakValue - totalValue) / peakValue) * 100 : 0;
  const realizedPnl = portfolio?.total_realized_pnl ?? 0;
  const unrealizedPnl = positions.reduce((acc, p) => {
    const pnl = p.side === 'BUY'
      ? (p.current_price - p.entry_price) * p.quantity
      : (p.entry_price - p.current_price) * p.quantity;
    return acc + pnl;
  }, 0);

  const closedTrades = trades.filter(t => t.exit_reason && t.exit_reason !== 'OPEN');
  const openTrades = trades.filter(t => !t.exit_reason || t.exit_reason === 'OPEN');
  const teamEntries = teamPerf
    ? Object.entries(teamPerf).sort((a, b) => b[1].signal_accuracy - a[1].signal_accuracy)
    : [];

  const winRate = stats?.win_rate ?? (closedTrades.length > 0
    ? Math.round(closedTrades.filter(t => t.pnl_usd > 0).length / closedTrades.length * 100)
    : 0);

  const displayedTrades = showAllTrades ? closedTrades : closedTrades.slice(0, 50);

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Results</h1>
        <p className="text-sm text-syn-muted mt-1">
          Every trade. Every win. Every loss. Full transparency — nothing hidden.
        </p>
      </div>

      {/* ── Portfolio Overview ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard
          label="Portfolio Value"
          value={fmtUsd(totalValue)}
          sub={`${fmtPct(returnPct)} return`}
          icon={DollarSign}
          color={returnPct >= 0 ? 'green' : 'red'}
        />
        <StatCard
          label="Realized P&L"
          value={`${realizedPnl >= 0 ? '+' : ''}${fmtUsd(realizedPnl)}`}
          sub={`${closedTrades.length} closed trades`}
          icon={BarChart3}
          color={realizedPnl >= 0 ? 'green' : 'red'}
        />
        <StatCard
          label="Unrealized P&L"
          value={`${unrealizedPnl >= 0 ? '+' : ''}${fmtUsd(unrealizedPnl)}`}
          sub={`${positions.length} open position${positions.length !== 1 ? 's' : ''}`}
          icon={Activity}
          color={unrealizedPnl >= 0 ? 'green' : 'red'}
        />
        <StatCard
          label="Win Rate"
          value={closedTrades.length > 0 ? `${winRate}%` : '--'}
          sub={stats ? `${stats.wins}W / ${stats.losses}L` : `${closedTrades.filter(t => t.pnl_usd > 0).length}W / ${closedTrades.filter(t => t.pnl_usd <= 0).length}L`}
          icon={Target}
          color={winRate >= 55 ? 'green' : winRate >= 45 ? 'amber' : 'red'}
        />
        <StatCard
          label="Max Drawdown"
          value={`${drawdownPct.toFixed(2)}%`}
          sub={peakValue > totalValue ? `Peak: ${fmtUsd(peakValue)}` : 'At peak'}
          icon={Shield}
          color={drawdownPct > 10 ? 'red' : drawdownPct > 5 ? 'amber' : 'green'}
        />
        <StatCard
          label="Profit Factor"
          value={stats?.profit_factor ? `${stats.profit_factor.toFixed(2)}` : '--'}
          sub={stats?.avg_holding_hours ? `Avg hold: ${fmtHours(stats.avg_holding_hours)}` : ''}
          icon={TrendingUp}
          color={stats?.profit_factor && stats.profit_factor > 1 ? 'green' : stats?.profit_factor ? 'red' : 'white'}
        />
      </div>

      {/* ── Open Positions ── */}
      {positions.length > 0 && (
        <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-syn-border flex items-center gap-2">
            <Activity size={14} className="text-syn-muted" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">
              Open Positions ({positions.length})
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px]">
              <thead>
                <tr className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted border-b border-syn-border">
                  <th className="text-left px-4 py-2.5">Symbol</th>
                  <th className="text-left px-4 py-2.5">Side</th>
                  <th className="text-right px-4 py-2.5">Entry</th>
                  <th className="text-right px-4 py-2.5">Current</th>
                  <th className="text-right px-4 py-2.5">Size</th>
                  <th className="text-right px-4 py-2.5">Unrealized P&L</th>
                  <th className="text-right px-4 py-2.5">Hold Time</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, i) => {
                  const isLong = pos.side === 'BUY';
                  const pnlPct = isLong
                    ? ((pos.current_price - pos.entry_price) / pos.entry_price) * 100
                    : ((pos.entry_price - pos.current_price) / pos.entry_price) * 100;
                  const pnlUsd = isLong
                    ? (pos.current_price - pos.entry_price) * pos.quantity
                    : (pos.entry_price - pos.current_price) * pos.quantity;
                  const notional = pos.quantity * pos.current_price;
                  const holdHours = pos.entry_time
                    ? (Date.now() - new Date(pos.entry_time).getTime()) / 3600000
                    : 0;
                  const isWin = pnlUsd > 0;

                  return (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.03] transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-semibold text-sm">{pos.symbol.replace('USDT', '')}</span>
                        <span className="text-white/20 text-xs ml-1">USDT</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
                          isLong ? 'bg-emerald-400/10 text-emerald-400 ring-emerald-400/20'
                            : 'bg-red-400/10 text-red-400 ring-red-400/20'
                        }`}>{isLong ? 'LONG' : 'SHORT'}</span>
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-white/70 tabular-nums">
                        ${pos.entry_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-white/70 tabular-nums">
                        ${pos.current_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-white/40 tabular-nums">
                        {fmtUsd(notional)}
                      </td>
                      <td className={`px-4 py-3 text-right text-sm font-semibold tabular-nums ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pnlUsd >= 0 ? '+' : ''}{fmtUsd(pnlUsd)}
                        <span className="text-[10px] ml-1 opacity-50">({fmtPct(pnlPct)})</span>
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-white/30 tabular-nums">
                        {holdHours > 0 ? fmtHours(holdHours) : '\u2014'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Main Content: Trade History + Team Accuracy ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Trade History - 3/4 */}
        <div className="lg:col-span-3 bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-syn-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap size={14} className="text-syn-muted" />
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">
                Trade History
              </p>
              {closedTrades.length > 0 && (
                <span className="text-[10px] text-white/20 ml-2">
                  {closedTrades.length} closed trade{closedTrades.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
            {/* Stats summary pills */}
            {stats && stats.closed_trades > 0 && (
              <div className="hidden sm:flex items-center gap-2">
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-400/10 text-emerald-400 ring-1 ring-inset ring-emerald-400/20">
                  Avg Win: {stats.avg_win_pct ? `${stats.avg_win_pct > 0 ? '+' : ''}${stats.avg_win_pct}%` : '--'}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-red-400/10 text-red-400 ring-1 ring-inset ring-red-400/20">
                  Avg Loss: {stats.avg_loss_pct ? `${stats.avg_loss_pct}%` : '--'}
                </span>
                {stats.current_streak !== 0 && (
                  <span className={`text-[10px] px-2 py-0.5 rounded ring-1 ring-inset ${
                    stats.current_streak > 0
                      ? 'bg-emerald-400/10 text-emerald-400 ring-emerald-400/20'
                      : 'bg-red-400/10 text-red-400 ring-red-400/20'
                  }`}>
                    Streak: {stats.current_streak > 0 ? '+' : ''}{stats.current_streak}
                  </span>
                )}
              </div>
            )}
          </div>

          {closedTrades.length === 0 ? (
            <div className="px-5 py-16 text-center">
              <Activity size={32} className="mx-auto text-white/10 mb-3" />
              <p className="text-sm text-white/40">No closed trades yet</p>
              <p className="text-xs text-white/20 mt-1">
                Trades appear here after positions are closed via stop-loss, take-profit, or time stop.
              </p>
              {openTrades.length > 0 && (
                <p className="text-xs text-white/30 mt-3">
                  {openTrades.length} trade{openTrades.length !== 1 ? 's' : ''} currently open and being monitored.
                </p>
              )}
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px]">
                  <thead>
                    <tr className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted border-b border-syn-border">
                      <th className="text-left px-4 py-2.5">Symbol</th>
                      <th className="text-left px-4 py-2.5">Side</th>
                      <th className="text-right px-4 py-2.5">Entry</th>
                      <th className="text-right px-4 py-2.5">Exit</th>
                      <th className="text-left px-4 py-2.5">Reason</th>
                      <th className="text-right px-4 py-2.5">P&L</th>
                      <th className="text-right px-4 py-2.5">P&L %</th>
                      <th className="text-right px-4 py-2.5">Hold</th>
                      <th className="text-left px-4 py-2.5">Tier</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedTrades.map((trade, i) => {
                      const pnlPct = (trade.pnl_pct ?? 0) * 100;
                      const isWin = trade.pnl_usd > 0;
                      return (
                        <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.03] transition-colors">
                          <td className="px-4 py-3">
                            <span className="font-semibold text-sm">{trade.symbol.replace('USDT', '')}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
                              trade.side === 'BUY' ? 'bg-emerald-400/10 text-emerald-400 ring-emerald-400/20'
                                : 'bg-red-400/10 text-red-400 ring-red-400/20'
                            }`}>{trade.side === 'BUY' ? 'LONG' : 'SHORT'}</span>
                          </td>
                          <td className="px-4 py-3 text-right text-sm text-white/70 tabular-nums">
                            ${trade.entry_price?.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                          </td>
                          <td className="px-4 py-3 text-right text-sm text-white/70 tabular-nums">
                            ${trade.exit_price?.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
                              trade.exit_reason?.includes('PROFIT')
                                ? 'bg-emerald-400/10 text-emerald-400 ring-emerald-400/20'
                                : trade.exit_reason === 'STOP_LOSS'
                                  ? 'bg-red-400/10 text-red-400 ring-red-400/20'
                                  : 'bg-white/[0.04] text-white/40 ring-white/[0.08]'
                            }`}>
                              {exitReasonLabel(trade.exit_reason)}
                            </span>
                          </td>
                          <td className={`px-4 py-3 text-right text-sm font-semibold tabular-nums ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
                            {trade.pnl_usd >= 0 ? '+' : ''}{fmtUsd(trade.pnl_usd)}
                          </td>
                          <td className={`px-4 py-3 text-right text-sm tabular-nums ${isWin ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
                            {fmtPct(pnlPct)}
                          </td>
                          <td className="px-4 py-3 text-right text-sm text-white/30 tabular-nums">
                            {trade.holding_hours > 0 ? fmtHours(trade.holding_hours) : '\u2014'}
                          </td>
                          <td className="px-4 py-3">
                            {trade.asset_tier && (
                              <span className="text-[10px] text-white/25 capitalize">{trade.asset_tier}</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Show all / Show less toggle */}
              {closedTrades.length > 50 && (
                <button
                  onClick={() => setShowAllTrades(!showAllTrades)}
                  className="w-full py-3 border-t border-syn-border text-xs text-white/40 hover:text-white/60 hover:bg-white/[0.02] transition-colors flex items-center justify-center gap-1.5"
                >
                  {showAllTrades ? (
                    <>Show less <ChevronUp size={12} /></>
                  ) : (
                    <>Show all {closedTrades.length} trades <ChevronDown size={12} /></>
                  )}
                </button>
              )}
            </>
          )}
        </div>

        {/* Sidebar - 1/4 */}
        <div className="space-y-4">
          {/* Team Accuracy Leaderboard */}
          <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-syn-border flex items-center gap-2">
              <Trophy size={14} className="text-syn-muted" />
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Team Accuracy</p>
            </div>
            {teamEntries.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <Target size={28} className="mx-auto text-white/10 mb-3" />
                <p className="text-sm text-white/40">No team data yet</p>
                <p className="text-xs text-white/20 mt-1">Appears after signals are evaluated</p>
              </div>
            ) : (
              <div className="divide-y divide-white/[0.03]">
                {teamEntries.map(([team, s], i) => {
                  const decided = s.correct + s.incorrect;
                  const accuracyPct = decided > 0 ? (s.signal_accuracy * 100) : 0;
                  return (
                    <div key={team} className="px-5 py-3 hover:bg-white/[0.03] transition-colors">
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold w-5 text-center ${
                            i === 0 ? 'text-syn-accent' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-700' : 'text-white/30'
                          }`}>
                            {i + 1}
                          </span>
                          <span className="text-sm font-semibold capitalize">{team}</span>
                        </div>
                        <span className={`text-sm font-bold ${accuracyPct >= 60 ? 'text-emerald-400' : accuracyPct >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
                          {accuracyPct.toFixed(0)}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${accuracyPct >= 60 ? 'bg-emerald-500' : accuracyPct >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                            style={{ width: `${Math.min(100, accuracyPct)}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-white/30 shrink-0">
                          {s.correct}W {s.incorrect}L
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-[10px] text-white/20">
                        <span>{s.total_signals} signals</span>
                        <span>{s.pending} pending</span>
                        <span>wt {s.current_weight.toFixed(1)}x</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Exit Reason Breakdown */}
          {stats?.by_exit_reason && Object.keys(stats.by_exit_reason).length > 0 && (
            <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
              <div className="px-5 py-4 border-b border-syn-border">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">By Exit Reason</p>
              </div>
              <div className="divide-y divide-white/[0.03]">
                {Object.entries(stats.by_exit_reason)
                  .sort((a, b) => b[1].count - a[1].count)
                  .map(([reason, data]) => (
                    <div key={reason} className="px-5 py-2.5 flex items-center justify-between">
                      <div>
                        <span className="text-xs font-medium">{exitReasonLabel(reason)}</span>
                        <span className="text-[10px] text-white/20 ml-2">{data.count}x</span>
                      </div>
                      <span className={`text-xs font-semibold tabular-nums ${data.avg_pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data.avg_pnl_pct >= 0 ? '+' : ''}{data.avg_pnl_pct}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* By Symbol Breakdown */}
          {stats?.by_symbol && Object.keys(stats.by_symbol).length > 0 && (
            <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
              <div className="px-5 py-4 border-b border-syn-border">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">P&L by Symbol</p>
              </div>
              <div className="divide-y divide-white/[0.03]">
                {Object.entries(stats.by_symbol)
                  .sort((a, b) => b[1].pnl_usd - a[1].pnl_usd)
                  .slice(0, 10)
                  .map(([sym, data]) => (
                    <div key={sym} className="px-5 py-2.5 flex items-center justify-between">
                      <div>
                        <span className="text-xs font-semibold">{sym.replace('USDT', '')}</span>
                        <span className="text-[10px] text-white/20 ml-2">{data.count}x ({data.win_rate}%W)</span>
                      </div>
                      <span className={`text-xs font-semibold tabular-nums ${data.pnl_usd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data.pnl_usd >= 0 ? '+' : ''}{fmtUsd(data.pnl_usd)}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Best / Worst Trade Cards */}
          {stats?.best_trade && (
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-syn-surface border border-emerald-500/20 rounded-lg p-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-emerald-400/50 mb-1">Best Trade</p>
                <p className="text-sm font-bold text-emerald-400">{stats.best_trade.symbol.replace('USDT', '')}</p>
                <p className="text-xs text-emerald-400/70">+{stats.best_trade.pnl_pct}%</p>
                <p className="text-[10px] text-white/20 mt-0.5">{exitReasonLabel(stats.best_trade.reason)}</p>
              </div>
              {stats.worst_trade && (
                <div className="bg-syn-surface border border-red-500/20 rounded-lg p-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-red-400/50 mb-1">Worst Trade</p>
                  <p className="text-sm font-bold text-red-400">{stats.worst_trade.symbol.replace('USDT', '')}</p>
                  <p className="text-xs text-red-400/70">{stats.worst_trade.pnl_pct}%</p>
                  <p className="text-[10px] text-white/20 mt-0.5">{exitReasonLabel(stats.worst_trade.reason)}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* CTA */}
      <div className="bg-syn-surface border border-syn-border rounded-lg p-6 border-syn-accent/10 bg-gradient-to-r from-violet-500/[0.04] to-purple-500/[0.04]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:justify-between">
          <div>
            <h3 className="text-sm font-bold mb-1">Want deeper analysis and real-time signals?</h3>
            <p className="text-xs text-white/30">Contribute your API key to expand the hive and unlock full signal access.</p>
          </div>
          <a href="/register" className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-syn-accent text-white text-xs font-bold rounded-lg hover:shadow-lg hover:shadow-violet-500/20 transition-all">
            Contribute <ArrowRight size={14} />
          </a>
        </div>
      </div>
    </div>
  );
}
