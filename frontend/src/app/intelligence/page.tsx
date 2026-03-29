'use client';

import { useEffect, useState, useMemo } from 'react';
import {
  Shield, Zap, AlertTriangle, Radio, Activity, Eye,
  TrendingUp, TrendingDown, Globe, DollarSign, BarChart3,
  Calendar, Clock, ArrowUpRight, ArrowDownRight, Minus,
  Sun, Moon,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';
import { SEVERITY_COLORS, DRAWDOWN_COLORS } from '@/lib/constants';
import type { FastLoopEvent, PortfolioRisk } from '@/lib/types';

/* ── Demo data ──────────────────────────────────────────────────── */

const YIELD_CURVE = [
  { label: '3M', rate: 5.38, color: 'bg-cyan-500' },
  { label: '2Y', rate: 4.62, color: 'bg-cyan-400' },
  { label: '5Y', rate: 4.21, color: 'bg-violet-400' },
  { label: '10Y', rate: 4.27, color: 'bg-violet-500' },
  { label: '30Y', rate: 4.45, color: 'bg-fuchsia-500' },
];
const SPREAD_2Y10Y = YIELD_CURVE[3].rate - YIELD_CURVE[1].rate; // 10Y - 2Y

function getUpcomingDates() {
  const today = new Date();
  const dates: Date[] = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    dates.push(d);
  }
  return dates;
}

function fmtCalDate(d: Date) {
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function buildEconCalendar() {
  const dates = getUpcomingDates();
  const events: {
    date: string; time: string; event: string;
    consensus: string; previous: string; impact: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  }[] = [];

  // Scatter events across 14 days deterministically
  const templates = [
    { event: 'Non-Farm Payrolls', time: '8:30 AM', consensus: '+185K', previous: '+216K', impact: 'CRITICAL' as const, dayOffset: 1 },
    { event: 'CPI Release (YoY)', time: '8:30 AM', consensus: '2.9%', previous: '3.1%', impact: 'CRITICAL' as const, dayOffset: 4 },
    { event: 'FOMC Rate Decision', time: '2:00 PM', consensus: '5.25-5.50%', previous: '5.25-5.50%', impact: 'HIGH' as const, dayOffset: 6 },
    { event: 'ISM Manufacturing PMI', time: '10:00 AM', consensus: '49.8', previous: '49.2', impact: 'HIGH' as const, dayOffset: 2 },
    { event: 'Retail Sales (MoM)', time: '8:30 AM', consensus: '+0.3%', previous: '+0.6%', impact: 'MEDIUM' as const, dayOffset: 5 },
    { event: 'Initial Jobless Claims', time: '8:30 AM', consensus: '215K', previous: '209K', impact: 'MEDIUM' as const, dayOffset: 3 },
    { event: 'PCE Price Index (YoY)', time: '8:30 AM', consensus: '2.6%', previous: '2.8%', impact: 'HIGH' as const, dayOffset: 8 },
    { event: 'Initial Jobless Claims', time: '8:30 AM', consensus: '218K', previous: '215K', impact: 'MEDIUM' as const, dayOffset: 10 },
    { event: 'Housing Starts', time: '8:30 AM', consensus: '1.46M', previous: '1.42M', impact: 'MEDIUM' as const, dayOffset: 9 },
    { event: 'Consumer Confidence', time: '10:00 AM', consensus: '104.5', previous: '102.0', impact: 'MEDIUM' as const, dayOffset: 7 },
    { event: 'Durable Goods Orders', time: '8:30 AM', consensus: '+1.2%', previous: '-0.8%', impact: 'HIGH' as const, dayOffset: 11 },
    { event: 'GDP (Q4 Second Estimate)', time: '8:30 AM', consensus: '3.3%', previous: '3.2%', impact: 'HIGH' as const, dayOffset: 12 },
  ];

  templates.forEach(t => {
    if (t.dayOffset < dates.length) {
      events.push({
        date: fmtCalDate(dates[t.dayOffset]),
        time: t.time,
        event: t.event,
        consensus: t.consensus,
        previous: t.previous,
        impact: t.impact,
      });
    }
  });

  return events.sort((a, b) => {
    const tA = templates.find(t => t.event === a.event)?.dayOffset ?? 0;
    const tB = templates.find(t => t.event === b.event)?.dayOffset ?? 0;
    return tA - tB;
  });
}

const EARNINGS_DATA = [
  { ticker: 'AAPL', name: 'Apple Inc.', time: 'AMC', expectedMove: '3.8%', history: ['beat', 'beat', 'beat', 'miss'] },
  { ticker: 'MSFT', name: 'Microsoft Corp.', time: 'AMC', expectedMove: '4.2%', history: ['beat', 'beat', 'beat', 'beat'] },
  { ticker: 'NVDA', name: 'NVIDIA Corp.', time: 'AMC', expectedMove: '8.5%', history: ['beat', 'beat', 'beat', 'beat'] },
  { ticker: 'GOOG', name: 'Alphabet Inc.', time: 'AMC', expectedMove: '5.1%', history: ['beat', 'miss', 'beat', 'beat'] },
  { ticker: 'META', name: 'Meta Platforms', time: 'AMC', expectedMove: '6.3%', history: ['beat', 'beat', 'beat', 'beat'] },
  { ticker: 'AMZN', name: 'Amazon.com Inc.', time: 'BMO', expectedMove: '5.7%', history: ['beat', 'beat', 'miss', 'beat'] },
  { ticker: 'JPM', name: 'JPMorgan Chase', time: 'BMO', expectedMove: '2.9%', history: ['beat', 'beat', 'beat', 'beat'] },
  { ticker: 'TSLA', name: 'Tesla Inc.', time: 'AMC', expectedMove: '9.2%', history: ['miss', 'beat', 'miss', 'beat'] },
];

function getEarningsDates() {
  const today = new Date();
  return EARNINGS_DATA.map((e, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() + (i % 7) + 1);
    return { ...e, date: d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) };
  });
}

const IMPACT_BADGE: Record<string, string> = {
  CRITICAL: 'bg-red-500/20 text-red-400 border border-red-500/40',
  HIGH: 'bg-orange-500/20 text-orange-400 border border-orange-500/40',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
};

/* ── Component ──────────────────────────────────────────────────── */

export default function IntelligencePage() {
  const [events, setEvents] = useState<FastLoopEvent[]>([]);
  const [risk, setRisk] = useState<PortfolioRisk | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [filter, setFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/intelligence/events?limit=100`).then(r => r.json()).catch(() => ({ events: [] })),
      fetch(`${API_BASE}/api/v1/portfolio/risk`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/intelligence/status`).then(r => r.json()).catch(() => null),
    ]).then(([evtData, riskData, statusData]) => {
      setEvents(evtData?.events ?? []);
      setRisk(riskData);
      setStatus(statusData);
      setLoading(false);
    });
  }, []);

  const econCalendar = useMemo(() => buildEconCalendar(), []);
  const earningsCalendar = useMemo(() => getEarningsDates(), []);

  const filteredEvents = filter === 'all'
    ? events
    : events.filter(e => e.severity === filter);

  const severityCounts = events.reduce((acc, e) => {
    acc[e.severity] = (acc[e.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const fmtTime = (iso: string) => {
    try { return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }); }
    catch { return ''; }
  };
  const fmtDate = (iso: string) => {
    try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); }
    catch { return ''; }
  };

  if (loading) return (
    <div className="min-h-screen bg-syn-bg flex items-center justify-center">
      <div className="animate-pulse text-syn-muted">Loading intelligence feed...</div>
    </div>
  );

  const maxRate = Math.max(...YIELD_CURVE.map(y => y.rate));

  return (
    <main className="min-h-screen bg-syn-bg text-syn-text py-20 px-4">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Radio size={20} className="text-cyan-400" />
              <h1 className="text-2xl font-bold">Intelligence Network</h1>
            </div>
            <p className="text-sm text-syn-text-secondary">
              15-minute fast loop monitoring news, prices, and portfolio risk between analysis cycles.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-syn-muted">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Fast loop {status?.fast_loop_enabled ? 'active' : 'inactive'} ({status?.interval_minutes ?? 15}min)
          </div>
        </div>

        {/* ════════════════════════════════════════════════════════════
            SECTION 1 — Macro Regime Dashboard
            ════════════════════════════════════════════════════════════ */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5 space-y-5">
          <div className="flex items-center gap-2 mb-1">
            <Globe size={18} className="text-violet-400" />
            <h2 className="text-xs font-bold uppercase tracking-widest text-syn-muted">Macro Regime Dashboard</h2>
          </div>

          {/* Regime pill */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/15 border border-emerald-500/40">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm font-bold text-emerald-400 uppercase tracking-wide">Current Regime: Goldilocks</span>
            </div>
            <p className="text-xs text-syn-text-secondary">
              Moderate growth, declining inflation, stable employment. Ideal environment for risk assets.
            </p>
          </div>

          {/* 4 sub-indicators */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Fed Funds */}
            <div className="bg-syn-bg/60 border border-syn-border rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <DollarSign size={14} className="text-syn-muted" />
                <p className="text-[10px] font-bold uppercase tracking-wider text-syn-muted">Fed Funds Rate</p>
              </div>
              <p className="text-xl font-mono font-bold text-red-400">5.33%</p>
              <p className="text-[10px] text-red-400/80 mt-1 flex items-center gap-1">
                <ArrowUpRight size={10} />
                vs 5.25% market exp. — Hawkish surprise
              </p>
            </div>

            {/* Yield Curve 2Y/10Y */}
            <div className="bg-syn-bg/60 border border-syn-border rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <BarChart3 size={14} className="text-syn-muted" />
                <p className="text-[10px] font-bold uppercase tracking-wider text-syn-muted">Yield Curve 2Y/10Y</p>
              </div>
              <p className="text-xl font-mono font-bold text-emerald-400">+0.35%</p>
              <p className="text-[10px] text-emerald-400/80 mt-1 flex items-center gap-1">
                <TrendingUp size={10} />
                Positive slope — Normal steepening
              </p>
            </div>

            {/* DXY */}
            <div className="bg-syn-bg/60 border border-syn-border rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Globe size={14} className="text-syn-muted" />
                <p className="text-[10px] font-bold uppercase tracking-wider text-syn-muted">DXY (Dollar Index)</p>
              </div>
              <p className="text-xl font-mono font-bold text-syn-text">103.2</p>
              <p className="text-[10px] text-cyan-400/80 mt-1 flex items-center gap-1">
                <ArrowDownRight size={10} />
                -0.8% vs 30-day avg — Weakening
              </p>
            </div>

            {/* Inflation */}
            <div className="bg-syn-bg/60 border border-syn-border rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <TrendingUp size={14} className="text-syn-muted" />
                <p className="text-[10px] font-bold uppercase tracking-wider text-syn-muted">Inflation (CPI YoY)</p>
              </div>
              <p className="text-xl font-mono font-bold text-yellow-400">2.8%</p>
              <p className="text-[10px] text-yellow-400/80 mt-1 flex items-center gap-1">
                <Minus size={10} />
                Target 2.0% — Above target
              </p>
            </div>
          </div>

          {/* Regime Impact */}
          <div className="bg-violet-500/10 border border-violet-500/30 rounded-lg px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-violet-400 mb-1">Regime Impact</p>
            <p className="text-xs text-syn-text-secondary">
              In Goldilocks: Tech/Growth outperform, Small-caps rally, REITs benefit. Risk-on positioning favored with moderate leverage.
            </p>
          </div>
        </div>

        {/* ════════════════════════════════════════════════════════════
            SECTION 2 — Economic Calendar (next 14 days)
            ════════════════════════════════════════════════════════════ */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Calendar size={18} className="text-cyan-400" />
            <h2 className="text-xs font-bold uppercase tracking-widest text-syn-muted">Economic Calendar — Next 14 Days</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-syn-border text-left">
                  <th className="pb-2 pr-3 text-[10px] font-bold uppercase tracking-wider text-syn-muted">Date</th>
                  <th className="pb-2 pr-3 text-[10px] font-bold uppercase tracking-wider text-syn-muted">Time (ET)</th>
                  <th className="pb-2 pr-3 text-[10px] font-bold uppercase tracking-wider text-syn-muted">Event</th>
                  <th className="pb-2 pr-3 text-[10px] font-bold uppercase tracking-wider text-syn-muted">Consensus</th>
                  <th className="pb-2 pr-3 text-[10px] font-bold uppercase tracking-wider text-syn-muted">Previous</th>
                  <th className="pb-2 text-[10px] font-bold uppercase tracking-wider text-syn-muted">Impact</th>
                </tr>
              </thead>
              <tbody>
                {econCalendar.map((row, i) => (
                  <tr key={i} className="border-b border-syn-border/50 hover:bg-syn-bg/40 transition">
                    <td className="py-2.5 pr-3 text-syn-text-secondary whitespace-nowrap">{row.date}</td>
                    <td className="py-2.5 pr-3 font-mono text-syn-muted whitespace-nowrap">{row.time}</td>
                    <td className="py-2.5 pr-3 text-syn-text font-medium">{row.event}</td>
                    <td className="py-2.5 pr-3 font-mono text-syn-text">{row.consensus}</td>
                    <td className="py-2.5 pr-3 font-mono text-syn-muted">{row.previous}</td>
                    <td className="py-2.5">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${IMPACT_BADGE[row.impact]}`}>
                        {row.impact}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ════════════════════════════════════════════════════════════
            SECTION 3 — Earnings Calendar (next 7 days)
            ════════════════════════════════════════════════════════════ */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={18} className="text-amber-400" />
            <h2 className="text-xs font-bold uppercase tracking-widest text-syn-muted">Earnings Calendar — Next 7 Days</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {earningsCalendar.map((e) => (
              <div key={e.ticker} className="bg-syn-bg/60 border border-syn-border rounded-lg p-3 hover:border-syn-accent/40 transition">
                {/* Header row */}
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-sm font-bold font-mono text-syn-text">{e.ticker}</span>
                    <p className="text-[10px] text-syn-muted truncate max-w-[120px]">{e.name}</p>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    e.time === 'BMO'
                      ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      : 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'
                  }`}>
                    {e.time === 'BMO' ? (
                      <span className="flex items-center gap-1"><Sun size={10} /> BMO</span>
                    ) : (
                      <span className="flex items-center gap-1"><Moon size={10} /> AMC</span>
                    )}
                  </span>
                </div>

                {/* Date */}
                <p className="text-[10px] text-syn-text-secondary mb-2 flex items-center gap-1">
                  <Clock size={10} /> {e.date}
                </p>

                {/* Expected move */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] text-syn-muted">Expected Move</span>
                  <span className="text-xs font-mono font-bold text-cyan-400">&plusmn;{e.expectedMove}</span>
                </div>

                {/* Surprise history */}
                <div>
                  <p className="text-[10px] text-syn-muted mb-1">Last 4 Quarters</p>
                  <div className="flex gap-1">
                    {e.history.map((h, qi) => (
                      <span
                        key={qi}
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          h === 'beat'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {h === 'beat' ? 'BEAT' : 'MISS'}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ════════════════════════════════════════════════════════════
            SECTION 4 — Yield Curve Visualization
            ════════════════════════════════════════════════════════════ */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp size={18} className="text-fuchsia-400" />
              <h2 className="text-xs font-bold uppercase tracking-widest text-syn-muted">US Treasury Yield Curve</h2>
            </div>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${
              SPREAD_2Y10Y >= 0
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40'
                : 'bg-red-500/15 text-red-400 border border-red-500/40'
            }`}>
              2Y/10Y Spread: {SPREAD_2Y10Y >= 0 ? '+' : ''}{SPREAD_2Y10Y.toFixed(2)}%
              {SPREAD_2Y10Y >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            </div>
          </div>

          {/* Bar chart */}
          <div className="flex items-end justify-around gap-3 h-48 mb-4 px-4">
            {YIELD_CURVE.map((y) => {
              const pct = (y.rate / (maxRate + 0.5)) * 100;
              return (
                <div key={y.label} className="flex flex-col items-center gap-1 flex-1">
                  <span className="text-xs font-mono font-bold text-syn-text">{y.rate.toFixed(2)}%</span>
                  <div
                    className={`w-full max-w-[48px] rounded-t-md ${y.color} transition-all`}
                    style={{ height: `${pct}%`, minHeight: '8px' }}
                  />
                  <span className="text-[10px] font-bold text-syn-muted">{y.label}</span>
                </div>
              );
            })}
          </div>

          {/* Status row */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-3 border-t border-syn-border">
            <div className={`flex items-center gap-2 text-xs font-bold ${
              SPREAD_2Y10Y >= 0 ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {SPREAD_2Y10Y >= 0 ? (
                <><TrendingUp size={14} /> Normal (Positive Slope)</>
              ) : (
                <><TrendingDown size={14} /> Inverted (Recession Signal)</>
              )}
            </div>
            <p className="text-[10px] text-syn-muted">
              The 2Y/10Y spread has inverted before <span className="text-syn-text font-bold">every</span> US recession since 1955.
              A positive spread indicates normal growth expectations.
            </p>
          </div>
        </div>

        {/* ════════════════════════════════════════════════════════════
            EXISTING — Risk Dashboard
            ════════════════════════════════════════════════════════════ */}
        {risk && (
          <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
            <h2 className="text-xs font-bold uppercase tracking-widest text-syn-muted mb-4">Portfolio Risk Status</h2>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              {/* Drawdown Level */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Drawdown Level</p>
                <div className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${
                  DRAWDOWN_COLORS[risk.drawdown_level]?.bg ?? 'bg-syn-surface'
                } ${DRAWDOWN_COLORS[risk.drawdown_level]?.color ?? ''}`}>
                  {DRAWDOWN_COLORS[risk.drawdown_level]?.label ?? risk.drawdown_level}
                </div>
                <p className="text-[10px] text-syn-muted mt-1">{risk.drawdown_pct.toFixed(2)}% from peak</p>
              </div>

              {/* Heat */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Portfolio Heat</p>
                <p className={`text-xl font-mono font-bold ${
                  risk.heat_exceeded ? 'text-red-400' : risk.portfolio_heat > 5 ? 'text-amber-400' : 'text-emerald-400'
                }`}>{risk.portfolio_heat.toFixed(1)}%</p>
                <p className="text-[10px] text-syn-muted">of 7% limit</p>
              </div>

              {/* Correlation */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Avg Correlation</p>
                <p className={`text-xl font-mono font-bold ${
                  risk.avg_correlation > 0.7 ? 'text-red-400' : risk.avg_correlation > 0.5 ? 'text-amber-400' : 'text-emerald-400'
                }`}>{risk.avg_correlation.toFixed(2)}</p>
                <p className="text-[10px] text-syn-muted">{risk.correlation_warning ? 'Warning!' : 'Normal'}</p>
              </div>

              {/* Exposure */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Gross Exposure</p>
                <p className="text-xl font-mono font-bold text-syn-text">{risk.gross_exposure.toFixed(0)}%</p>
                <p className="text-[10px] text-syn-muted">Net: {risk.net_exposure.toFixed(0)}%</p>
              </div>

              {/* Trading Status */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Trading</p>
                <p className={`text-xl font-bold ${risk.trading_allowed ? 'text-emerald-400' : 'text-red-500'}`}>
                  {risk.trading_allowed ? 'ACTIVE' : 'HALTED'}
                </p>
                <p className="text-[10px] text-syn-muted">Size: {(risk.size_multiplier * 100).toFixed(0)}%</p>
              </div>
            </div>

            {risk.actions.length > 0 && (
              <div className="mt-3 pt-3 border-t border-syn-border">
                {risk.actions.map((a, i) => (
                  <p key={i} className="text-xs text-orange-400 font-mono flex items-center gap-1.5 mb-1">
                    <AlertTriangle size={12} /> {a}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Event Stats + Filter */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`text-xs px-3 py-1.5 rounded-full border transition ${
              filter === 'all' ? 'bg-syn-accent/20 border-syn-accent text-syn-accent' : 'border-syn-border text-syn-muted hover:text-syn-text'
            }`}
          >All ({events.length})</button>
          {(['critical', 'high', 'medium', 'low'] as const).map(sev => (
            <button
              key={sev}
              onClick={() => setFilter(sev)}
              className={`text-xs px-3 py-1.5 rounded-full border transition ${
                filter === sev ? `${SEVERITY_COLORS[sev]} border-current` : 'border-syn-border text-syn-muted hover:text-syn-text'
              }`}
            >{sev} ({severityCounts[sev] ?? 0})</button>
          ))}
        </div>

        {/* Event Feed */}
        <div className="space-y-2">
          {filteredEvents.length === 0 ? (
            <div className="bg-syn-surface border border-syn-border rounded-xl p-8 text-center">
              <Eye size={24} className="mx-auto text-syn-muted mb-2" />
              <p className="text-sm text-syn-muted">No intelligence events yet. The fast loop will populate this feed.</p>
            </div>
          ) : (
            filteredEvents.map((evt, i) => (
              <div
                key={i}
                className={`bg-syn-surface border border-syn-border rounded-lg p-3 flex items-start gap-3 ${
                  evt.acted_upon ? 'border-l-2 border-l-orange-400' : ''
                }`}
              >
                <div className={`mt-0.5 shrink-0 ${SEVERITY_COLORS[evt.severity] ?? 'text-syn-muted'}`}>
                  {evt.severity === 'critical' ? <AlertTriangle size={16} /> :
                    evt.severity === 'high' ? <Zap size={16} /> :
                      evt.event_type === 'risk_action' ? <Shield size={16} /> :
                        <Activity size={16} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${SEVERITY_COLORS[evt.severity] ?? ''}`}>
                      {evt.severity}
                    </span>
                    <span className="text-[10px] text-syn-muted font-mono">{evt.event_type.replace(/_/g, ' ')}</span>
                    <span className="text-[10px] text-syn-text-tertiary">{evt.source}</span>
                    {evt.acted_upon && (
                      <span className="text-[10px] font-bold text-orange-400">ACTION TAKEN</span>
                    )}
                  </div>
                  <p className="text-sm text-syn-text mt-1 break-words">{evt.title}</p>
                  {evt.symbols.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {evt.symbols.map(s => (
                        <span key={s} className="text-[10px] font-mono bg-syn-bg px-1.5 py-0.5 rounded text-syn-muted">
                          {s.replace('USDT', '')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[10px] text-syn-text-tertiary">{fmtTime(evt.timestamp)}</p>
                  <p className="text-[10px] text-syn-muted">{fmtDate(evt.timestamp)}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </main>
  );
}
