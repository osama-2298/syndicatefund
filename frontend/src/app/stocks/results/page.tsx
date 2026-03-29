
'use client';

import {
  BarChart3, Activity, Trophy, Target, Zap, Shield,
  TrendingUp, TrendingDown, ArrowRight, Calendar, AlertTriangle,
} from 'lucide-react';
import { DemoBanner } from '@/components/DemoBanner';
import { wilsonInterval } from '@/lib/stats';

// ── Demo Data ──────────────────────────────────────────────────────────

const demoMetrics = {
  sharpe: 1.45,
  maxDrawdown: -8.2,
  totalReturn: 12.8,
  winRate: 61.5,
  totalTrades: 48,
  profitFactor: 1.72,
  avgHoldDays: 4.2,
  longWinRate: 65.0,
  shortWinRate: 52.3,
};

const demoTeamPerf = [
  { team: 'Fundamental', accuracy: 68, correct: 29, incorrect: 13, total: 42, weight: 1.3, color: 'emerald' },
  { team: 'Institutional', accuracy: 64, correct: 22, incorrect: 13, total: 35, weight: 1.1, color: 'cyan' },
  { team: 'Technical', accuracy: 62, correct: 28, incorrect: 17, total: 45, weight: 1.2, color: 'blue' },
  { team: 'Macro', accuracy: 58, correct: 23, incorrect: 17, total: 40, weight: 1.0, color: 'orange' },
  { team: 'Sentiment', accuracy: 55, correct: 21, incorrect: 17, total: 38, weight: 1.0, color: 'purple' },
  { team: 'News', accuracy: 52, correct: 16, incorrect: 14, total: 30, weight: 0.9, color: 'pink' },
];

const demoClosedTrades = [
  { symbol: 'META', side: 'BUY', entry: 485.00, exit: 512.30, pnlUsd: 546.00, pnlPct: 5.63, exitReason: 'TP_HIT', holdHours: 72, date: '2026-03-15' },
  { symbol: 'AMZN', side: 'BUY', entry: 178.50, exit: 185.20, pnlUsd: 335.00, pnlPct: 3.75, exitReason: 'TP_HIT', holdHours: 96, date: '2026-03-14' },
  { symbol: 'GOOGL', side: 'SELL', entry: 155.00, exit: 158.80, pnlUsd: -190.00, pnlPct: -2.45, exitReason: 'SL_HIT', holdHours: 24, date: '2026-03-13' },
  { symbol: 'JPM', side: 'BUY', entry: 198.00, exit: 205.40, pnlUsd: 370.00, pnlPct: 3.74, exitReason: 'TP_HIT', holdHours: 120, date: '2026-03-12' },
  { symbol: 'AMD', side: 'BUY', entry: 165.00, exit: 158.20, pnlUsd: -340.00, pnlPct: -4.12, exitReason: 'SL_HIT', holdHours: 48, date: '2026-03-11' },
  { symbol: 'NFLX', side: 'BUY', entry: 620.00, exit: 648.50, pnlUsd: 285.00, pnlPct: 4.60, exitReason: 'TP_HIT', holdHours: 72, date: '2026-03-10' },
  { symbol: 'BA', side: 'SELL', entry: 195.00, exit: 188.20, pnlUsd: 340.00, pnlPct: 3.49, exitReason: 'TP_HIT', holdHours: 96, date: '2026-03-09' },
  { symbol: 'DIS', side: 'BUY', entry: 112.00, exit: 108.50, pnlUsd: -175.00, pnlPct: -3.13, exitReason: 'SL_HIT', holdHours: 36, date: '2026-03-08' },
];

const demoBlackoutStats = {
  totalBlackouts: 12,
  tradesAvoided: 8,
  avgBlackoutSwing: 4.2,
  savedFromLoss: 5,
  missedGains: 3,
};

const demoShortStats = {
  totalShorts: 14,
  winRate: 52.3,
  avgReturn: 2.8,
  bestTrade: { symbol: 'BA', pnlPct: 3.49 },
  worstTrade: { symbol: 'GOOGL', pnlPct: -2.45 },
};

const equityCurve = [
  100000, 100200, 100800, 101500, 101200, 102000, 102800, 103500,
  103200, 103800, 104500, 105200, 104800, 105500, 106200, 106800,
  107500, 107200, 108000, 108500, 109200, 109800, 110500, 111200,
  111000, 111800, 112800,
];

// ── Page ───────────────────────────────────────────────────────────────

const teamColorMap: Record<string, string> = {
  emerald: 'bg-emerald-500',
  cyan: 'bg-cyan-500',
  blue: 'bg-blue-500',
  orange: 'bg-orange-500',
  purple: 'bg-purple-500',
  pink: 'bg-pink-500',
};

export default function StockResultsPage() {
  return (
    <div className="slide-up space-y-6">
      <DemoBanner />
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Stock Results</h1>
        <p className="text-sm text-hive-muted mt-1">Performance metrics, team accuracy, and trade history for equities</p>
      </div>

      {/* Key Metrics */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={14} className="text-blue-400" />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Performance Summary</p>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="glass-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Sharpe Ratio</p>
            <p className={`mt-1 text-2xl font-bold tracking-tight ${demoMetrics.sharpe >= 1 ? 'text-emerald-400' : 'text-hive-text'}`}>
              {demoMetrics.sharpe.toFixed(2)}
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Max Drawdown</p>
            <p className="mt-1 text-2xl font-bold tracking-tight text-red-400">
              {demoMetrics.maxDrawdown.toFixed(1)}%
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Win Rate</p>
            <p className={`mt-1 text-2xl font-bold tracking-tight ${demoMetrics.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
              {demoMetrics.winRate.toFixed(1)}%
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Total Return</p>
            <p className={`mt-1 text-2xl font-bold tracking-tight ${demoMetrics.totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              +{demoMetrics.totalReturn.toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Equity Curve */}
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-3">Equity Curve</p>
          <div className="flex items-end gap-[3px] h-32">
            {equityCurve.map((val, i) => {
              const min = Math.min(...equityCurve);
              const max = Math.max(...equityCurve);
              const range = max - min || 1;
              const height = ((val - min) / range) * 100;
              const isPositive = val >= equityCurve[0];
              return (
                <div
                  key={i}
                  className={`flex-1 rounded-t-sm ${isPositive ? 'bg-blue-500/60' : 'bg-red-500/60'}`}
                  style={{ height: `${Math.max(2, height)}%` }}
                  title={`$${val.toLocaleString()}`}
                />
              );
            })}
          </div>
          <div className="flex justify-between mt-2 text-[10px] text-hive-muted">
            <span>Mar 1</span>
            <span>Mar 16</span>
          </div>
        </div>

        {/* Extra stats */}
        <div className="flex items-center gap-6 mt-4 text-xs text-hive-muted">
          <span>{demoMetrics.totalTrades} total trades</span>
          <span>Profit factor: {demoMetrics.profitFactor.toFixed(2)}</span>
          <span>Avg hold: {demoMetrics.avgHoldDays} days</span>
        </div>
      </div>

      {/* Team Accuracy + Trades */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Team Leaderboard */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-2">
            <Trophy size={14} className="text-blue-400" />
            <h2 className="text-sm font-semibold">Team Accuracy</h2>
          </div>
          <div className="divide-y divide-white/[0.03]">
            {demoTeamPerf.map((team, i) => (
              <div key={team.team} className="px-5 py-3 hover:bg-white/[0.02] transition-colors">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold w-5 text-center ${
                      i === 0 ? 'text-amber-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-700' : 'text-hive-muted'
                    }`}>{i + 1}</span>
                    <span className="text-sm font-semibold">{team.team}</span>
                  </div>
                  <span className={`text-sm font-bold ${
                    team.accuracy >= 60 ? 'text-emerald-400' : team.accuracy >= 50 ? 'text-amber-400' : 'text-red-400'
                  }`}>
                    {team.accuracy}%
                    {(() => { const [lo, hi] = wilsonInterval(team.correct, team.total); return <span className="text-[9px] text-hive-muted font-normal ml-1">({Math.round(lo*100)}-{Math.round(hi*100)}%)</span>; })()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${teamColorMap[team.color]}`}
                      style={{ width: `${team.accuracy}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-hive-muted shrink-0">
                    {team.correct}W {team.incorrect}L
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-[10px] text-hive-muted">
                  <span>{team.total} signals</span>
                  <span>wt {team.weight.toFixed(1)}x</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Closed Trades */}
        <div className="lg:col-span-2 glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap size={14} className="text-blue-400" />
              <h2 className="text-sm font-semibold">Recent Closed Trades</h2>
            </div>
            <span className="text-xs text-hive-muted">{demoClosedTrades.length} trades</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
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
              {demoClosedTrades.map((trade, i) => {
                const isWin = trade.pnlUsd > 0;
                return (
                  <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3">
                      <span className="font-semibold text-sm">{trade.symbol}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        trade.side === 'BUY'
                          ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20'
                          : 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20'
                      }`}>{trade.side === 'BUY' ? 'LONG' : 'SHORT'}</span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm">${trade.entry.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-sm">${trade.exit.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${
                        trade.exitReason === 'TP_HIT'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-red-500/10 text-red-400'
                      }`}>{trade.exitReason}</span>
                    </td>
                    <td className={`px-4 py-3 text-right text-sm font-semibold ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
                      {trade.pnlUsd >= 0 ? '+' : ''}${trade.pnlUsd.toLocaleString()}
                      <span className="text-[10px] ml-1 opacity-60">({trade.pnlPct >= 0 ? '+' : ''}{trade.pnlPct.toFixed(1)}%)</span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-hive-muted">
                      {Math.round(trade.holdHours / 24)}d
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Earnings Blackout + Short Selling Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Earnings Blackout Stats */}
        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Calendar size={14} className="text-amber-400" />
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Earnings Blackout Effectiveness</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Total Blackouts</p>
              <p className="text-xl font-bold mt-1">{demoBlackoutStats.totalBlackouts}</p>
            </div>
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Trades Avoided</p>
              <p className="text-xl font-bold mt-1 text-amber-400">{demoBlackoutStats.tradesAvoided}</p>
            </div>
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Avg Earnings Swing</p>
              <p className="text-xl font-bold mt-1">{demoBlackoutStats.avgBlackoutSwing}%</p>
            </div>
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Saved From Loss</p>
              <p className="text-xl font-bold mt-1 text-emerald-400">{demoBlackoutStats.savedFromLoss}</p>
            </div>
          </div>
          <div className="mt-4 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle size={12} className="text-amber-400" />
              <span className="text-xs font-semibold text-amber-400">Blackout Filter Impact</span>
            </div>
            <p className="text-xs text-hive-muted">
              Avoided {demoBlackoutStats.savedFromLoss} potential losses from earnings surprises.
              Missed {demoBlackoutStats.missedGains} positive moves. Net positive expected value.
            </p>
          </div>
        </div>

        {/* Short Selling Performance */}
        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown size={14} className="text-red-400" />
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Short Selling Performance</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Total Shorts</p>
              <p className="text-xl font-bold mt-1">{demoShortStats.totalShorts}</p>
            </div>
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Short Win Rate</p>
              <p className={`text-xl font-bold mt-1 ${demoShortStats.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                {demoShortStats.winRate}%
              </p>
            </div>
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Avg Return</p>
              <p className="text-xl font-bold mt-1 text-emerald-400">+{demoShortStats.avgReturn}%</p>
            </div>
            <div className="glass-card p-3">
              <p className="text-[10px] text-hive-muted">Long Win Rate</p>
              <p className="text-xl font-bold mt-1 text-emerald-400">{demoMetrics.longWinRate}%</p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
              <span className="text-xs text-hive-muted">Best Short</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold">{demoShortStats.bestTrade.symbol}</span>
                <span className="text-xs font-bold text-emerald-400">+{demoShortStats.bestTrade.pnlPct}%</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-red-500/5 border border-red-500/10">
              <span className="text-xs text-hive-muted">Worst Short</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold">{demoShortStats.worstTrade.symbol}</span>
                <span className="text-xs font-bold text-red-400">{demoShortStats.worstTrade.pnlPct}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
