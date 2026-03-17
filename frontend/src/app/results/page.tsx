'use client';

import { useEffect, useState } from 'react';
import {
  TrendingUp, TrendingDown, Activity,
  Target, Zap, Trophy, ArrowRight,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  pnl_pct: number;
  pnl_usd: number;
  exit_reason: string;
  holding_hours: number;
  exit_time: string;
}

export default function ResultsPage() {
  const [teamPerf, setTeamPerf] = useState<TeamPerf | null>(null);
  const [trades, setTrades] = useState<TradeEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/portfolio/team-performance`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/portfolio/trades`).then(r => r.json()).catch(() => ({ trades: [] })),
    ]).then(([tp, tr]) => {
      setTeamPerf(tp);
      const rawTrades = Array.isArray(tr) ? tr : (tr?.trades ?? tr ?? []);
      const closedTrades = (Array.isArray(rawTrades) ? rawTrades : [])
        .filter((t: TradeEntry) => t.exit_reason && t.exit_reason !== 'OPEN')
        .sort((a: TradeEntry, b: TradeEntry) => (b.exit_time ?? '').localeCompare(a.exit_time ?? ''));
      setTrades(closedTrades);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
          <p className="text-sm text-white/30">Loading results...</p>
        </div>
      </div>
    );
  }

  const teamEntries = teamPerf
    ? Object.entries(teamPerf).sort((a, b) => b[1].signal_accuracy - a[1].signal_accuracy)
    : [];

  const recentTrades = trades.slice(0, 20);

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Results</h1>
        <p className="text-sm text-hive-muted mt-1">Team accuracy and live trade history</p>
      </div>

      {/* Team Accuracy Leaderboard + Recent Trades side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Team Leaderboard - 1/3 */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-2">
            <Trophy size={14} className="text-amber-400/60" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Team Accuracy</p>
          </div>
          {teamEntries.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <Target size={28} className="mx-auto text-white/10 mb-3" />
              <p className="text-sm text-white/40">No team data yet</p>
              <p className="text-xs text-white/20 mt-1">Performance data appears after signals are evaluated</p>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.03]">
              {teamEntries.map(([team, stats], i) => {
                const decided = stats.correct + stats.incorrect;
                const accuracyPct = decided > 0 ? (stats.signal_accuracy * 100) : 0;
                return (
                  <div key={team} className="px-5 py-3 hover:bg-white/[0.03] transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold w-5 text-center ${
                          i === 0 ? 'text-amber-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-700' : 'text-white/30'
                        }`}>
                          {i + 1}
                        </span>
                        <span className="text-sm font-semibold capitalize">{team}</span>
                      </div>
                      <span className={`text-sm font-bold ${accuracyPct >= 60 ? 'text-emerald-400' : accuracyPct >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
                        {accuracyPct.toFixed(0)}%
                      </span>
                    </div>
                    {/* Accuracy bar */}
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${accuracyPct >= 60 ? 'bg-emerald-500' : accuracyPct >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                          style={{ width: `${Math.min(100, accuracyPct)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-white/30 shrink-0">
                        {stats.correct}W {stats.incorrect}L
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-white/20">
                      <span>{stats.total_signals} signals</span>
                      <span>{stats.pending} pending</span>
                      <span>wt {stats.current_weight.toFixed(1)}x</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Trades - 2/3 */}
        <div className="lg:col-span-2 glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap size={14} className="text-amber-400/60" />
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Recent Closed Trades</p>
            </div>
            {trades.length > 20 && (
              <span className="text-[10px] text-white/20">Showing 20 of {trades.length}</span>
            )}
          </div>
          {recentTrades.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <Activity size={28} className="mx-auto text-white/10 mb-3" />
              <p className="text-sm text-white/40">No closed trades yet</p>
              <p className="text-xs text-white/20 mt-1">Trades appear here after positions are closed</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 border-b border-white/[0.06]">
                    <th className="text-left px-4 py-2.5">Symbol</th>
                    <th className="text-left px-4 py-2.5">Side</th>
                    <th className="text-right px-4 py-2.5">Entry</th>
                    <th className="text-right px-4 py-2.5">Exit</th>
                    <th className="text-left px-4 py-2.5">Reason</th>
                    <th className="text-right px-4 py-2.5">P&L</th>
                    <th className="text-right px-4 py-2.5">Hold</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTrades.map((trade, i) => {
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
                          }`}>{trade.side}</span>
                        </td>
                        <td className="px-4 py-3 text-right text-sm text-white/70">${trade.entry_price.toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-sm text-white/70">${trade.exit_price.toLocaleString()}</td>
                        <td className="px-4 py-3">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset bg-white/[0.04] text-white/40 ring-white/[0.08]">
                            {trade.exit_reason}
                          </span>
                        </td>
                        <td className={`px-4 py-3 text-right text-sm font-semibold ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
                          {trade.pnl_usd >= 0 ? '+' : ''}${trade.pnl_usd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                          <span className="text-[10px] ml-1 opacity-50">({pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%)</span>
                        </td>
                        <td className="px-4 py-3 text-right text-sm text-white/30">
                          {trade.holding_hours > 0 ? `${Math.round(trade.holding_hours)}h` : '\u2014'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* CTA */}
      <div className="glass-card p-6 border-amber-400/10 bg-gradient-to-r from-amber-500/[0.04] to-orange-500/[0.04]">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold mb-1">Want deeper analysis and real-time signals?</h3>
            <p className="text-xs text-white/30">Contribute your API key to expand the hive and unlock full signal access.</p>
          </div>
          <a href="/register" className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-black text-xs font-bold rounded-lg hover:shadow-lg hover:shadow-amber-500/20 transition-all">
            Contribute <ArrowRight size={14} />
          </a>
        </div>
      </div>
    </div>
  );
}
