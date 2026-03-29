
'use client';

import {
  TrendingUp, TrendingDown, DollarSign, BarChart3, Activity,
  Calendar, ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react';
import { DemoBanner } from '@/components/DemoBanner';
import LineChart from '@/components/LineChart';

// ── Demo P&L Data ──

const portfolioValue = 104_287;
const startingCapital = 100_000;
const totalReturn = ((portfolioValue - startingCapital) / startingCapital) * 100;
const realizedPnl = 3_142;
const unrealizedPnl = 1_145;
const totalPnl = realizedPnl + unrealizedPnl;
const peakValue = 106_800;
const drawdownPct = ((peakValue - portfolioValue) / peakValue) * 100;

const dailyPnl = [
  { date: 'Mar 10', pnl: 420, cumulative: 100_420 },
  { date: 'Mar 11', pnl: -180, cumulative: 100_240 },
  { date: 'Mar 12', pnl: 890, cumulative: 101_130 },
  { date: 'Mar 13', pnl: -310, cumulative: 100_820 },
  { date: 'Mar 14', pnl: 1_250, cumulative: 102_070 },
  { date: 'Mar 15', pnl: 680, cumulative: 102_750 },
  { date: 'Mar 16', pnl: -420, cumulative: 102_330 },
  { date: 'Mar 17', pnl: 1_957, cumulative: 104_287 },
];

const weeklyPnl = [
  { week: 'W10 (Mar 3-7)', pnl: 1_820, trades: 6, winRate: 67 },
  { week: 'W11 (Mar 10-14)', pnl: 2_070, trades: 8, winRate: 63 },
  { week: 'W12 (Mar 15-17)', pnl: 2_217, trades: 4, winRate: 75 },
];

const tradeAttribution = [
  { team: 'Technical', pnl: 1_680, trades: 8, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  { team: 'Fundamental', pnl: 1_240, trades: 6, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { team: 'News', pnl: 890, trades: 5, color: 'text-pink-400', bg: 'bg-pink-500/10' },
  { team: 'Institutional', pnl: 420, trades: 4, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  { team: 'Macro', pnl: -180, trades: 3, color: 'text-orange-400', bg: 'bg-orange-500/10' },
  { team: 'Sentiment', pnl: -763, trades: 5, color: 'text-purple-400', bg: 'bg-purple-500/10' },
];

const closedTrades = [
  { symbol: 'NVDA', side: 'BUY', entry: 875, exit: 912, pnl: 444, pnlPct: 4.23, reason: 'TP1', team: 'Technical', conviction: 8 },
  { symbol: 'GOOGL', side: 'BUY', entry: 172, exit: 178, pnl: 300, pnlPct: 3.49, reason: 'TRAILING', team: 'Fundamental', conviction: 7 },
  { symbol: 'META', side: 'BUY', entry: 502, exit: 518, pnl: 320, pnlPct: 3.19, reason: 'TP1', team: 'News', conviction: 8 },
  { symbol: 'JPM', side: 'BUY', entry: 198, exit: 205, pnl: 210, pnlPct: 3.54, reason: 'TP2', team: 'Institutional', conviction: 7 },
  { symbol: 'AMZN', side: 'SHORT', entry: 185, exit: 188, pnl: -180, pnlPct: -1.62, reason: 'SL', team: 'Sentiment', conviction: 5 },
  { symbol: 'AMD', side: 'BUY', entry: 165, exit: 161, pnl: -320, pnlPct: -2.42, reason: 'SL', team: 'Technical', conviction: 6 },
];

function PnlBadge({ value }: { value: number }) {
  if (value > 0) return <span className="text-emerald-400 flex items-center gap-0.5"><ArrowUpRight size={12} />${value.toLocaleString()}</span>;
  if (value < 0) return <span className="text-red-400 flex items-center gap-0.5"><ArrowDownRight size={12} />${Math.abs(value).toLocaleString()}</span>;
  return <span className="text-hive-muted flex items-center gap-0.5"><Minus size={12} />$0</span>;
}

export default function PnLPage() {
  const maxAbsPnl = Math.max(...dailyPnl.map(d => Math.abs(d.pnl)));

  return (
    <div className="slide-up space-y-6">
      <DemoBanner />
      <div>
        <h1 className="text-2xl font-bold tracking-tight">P&L Dashboard</h1>
        <p className="text-sm text-hive-muted mt-1">Profit & loss breakdown — daily, weekly, by team</p>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Portfolio Value', value: `$${portfolioValue.toLocaleString()}`, color: 'text-hive-text', icon: DollarSign },
          { label: 'Total P&L', value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toLocaleString()}`, color: totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400', icon: TrendingUp },
          { label: 'Realized', value: `+$${realizedPnl.toLocaleString()}`, color: 'text-emerald-400', icon: BarChart3 },
          { label: 'Unrealized', value: `+$${unrealizedPnl.toLocaleString()}`, color: 'text-blue-400', icon: Activity },
          { label: 'Drawdown', value: `-${drawdownPct.toFixed(1)}%`, color: 'text-red-400', icon: TrendingDown },
        ].map((stat) => (
          <div key={stat.label} className="glass-card p-4">
            <div className="flex items-center gap-1.5 mb-1">
              <stat.icon size={11} className="text-hive-muted/40" />
              <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">{stat.label}</p>
            </div>
            <p className={`text-xl font-bold tracking-tight ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Daily P&L Bar Chart + Equity Curve */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4">Daily P&L</p>
          <div className="space-y-2">
            {dailyPnl.map((d) => {
              const width = (Math.abs(d.pnl) / maxAbsPnl) * 100;
              const isPositive = d.pnl >= 0;
              return (
                <div key={d.date} className="flex items-center gap-3">
                  <span className="text-[10px] text-hive-muted w-12 shrink-0">{d.date}</span>
                  <div className="flex-1 flex items-center">
                    {isPositive ? (
                      <div className="flex items-center w-full">
                        <div className="w-1/2" />
                        <div className="w-1/2">
                          <div className="h-5 bg-emerald-500/30 rounded-r" style={{ width: `${width}%` }} />
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center w-full">
                        <div className="w-1/2 flex justify-end">
                          <div className="h-5 bg-red-500/30 rounded-l" style={{ width: `${width}%` }} />
                        </div>
                        <div className="w-1/2" />
                      </div>
                    )}
                  </div>
                  <span className={`text-xs font-bold w-16 text-right ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                    {isPositive ? '+' : ''}${d.pnl.toLocaleString()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Equity Curve vs SPY</p>
            <div className="flex items-center gap-3 text-[9px]">
              <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-emerald-500 rounded" /> Strategy</span>
              <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-hive-muted rounded opacity-50" style={{ borderTop: '1px dashed' }} /> SPY</span>
            </div>
          </div>
          <LineChart
            data={dailyPnl.map(d => d.cumulative)}
            benchmarkData={[100_000, 100_180, 100_520, 100_340, 100_890, 101_200, 101_050, 102_450]}
            labels={dailyPnl.map(d => d.date)}
            startValue={startingCapital}
            height={160}
          />
          <div className="flex items-center justify-between mt-2 text-[10px]">
            <span className="text-hive-muted">{dailyPnl[0].date}</span>
            <span className="text-emerald-400 font-bold">Strategy +{totalReturn.toFixed(2)}% · Alpha +1.83%</span>
            <span className="text-hive-muted">{dailyPnl[dailyPnl.length - 1].date}</span>
          </div>
        </div>
      </div>

      {/* Weekly Summary + Team Attribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Weekly */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-3 border-b border-white/[0.06]">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted flex items-center gap-1.5">
              <Calendar size={11} /> Weekly Summary
            </p>
          </div>
          <div className="divide-y divide-white/[0.03]">
            {weeklyPnl.map((w) => (
              <div key={w.week} className="px-5 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium">{w.week}</span>
                  <PnlBadge value={w.pnl} />
                </div>
                <div className="flex items-center gap-3 text-[10px] text-hive-muted">
                  <span>{w.trades} trades</span>
                  <span>{w.winRate}% win rate</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Team Attribution */}
        <div className="lg:col-span-2 glass-card overflow-hidden">
          <div className="px-5 py-3 border-b border-white/[0.06]">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">P&L by Team (Alpha Attribution)</p>
          </div>
          <div className="divide-y divide-white/[0.03]">
            {tradeAttribution.map((t) => {
              const maxTeamPnl = Math.max(...tradeAttribution.map(x => Math.abs(x.pnl)));
              const barWidth = (Math.abs(t.pnl) / maxTeamPnl) * 100;
              return (
                <div key={t.team} className="px-5 py-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${t.color}`}>{t.team}</span>
                      <span className="text-[10px] text-hive-muted">{t.trades} trades</span>
                    </div>
                    <span className={`text-sm font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {t.pnl >= 0 ? '+' : ''}${t.pnl.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${t.pnl >= 0 ? 'bg-emerald-500/60' : 'bg-red-500/60'}`} style={{ width: `${barWidth}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recent Closed Trades with Full Context */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-white/[0.06]">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Trade History (with signal context)</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
                <th className="text-left px-4 py-2.5">Symbol</th>
                <th className="text-left px-4 py-2.5">Side</th>
                <th className="text-right px-4 py-2.5">Entry</th>
                <th className="text-right px-4 py-2.5">Exit</th>
                <th className="text-left px-4 py-2.5">Reason</th>
                <th className="text-left px-4 py-2.5">Lead Team</th>
                <th className="text-center px-4 py-2.5">Conv.</th>
                <th className="text-right px-4 py-2.5">P&L</th>
              </tr>
            </thead>
            <tbody>
              {closedTrades.map((t, i) => (
                <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 font-semibold text-sm">{t.symbol}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
                      t.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20' : 'bg-red-500/10 text-red-400 ring-red-500/20'
                    }`}>{t.side === 'BUY' ? 'LONG' : 'SHORT'}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-hive-muted">${t.entry}</td>
                  <td className="px-4 py-3 text-right text-sm">${t.exit}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      t.reason === 'SL' ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'
                    }`}>{t.reason}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-hive-muted">{t.team}</td>
                  <td className="px-4 py-3 text-center text-xs">{t.conviction}/10</td>
                  <td className={`px-4 py-3 text-right text-sm font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {t.pnl >= 0 ? '+' : ''}${t.pnl} <span className="text-[10px] opacity-60">({t.pnlPct >= 0 ? '+' : ''}{t.pnlPct}%)</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
