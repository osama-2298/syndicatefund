'use client';

import { useEffect, useState, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import {
  TrendingUp, TrendingDown, Shield, Activity, ArrowRight,
  ChevronRight, ChevronDown, ChevronUp, Zap, Swords,
  Target, BarChart3, Clock, Globe, DollarSign, Gauge,
  ArrowUpRight, ArrowDownRight, Timer, Layers, Coins,
} from 'lucide-react';
import CycleCard, { type CycleData, type PipelineEvent } from '@/components/CycleCard';
import { AGENT_COLORS, DRAWDOWN_COLORS } from '@/lib/constants';
import { API_BASE } from '@/lib/api';
import type { PortfolioRisk } from '@/lib/types';

// Lazy-load Recharts (no SSR)
const AreaChart = dynamic(() => import('recharts').then(m => m.AreaChart), { ssr: false });
const Area = dynamic(() => import('recharts').then(m => m.Area), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(m => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(m => m.YAxis), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(m => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import('recharts').then(m => m.ResponsiveContainer), { ssr: false });

/* ── Types ── */

interface Position { symbol: string; side: string; entry_price: number; quantity: number; current_price: number; }
interface TradeEntry { symbol: string; side: string; entry_price: number; exit_price: number; stop_loss: number; take_profit_1: number; conviction: number; confidence: number; risk_amount: number; exit_reason: string; asset_tier: string; pnl_pct: number; pnl_usd: number; holding_hours: number; exit_time: string; entry_time: string; }
interface TradeStats { total_trades: number; closed_trades: number; open_trades: number; wins: number; losses: number; win_rate: number; total_pnl_usd: number; avg_pnl_pct: number; profit_factor: number; current_streak: number; best_trade: { symbol: string; pnl_pct: number; pnl_usd: number; reason: string } | null; worst_trade: { symbol: string; pnl_pct: number; pnl_usd: number; reason: string } | null; }
interface AgentData { id: string; team_name: string | null; role: string; agent_class: string | null; status: string; total_signals: number; accuracy: number; provider: string; }
interface CyclePoint { id: number; date: string; value: number; regime: string | null; }

/* ── Animated Number ── */

function AnimatedNumber({ value, prefix = '$', decimals = 0 }: { value: number; prefix?: string; decimals?: number }) {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);

  useEffect(() => {
    const start = prevRef.current;
    prevRef.current = value;
    const startTime = performance.now();
    const duration = 800;
    let raf: number;
    const animate = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(start + (value - start) * eased);
      if (progress < 1) raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return (
    <span className="tabular-nums font-mono">
      {prefix}{display.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
    </span>
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
    STOP_LOSS: 'Stop Loss', TAKE_PROFIT_1: 'TP1', TAKE_PROFIT_2: 'TP2',
    TRAILING_STOP: 'Trail', BREAKEVEN_STOP: 'BE Stop', TIME_STOP: 'Time',
  };
  return map[reason] || reason;
}

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/* ── Equity Curve Chart ── */

function EquityCurve({ data }: { data: CyclePoint[] }) {
  if (data.length < 2) return null;

  const minVal = Math.min(...data.map(d => d.value));
  const maxVal = Math.max(...data.map(d => d.value));
  const isUp = data[data.length - 1].value >= data[0].value;
  const gradientColor = isUp ? '#34d399' : '#f87171';

  return (
    <div className="bg-syn-surface border border-syn-border rounded-xl p-4 pb-2 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-syn-muted" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Portfolio Performance</span>
        </div>
        <span className="text-[10px] font-mono text-syn-text-tertiary">{data.length} cycles</span>
      </div>
      <div className="h-[200px] -mx-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={gradientColor} stopOpacity={0.25} />
                <stop offset="100%" stopColor={gradientColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.2)' }}
              minTickGap={60}
            />
            <YAxis
              domain={[minVal * 0.998, maxVal * 1.002]}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.2)' }}
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
              width={52}
            />
            <Tooltip
              contentStyle={{
                background: 'rgba(15,15,20,0.95)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '8px',
                fontSize: '11px',
                padding: '8px 12px',
              }}
              labelStyle={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', marginBottom: '4px' }}
              formatter={(value: any) => [`$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`, 'NAV']}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={gradientColor}
              strokeWidth={1.5}
              fill="url(#equityGrad)"
              dot={false}
              activeDot={{ r: 3, strokeWidth: 0, fill: gradientColor }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ── Sidebar: Recent Activity ── */

function ActivityFeed({ trades }: { trades: TradeEntry[] }) {
  // Merge open and closed trades, sort by most recent activity
  const activities = useMemo(() => {
    const items: { type: 'open' | 'close'; symbol: string; side: string; time: string; pnlPct?: number; reason?: string }[] = [];
    for (const t of trades) {
      if (t.entry_time) {
        items.push({ type: 'open', symbol: t.symbol, side: t.side, time: t.entry_time });
      }
      if (t.exit_reason && t.exit_reason !== 'OPEN' && t.exit_time) {
        items.push({ type: 'close', symbol: t.symbol, side: t.side, time: t.exit_time, pnlPct: (t.pnl_pct ?? 0) * 100, reason: t.exit_reason });
      }
    }
    return items.sort((a, b) => b.time.localeCompare(a.time)).slice(0, 8);
  }, [trades]);

  if (activities.length === 0) return null;

  return (
    <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Recent Activity</h3>
        <a href="/activity" className="text-[10px] text-syn-muted hover:text-syn-accent transition-colors flex items-center gap-0.5">
          All <ChevronRight size={10} />
        </a>
      </div>
      <div className="space-y-1.5">
        {activities.map((act, i) => {
          const base = act.symbol.replace('USDT', '');
          const isClose = act.type === 'close';
          const isWin = (act.pnlPct ?? 0) > 0;
          return (
            <div key={i} className="flex items-center gap-2 py-1">
              <div className={`w-1 h-1 rounded-full shrink-0 ${
                isClose ? (isWin ? 'bg-emerald-400' : 'bg-red-400') : 'bg-syn-accent'
              }`} />
              <div className="flex-1 min-w-0">
                <span className="text-[11px] font-medium">
                  {isClose ? 'Closed' : 'Opened'}{' '}
                  <span className={act.side === 'BUY' ? 'text-emerald-400' : 'text-red-400'}>
                    {act.side === 'BUY' ? 'LONG' : 'SHORT'}
                  </span>{' '}
                  <span className="font-semibold">{base}</span>
                </span>
                {isClose && act.pnlPct !== undefined && (
                  <span className={`text-[10px] ml-1 font-mono ${isWin ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
                    {fmtPct(act.pnlPct)}
                  </span>
                )}
              </div>
              <span className="text-[10px] text-syn-text-tertiary shrink-0">{timeAgo(act.time)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Sidebar: Performance Snapshot ── */

function PerformanceSnapshot({ stats, closedTrades }: { stats: TradeStats | null; closedTrades: TradeEntry[] }) {
  const winRate = stats?.win_rate ?? (closedTrades.length > 0
    ? Math.round(closedTrades.filter(t => (t.pnl_usd ?? 0) > 0).length / closedTrades.length * 100)
    : 0);
  const wins = stats?.wins ?? closedTrades.filter(t => (t.pnl_usd ?? 0) > 0).length;
  const losses = stats?.losses ?? closedTrades.filter(t => (t.pnl_usd ?? 0) <= 0).length;
  const streak = stats?.current_streak ?? 0;

  if (closedTrades.length === 0) return null;

  return (
    <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Performance</h3>
        <a href="/results" className="text-[10px] text-syn-muted hover:text-syn-accent transition-colors flex items-center gap-0.5">
          Details <ChevronRight size={10} />
        </a>
      </div>
      {/* Win rate bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium">Win Rate</span>
          <span className={`text-sm font-bold font-mono ${winRate >= 55 ? 'text-emerald-400' : winRate >= 45 ? 'text-amber-400' : 'text-red-400'}`}>
            {winRate}%
          </span>
        </div>
        <div className="h-2 rounded-full bg-white/[0.04] overflow-hidden flex">
          {wins > 0 && (
            <div
              className="h-full bg-emerald-500 rounded-l-full transition-all"
              style={{ width: `${(wins / (wins + losses)) * 100}%` }}
            />
          )}
          {losses > 0 && (
            <div
              className="h-full bg-red-500/60 rounded-r-full transition-all"
              style={{ width: `${(losses / (wins + losses)) * 100}%` }}
            />
          )}
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-emerald-400/50">{wins}W</span>
          <span className="text-[10px] text-red-400/50">{losses}L</span>
        </div>
      </div>
      {/* Stat rows */}
      <div className="space-y-2 border-t border-syn-border pt-2">
        {stats?.profit_factor != null && (
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-syn-text-tertiary">Profit Factor</span>
            <span className={`text-[11px] font-mono font-semibold ${stats.profit_factor > 1 ? 'text-emerald-400' : 'text-red-400'}`}>
              {stats.profit_factor.toFixed(2)}
            </span>
          </div>
        )}
        {streak !== 0 && (
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-syn-text-tertiary">Streak</span>
            <span className={`text-[11px] font-mono font-semibold ${streak > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {streak > 0 ? '+' : ''}{streak}
            </span>
          </div>
        )}
        {stats?.best_trade && (
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-syn-text-tertiary">Best Trade</span>
            <span className="text-[11px] font-mono text-emerald-400">
              {stats.best_trade.symbol.replace('USDT', '')} +{stats.best_trade.pnl_pct}%
            </span>
          </div>
        )}
        {stats?.worst_trade && (
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-syn-text-tertiary">Worst Trade</span>
            <span className="text-[11px] font-mono text-red-400">
              {stats.worst_trade.symbol.replace('USDT', '')} {stats.worst_trade.pnl_pct}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Sidebar: Disagreement Card ── */

function DisagreementSidebar() {
  const [events, setEvents] = useState<any[]>([]);
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/events?event_type=disagreement&limit=5`)
      .then(r => r.json())
      .then(data => setEvents(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  if (events.length === 0) return null;

  return (
    <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Recent Clashes</h3>
        <a href="/disagreements" className="text-[10px] text-syn-muted hover:text-syn-accent transition-colors flex items-center gap-0.5">
          All <ChevronRight size={10} />
        </a>
      </div>
      <div className="space-y-2">
        {events.slice(0, 3).map((event: any) => {
          const d = event.detail || {};
          const base = (d.symbol || '').replace('USDT', '');
          const pol = Math.round((d.polarization || 0) * 100);
          return (
            <div key={event.id} className="flex items-center gap-2 py-1.5">
              <Swords size={10} className="text-red-400 shrink-0" />
              <span className="text-xs font-semibold flex-1 truncate">{base}</span>
              <span className="text-[10px] text-red-400 font-medium">{pol}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Sidebar: Leaderboard Card ── */

function LeaderboardSidebar({ agents }: { agents: AgentData[] }) {
  const topAgents = [...agents].sort((a, b) => b.total_signals - a.total_signals).slice(0, 5);
  if (topAgents.length === 0) return null;

  return (
    <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Agent Leaderboard</h3>
        <a href="/agents" className="text-[10px] text-syn-muted hover:text-syn-accent transition-colors flex items-center gap-0.5">
          All <ChevronRight size={10} />
        </a>
      </div>
      <div className="space-y-2">
        {topAgents.map((agent, i) => {
          const agentClass = agent.agent_class ?? '';
          const gradient = AGENT_COLORS[agentClass] ?? 'from-white/20 to-white/10';
          const initial = agentClass.charAt(0) || agent.id.charAt(0).toUpperCase();
          const maxSignals = Math.max(...topAgents.map(a => a.total_signals), 1);
          return (
            <div key={agent.id} className="flex items-center gap-2.5 py-1.5 group">
              <span className="text-[10px] font-mono text-syn-text-tertiary w-3 text-right">{i + 1}</span>
              <div className={`w-7 h-7 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center shrink-0`}>
                <span className="text-[10px] font-bold text-white/90">{initial}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-syn-text truncate max-w-[120px]">
                    {agentClass.replace('Agent', '')}
                  </span>
                  <span className="text-[10px] font-mono tabular-nums text-syn-text-tertiary">
                    {agent.total_signals}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-[10px] text-syn-text-tertiary capitalize">{agent.team_name ?? 'unassigned'}</span>
                  {agent.accuracy > 0 && (
                    <span className="text-[10px] font-mono text-emerald-400/50">{(agent.accuracy * 100).toFixed(0)}%</span>
                  )}
                </div>
                <div className="mt-1 h-[2px] rounded-full bg-white/[0.04] overflow-hidden">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all duration-500`}
                    style={{ width: `${(agent.total_signals / maxSignals) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   ██  DASHBOARD
   ══════════════════════════════════════════ */

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [portfolioRisk, setPortfolioRisk] = useState<PortfolioRisk | null>(null);
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [allCycles, setAllCycles] = useState<CyclePoint[]>([]);
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [trades, setTrades] = useState<TradeEntry[]>([]);
  const [tradeStats, setTradeStats] = useState<TradeStats | null>(null);
  const [eventsByCycle, setEventsByCycle] = useState<Record<number, PipelineEvent[]>>({});
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const [priceFlash, setPriceFlash] = useState<Record<string, 'up' | 'down' | ''>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showAllClosed, setShowAllClosed] = useState(false);
  const livePricesRef = useRef<Record<string, number>>({});

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/portfolio`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/cycles?limit=3`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/agents`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/portfolio/trades`).then(r => r.json()).catch(() => ({ trades: [], stats: null })),
      fetch(`${API_BASE}/api/v1/events?limit=200`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/cycles?limit=500`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/portfolio/risk`).then(r => r.json()).catch(() => null),
    ]).then(([p, c, a, tr, evts, allC, riskData]) => {
      if (riskData) setPortfolioRisk(riskData);
      setPortfolio(p);
      setCycles(c);
      setAgents(a);
      setTrades(Array.isArray(tr) ? tr : (tr?.trades ?? []));
      if (tr?.stats && Object.keys(tr.stats).length > 0) {
        setTradeStats(tr.stats);
      }

      // Build equity curve from all cycles
      const cycleArr = Array.isArray(allC) ? allC : [];
      const points: CyclePoint[] = cycleArr
        .filter((cyc: any) => cyc.portfolio_value != null)
        .map((cyc: any) => ({
          id: cyc.id,
          date: cyc.completed_at
            ? new Date(cyc.completed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            : '',
          value: cyc.portfolio_value,
          regime: cyc.regime,
        }))
        .reverse(); // oldest first
      setAllCycles(points);

      // Group events by cycle
      const grouped: Record<number, PipelineEvent[]> = {};
      const ungrouped: PipelineEvent[] = [];
      const events = Array.isArray(evts) ? evts : [];
      for (const event of events) {
        const cid = event.cycle_id;
        if (cid != null) {
          if (!grouped[cid]) grouped[cid] = [];
          grouped[cid].push(event);
        } else {
          ungrouped.push(event);
        }
      }
      if (ungrouped.length > 0 && c.length > 0) {
        const firstCycleId = c[0].id;
        if (!grouped[firstCycleId]) grouped[firstCycleId] = [];
        grouped[firstCycleId].push(...ungrouped);
      }
      for (const cid of Object.keys(grouped)) {
        grouped[Number(cid)] = grouped[Number(cid)].reverse();
      }
      setEventsByCycle(grouped);
    }).catch(() => setError(true)).finally(() => setLoading(false));
  }, []);

  // Live Binance price polling
  useEffect(() => {
    const symbols = (portfolio?.positions ?? []).map((p: Position) => p.symbol);
    if (symbols.length === 0) return;

    const fetchPrices = async () => {
      try {
        const params = symbols.map((s: string) => `"${s}"`).join(',');
        const res = await fetch(`https://data-api.binance.vision/api/v3/ticker/price?symbols=[${params}]`);
        const data = await res.json();
        const newPrices: Record<string, number> = {};
        const flashes: Record<string, 'up' | 'down' | ''> = {};
        for (const item of data) {
          const price = parseFloat(item.price);
          newPrices[item.symbol] = price;
          const prev = livePricesRef.current[item.symbol];
          if (prev && price !== prev) {
            flashes[item.symbol] = price > prev ? 'up' : 'down';
          }
        }
        livePricesRef.current = newPrices;
        setLivePrices(newPrices);
        if (Object.keys(flashes).length > 0) {
          setPriceFlash(flashes);
          setTimeout(() => setPriceFlash({}), 1000);
        }
      } catch { /* silently fail */ }
    };

    fetchPrices();
    const interval = setInterval(fetchPrices, 10000);
    return () => clearInterval(interval);
  }, [portfolio]);

  /* ── Derived data ── */
  const positions: Position[] = portfolio?.positions ?? [];
  const cash = portfolio?.cash ?? 100000;
  const invested = positions.reduce((s, p) => s + p.quantity * (livePrices[p.symbol] || p.current_price || p.entry_price), 0);
  const totalValue = cash + invested;
  const returnPct = ((totalValue - 100000) / 100000) * 100;

  const openTradesBySymbol: Record<string, TradeEntry> = {};
  for (const t of trades) {
    if (t.exit_reason === 'OPEN') openTradesBySymbol[t.symbol] = t;
  }

  const activeAgents = agents.filter(a => ['founding', 'active', 'assigned'].includes(a.status));
  const totalSignals = agents.reduce((s, a) => s + a.total_signals, 0);
  const lastCycle = cycles?.[0];

  const closedTrades = trades
    .filter(t => t.exit_reason && t.exit_reason !== 'OPEN')
    .sort((a, b) => (b.exit_time ?? '').localeCompare(a.exit_time ?? ''));
  const displayedClosed = showAllClosed ? closedTrades : closedTrades.slice(0, 10);
  const closedPnl = closedTrades.reduce((s, t) => s + (t.pnl_usd ?? 0), 0);
  const winRate = tradeStats?.win_rate ?? (closedTrades.length > 0
    ? Math.round(closedTrades.filter(t => (t.pnl_usd ?? 0) > 0).length / closedTrades.length * 100)
    : 0);

  const hasCycles = cycles.length > 0;
  const hasPositions = positions.length > 0;
  const hasClosedTrades = closedTrades.length > 0;
  const hasData = hasCycles || hasPositions || hasClosedTrades;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={20} className="animate-spin text-syn-accent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Zap size={36} className="text-white/10" />
        <p className="text-sm text-syn-muted">Could not load dashboard data</p>
        <p className="text-xs text-syn-muted/50">Ensure the API server is running on {API_BASE}</p>
      </div>
    );
  }

  return (
    <div className="slide-up">

      {/* ══ Macro Regime Bar ══ */}
      <div className="bg-syn-surface border border-syn-border rounded-xl p-4 mb-4 relative overflow-hidden">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Globe size={14} className="text-cyan-400" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Macro Regime</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-bold text-emerald-400 tracking-wider">GOLDILOCKS</span>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* Fed Funds Rate */}
          <div className="text-center">
            <p className="text-[10px] text-syn-text-tertiary mb-1">Fed Funds Rate</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-lg font-bold font-mono text-syn-text">5.33%</span>
              <ArrowDownRight size={12} className="text-emerald-400" />
            </div>
            <p className="text-[10px] text-syn-muted mt-0.5">Cuts expected</p>
          </div>
          {/* M2 Money Supply */}
          <div className="text-center">
            <p className="text-[10px] text-syn-text-tertiary mb-1">M2 Money Supply</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-lg font-bold font-mono text-emerald-400">+3.8%</span>
              <ArrowUpRight size={12} className="text-emerald-400" />
            </div>
            <p className="text-[10px] text-syn-muted mt-0.5">YoY — leads BTC 10-12wk</p>
          </div>
          {/* DXY */}
          <div className="text-center">
            <p className="text-[10px] text-syn-text-tertiary mb-1">DXY Index</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-lg font-bold font-mono text-amber-400">103.2</span>
              <ArrowDownRight size={12} className="text-emerald-400" />
            </div>
            <p className="text-[10px] text-syn-muted mt-0.5">Below 200-day MA</p>
          </div>
          {/* FOMC Countdown */}
          <div className="text-center">
            <p className="text-[10px] text-syn-text-tertiary mb-1">FOMC Meeting</p>
            <div className="flex items-center justify-center gap-1">
              <Timer size={14} className="text-amber-400" />
              <span className="text-lg font-bold font-mono text-syn-text">12d</span>
            </div>
            <p className="text-[10px] text-syn-muted mt-0.5">Next decision in 12 days</p>
          </div>
        </div>
      </div>

      {/* ══ On-Chain Signals Row ══ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {/* MVRV Ratio */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 mb-2">
            <Layers size={12} className="text-cyan-400" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">MVRV Ratio</p>
          </div>
          <p className="text-xl font-bold font-mono text-amber-400">2.1</p>
          <div className="mt-2 h-1.5 bg-white/[0.04] rounded-full overflow-hidden relative">
            <div className="absolute inset-y-0 left-0 w-[57%] rounded-full" style={{ background: 'linear-gradient(90deg, #34d399 0%, #34d399 35%, #fbbf24 35%, #fbbf24 65%, #f87171 65%)' }} />
            <div className="absolute top-1/2 -translate-y-1/2 h-3 w-0.5 bg-white rounded-full shadow-lg" style={{ left: '42%' }} />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[9px] text-emerald-400/60">&lt;2 Accum</span>
            <span className="text-[9px] text-amber-400/60">2-3.5</span>
            <span className="text-[9px] text-red-400/60">&gt;3.5 Top</span>
          </div>
        </div>

        {/* Funding Rate */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 mb-2">
            <DollarSign size={12} className="text-emerald-400" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Funding Rate</p>
          </div>
          <p className="text-xl font-bold font-mono text-emerald-400">0.03%</p>
          <p className="text-[10px] text-syn-text-tertiary mt-1">per 8hr</p>
          <div className="mt-1.5 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[10px] text-emerald-400">Neutral — healthy long bias</span>
          </div>
        </div>

        {/* BTC Dominance */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 mb-2">
            <Coins size={12} className="text-orange-400" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">BTC Dominance</p>
          </div>
          <p className="text-xl font-bold font-mono text-syn-text">57.2%</p>
          <div className="mt-1.5 flex items-center gap-1">
            <ArrowUpRight size={10} className="text-amber-400" />
            <span className="text-[10px] text-amber-400">Stage 3 — BTC leading</span>
          </div>
          <p className="text-[10px] text-syn-muted mt-0.5">Alt rotation not yet started</p>
        </div>

        {/* Stablecoin Supply */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 mb-2">
            <DollarSign size={12} className="text-blue-400" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Stablecoin Supply</p>
          </div>
          <p className="text-xl font-bold font-mono text-syn-text">$168B</p>
          <div className="mt-1.5 flex items-center gap-1">
            <ArrowUpRight size={10} className="text-emerald-400" />
            <span className="text-[10px] text-emerald-400">Growing — bullish inflow</span>
          </div>
          <p className="text-[10px] text-syn-muted mt-0.5">+$4.2B last 30 days</p>
        </div>
      </div>

      {/* ══ Fear & Greed + VIX Row ══ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        {/* Fear & Greed Gauge */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 mb-3">
            <Gauge size={14} className="text-amber-400" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Crypto Fear & Greed</p>
          </div>
          <div className="flex items-center gap-6">
            {/* Gauge visual */}
            <div className="relative w-28 h-16 shrink-0">
              <svg viewBox="0 0 120 70" className="w-full h-full">
                {/* Background arc */}
                <path d="M 10 65 A 50 50 0 0 1 110 65" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" strokeLinecap="round" />
                {/* Extreme Fear (red) */}
                <path d="M 10 65 A 50 50 0 0 1 35 22" fill="none" stroke="#ef4444" strokeWidth="8" strokeLinecap="round" opacity="0.6" />
                {/* Fear (orange) */}
                <path d="M 35 22 A 50 50 0 0 1 60 15" fill="none" stroke="#f97316" strokeWidth="8" strokeLinecap="round" opacity="0.6" />
                {/* Neutral (yellow) */}
                <path d="M 60 15 A 50 50 0 0 1 85 22" fill="none" stroke="#eab308" strokeWidth="8" strokeLinecap="round" opacity="0.6" />
                {/* Greed (lime) */}
                <path d="M 85 22 A 50 50 0 0 1 100 40" fill="none" stroke="#84cc16" strokeWidth="8" strokeLinecap="round" opacity="0.6" />
                {/* Extreme Greed (green) */}
                <path d="M 100 40 A 50 50 0 0 1 110 65" fill="none" stroke="#22c55e" strokeWidth="8" strokeLinecap="round" opacity="0.6" />
                {/* Needle — 68/100 = ~122 degrees from left */}
                <line x1="60" y1="65" x2={60 + 40 * Math.cos(Math.PI * (1 - 68 / 100))} y2={65 - 40 * Math.sin(Math.PI * (1 - 68 / 100))} stroke="white" strokeWidth="2" strokeLinecap="round" />
                <circle cx="60" cy="65" r="3" fill="white" />
              </svg>
            </div>
            <div>
              <p className="text-3xl font-bold font-mono text-lime-400">68</p>
              <p className="text-xs font-semibold text-lime-400">Greed</p>
              <p className="text-[10px] text-syn-muted mt-1">Historically favors continuation</p>
            </div>
          </div>
        </div>

        {/* VIX Card */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 mb-3">
            <Activity size={14} className="text-blue-400" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">VIX — Volatility Index</p>
          </div>
          <div className="flex items-center gap-6">
            <div>
              <p className="text-3xl font-bold font-mono text-emerald-400">16.8</p>
              <p className="text-xs text-syn-text-tertiary mt-0.5">25th percentile</p>
            </div>
            <div className="flex-1 space-y-2">
              <div>
                <div className="flex justify-between text-[10px] mb-0.5">
                  <span className="text-syn-muted">Term Structure</span>
                  <span className="text-emerald-400 font-semibold">Contango</span>
                </div>
                <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500/40 rounded-full" style={{ width: '30%' }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-[10px] mb-0.5">
                  <span className="text-syn-muted">Risk Level</span>
                  <span className="text-emerald-400 font-semibold">Low Vol</span>
                </div>
                <div className="flex gap-0.5">
                  {[
                    { label: '<15', active: false, color: 'bg-emerald-500/30' },
                    { label: '15-20', active: true, color: 'bg-emerald-500/60' },
                    { label: '20-30', active: false, color: 'bg-amber-500/30' },
                    { label: '>30', active: false, color: 'bg-red-500/30' },
                  ].map((zone) => (
                    <div key={zone.label} className={`flex-1 h-1.5 rounded-sm ${zone.active ? zone.color + ' ring-1 ring-white/20' : 'bg-white/[0.04]'}`} />
                  ))}
                </div>
                <div className="flex justify-between mt-0.5">
                  <span className="text-[8px] text-syn-muted">Calm</span>
                  <span className="text-[8px] text-syn-muted">Panic</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Stats Strip ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {/* Portfolio Value */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4 relative overflow-hidden">
          <div className="absolute -top-8 -left-8 w-40 h-40 bg-syn-accent-muted rounded-full blur-3xl pointer-events-none" />
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Portfolio Value</p>
          <div className={`text-lg font-bold ${returnPct >= 0 ? 'text-syn-text' : 'text-red-400'}`}>
            <AnimatedNumber value={totalValue} prefix="$" decimals={0} />
          </div>
          <div className={`mt-1 flex items-center gap-1 text-xs font-medium ${returnPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {returnPct >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
            <span className="font-mono tabular-nums">{returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%</span>
          </div>
        </div>

        {/* Realized P&L */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Realized P&L</p>
          <p className={`text-lg font-bold font-mono tabular-nums ${closedPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {closedPnl >= 0 ? '+' : ''}{fmtUsd(closedPnl)}
          </p>
          <p className="text-[10px] text-syn-text-tertiary mt-1">{closedTrades.length} closed trades</p>
        </div>

        {/* Win Rate */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Win Rate</p>
          {closedTrades.length > 0 ? (
            <>
              <div className="flex items-center gap-2">
                <Target size={14} className={winRate >= 55 ? 'text-emerald-400' : winRate >= 45 ? 'text-amber-400' : 'text-red-400'} />
                <span className={`text-lg font-bold font-mono ${winRate >= 55 ? 'text-emerald-400' : winRate >= 45 ? 'text-amber-400' : 'text-red-400'}`}>
                  {winRate}%
                </span>
              </div>
              <p className="text-[10px] text-syn-text-tertiary mt-1">
                {tradeStats ? `${tradeStats.wins}W / ${tradeStats.losses}L` : `${closedTrades.filter(t => (t.pnl_usd ?? 0) > 0).length}W / ${closedTrades.filter(t => (t.pnl_usd ?? 0) <= 0).length}L`}
              </p>
            </>
          ) : (
            <p className="text-xs text-syn-text-tertiary">Awaiting trades</p>
          )}
        </div>

        {/* Regime */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Regime</p>
          {lastCycle?.regime ? (
            <>
              <div className="flex items-center gap-1.5">
                {lastCycle.regime === 'bull' ? <TrendingUp size={14} className="text-emerald-400" /> :
                  lastCycle.regime === 'bear' ? <TrendingDown size={14} className="text-red-400" /> :
                    <Shield size={14} className="text-syn-accent" />}
                <span className={`text-lg font-bold ${
                  lastCycle.regime === 'bull' ? 'text-emerald-400' :
                    lastCycle.regime === 'bear' ? 'text-red-400' :
                      'text-syn-accent'
                }`}>{lastCycle.regime.toUpperCase()}</span>
              </div>
              <p className="text-[10px] text-syn-text-tertiary mt-1">
                {positions.length} open / {activeAgents.length} agents / {totalSignals.toLocaleString()} signals
              </p>
            </>
          ) : (
            <p className="text-xs text-syn-text-tertiary">Awaiting</p>
          )}
        </div>
      </div>

      {/* ── Portfolio Risk Card ── */}
      {portfolioRisk && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Portfolio Risk</h3>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              DRAWDOWN_COLORS[portfolioRisk.drawdown_level]?.bg ?? 'bg-syn-surface'
            } ${DRAWDOWN_COLORS[portfolioRisk.drawdown_level]?.color ?? 'text-syn-muted'}`}>
              {DRAWDOWN_COLORS[portfolioRisk.drawdown_level]?.label ?? portfolioRisk.drawdown_level}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <p className="text-[10px] text-syn-text-tertiary">Drawdown</p>
              <p className={`text-sm font-mono font-bold ${
                portfolioRisk.drawdown_pct > 3 ? 'text-red-400' : portfolioRisk.drawdown_pct > 1.5 ? 'text-amber-400' : 'text-emerald-400'
              }`}>{portfolioRisk.drawdown_pct.toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-[10px] text-syn-text-tertiary">Portfolio Heat</p>
              <p className={`text-sm font-mono font-bold ${
                portfolioRisk.heat_exceeded ? 'text-red-400' : portfolioRisk.portfolio_heat > 5 ? 'text-amber-400' : 'text-emerald-400'
              }`}>{portfolioRisk.portfolio_heat.toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-[10px] text-syn-text-tertiary">Correlation</p>
              <p className={`text-sm font-mono font-bold ${
                portfolioRisk.correlation_warning ? 'text-red-400' : portfolioRisk.avg_correlation > 0.6 ? 'text-amber-400' : 'text-emerald-400'
              }`}>{portfolioRisk.avg_correlation.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-[10px] text-syn-text-tertiary">Size Multiplier</p>
              <p className={`text-sm font-mono font-bold ${
                portfolioRisk.size_multiplier < 1 ? 'text-amber-400' : 'text-emerald-400'
              }`}>{(portfolioRisk.size_multiplier * 100).toFixed(0)}%</p>
            </div>
          </div>
          {portfolioRisk.actions.length > 0 && (
            <div className="mt-2 space-y-1">
              {portfolioRisk.actions.slice(0, 2).map((a, i) => (
                <p key={i} className="text-[10px] text-orange-400/80 font-mono">{a}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Equity Curve ── */}
      <EquityCurve data={allCycles} />

      {/* Welcome message when no data */}
      {!hasData && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-10 text-center mb-6">
          <p className="text-sm text-syn-text-secondary font-medium mb-1">Welcome to Syndicate</p>
          <p className="text-xs text-syn-text-tertiary max-w-md mx-auto">
            The pipeline runs every 4 hours. Once the first cycle completes, you&apos;ll see the latest analysis here with positions and trade activity.
          </p>
        </div>
      )}

      {/* ── Main Content + Sidebar ── */}
      {hasData && (
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Main column */}
          <div className="flex-1 min-w-0 space-y-4">
            {/* Open Positions Table */}
            {hasPositions && (
              <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-syn-border flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full bg-syn-accent animate-pulse" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Open Positions</span>
                  </div>
                  <span className="text-[10px] font-mono text-syn-text-tertiary whitespace-nowrap">
                    {positions.length} open / ${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })} deployed
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[700px]">
                    <thead>
                      <tr className="text-[11px] font-bold uppercase tracking-[0.15em] text-syn-text-tertiary border-b border-syn-border">
                        <th className="text-left pl-4 pr-2 py-2 whitespace-nowrap">Symbol</th>
                        <th className="text-left px-2 py-2 whitespace-nowrap">Side</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">Size</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">Entry</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">Price</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">SL</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">TP</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">P&L</th>
                        <th className="text-right pr-4 pl-2 py-2 whitespace-nowrap">Conv</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos, i) => {
                        const live = livePrices[pos.symbol] || pos.current_price;
                        const size = pos.quantity * live;
                        const pnlUsd = pos.side === 'BUY'
                          ? (live - pos.entry_price) * pos.quantity
                          : (pos.entry_price - live) * pos.quantity;
                        const pnlPct = pos.entry_price > 0
                          ? ((live - pos.entry_price) / pos.entry_price * 100) * (pos.side === 'BUY' ? 1 : -1)
                          : 0;
                        const trade = openTradesBySymbol[pos.symbol];
                        const sl = trade?.stop_loss ?? 0;
                        const tp = trade?.take_profit_1 ?? 0;
                        const conviction = trade?.conviction ?? 0;
                        const flash = priceFlash[pos.symbol];

                        return (
                          <tr
                            key={i}
                            className={`border-b border-white/[0.03] transition-all duration-300 hover:bg-white/[0.02] ${
                              flash === 'up' ? 'bg-emerald-500/[0.04]' :
                                flash === 'down' ? 'bg-red-500/[0.04]' : ''
                            }`}
                          >
                            <td className="pl-4 pr-2 py-2.5 whitespace-nowrap">
                              <span className="text-sm font-bold text-syn-text">
                                {pos.symbol.replace('USDT', '')}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 whitespace-nowrap">
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                pos.side === 'BUY'
                                  ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20'
                                  : 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20'
                              }`}>
                                {pos.side}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <span className="text-xs font-mono tabular-nums text-syn-text">
                                ${size.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <span className="text-xs font-mono tabular-nums text-syn-text-tertiary">
                                ${pos.entry_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                              </span>
                            </td>
                            <td className={`px-2 py-2.5 text-right whitespace-nowrap transition-colors duration-500 ${
                              flash === 'up' ? 'text-emerald-400' :
                                flash === 'down' ? 'text-red-400' : 'text-syn-text'
                            }`}>
                              <span className="text-xs font-mono tabular-nums font-medium">
                                ${live.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <span className="text-xs font-mono tabular-nums text-red-400/60">
                                {sl > 0 ? `$${sl.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '\u2014'}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <span className="text-xs font-mono tabular-nums text-emerald-400/60">
                                {tp > 0 ? `$${tp.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '\u2014'}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <div className={`text-xs font-mono tabular-nums font-semibold ${pnlUsd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {pnlUsd >= 0 ? '+' : ''}{pnlUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                              </div>
                              <div className={`text-[10px] font-mono tabular-nums ${pnlUsd >= 0 ? 'text-emerald-400/50' : 'text-red-400/50'}`}>
                                {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                              </div>
                            </td>
                            <td className="pr-4 pl-2 py-2.5 whitespace-nowrap">
                              <div className="flex items-center justify-end gap-1.5">
                                <div className="w-12 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-syn-accent transition-all"
                                    style={{ width: `${(conviction / 10) * 100}%` }}
                                  />
                                </div>
                                <span className="text-[10px] font-mono text-syn-text-tertiary w-4 text-right">{conviction}</span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Closed Positions Table */}
            {hasClosedTrades && (
              <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-syn-border flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full bg-white/20" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Closed Positions</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-[10px] font-mono tabular-nums ${closedPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {closedPnl >= 0 ? '+' : ''}{fmtUsd(closedPnl)} realized
                    </span>
                    <a href="/results" className="text-[10px] text-syn-muted hover:text-syn-accent transition-colors flex items-center gap-0.5">
                      Details <ChevronRight size={10} />
                    </a>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[700px]">
                    <thead>
                      <tr className="text-[11px] font-bold uppercase tracking-[0.15em] text-syn-text-tertiary border-b border-syn-border">
                        <th className="text-left pl-4 pr-2 py-2 whitespace-nowrap">Symbol</th>
                        <th className="text-left px-2 py-2 whitespace-nowrap">Side</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">Entry</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">Exit</th>
                        <th className="text-left px-2 py-2 whitespace-nowrap">Reason</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">P&L</th>
                        <th className="text-right px-2 py-2 whitespace-nowrap">Hold</th>
                        <th className="text-left pr-4 pl-2 py-2 whitespace-nowrap">Tier</th>
                      </tr>
                    </thead>
                    <tbody>
                      {displayedClosed.map((trade, i) => {
                        const pnlPct = (trade.pnl_pct ?? 0) * 100;
                        const isWin = (trade.pnl_usd ?? 0) > 0;
                        return (
                          <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                            <td className="pl-4 pr-2 py-2.5 whitespace-nowrap">
                              <span className="text-sm font-bold text-syn-text">
                                {trade.symbol.replace('USDT', '')}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 whitespace-nowrap">
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                trade.side === 'BUY'
                                  ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20'
                                  : 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20'
                              }`}>
                                {trade.side === 'BUY' ? 'LONG' : 'SHORT'}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <span className="text-xs font-mono tabular-nums text-syn-text-tertiary">
                                ${trade.entry_price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <span className="text-xs font-mono tabular-nums text-syn-text-tertiary">
                                ${trade.exit_price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 whitespace-nowrap">
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
                                trade.exit_reason?.includes('PROFIT')
                                  ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20'
                                  : trade.exit_reason === 'STOP_LOSS'
                                    ? 'bg-red-500/10 text-red-400 ring-red-500/20'
                                    : 'bg-white/[0.04] text-white/40 ring-white/[0.08]'
                              }`}>
                                {exitReasonLabel(trade.exit_reason)}
                              </span>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <div className={`text-xs font-mono tabular-nums font-semibold ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
                                {(trade.pnl_usd ?? 0) >= 0 ? '+' : ''}{fmtUsd(trade.pnl_usd ?? 0)}
                              </div>
                              <div className={`text-[10px] font-mono tabular-nums ${isWin ? 'text-emerald-400/50' : 'text-red-400/50'}`}>
                                {fmtPct(pnlPct)}
                              </div>
                            </td>
                            <td className="px-2 py-2.5 text-right whitespace-nowrap">
                              <span className="text-xs font-mono tabular-nums text-syn-text-tertiary">
                                {(trade.holding_hours ?? 0) > 0 ? fmtHours(trade.holding_hours) : '\u2014'}
                              </span>
                            </td>
                            <td className="pr-4 pl-2 py-2.5 whitespace-nowrap">
                              {trade.asset_tier && (
                                <span className="text-[10px] text-syn-text-tertiary capitalize">{trade.asset_tier}</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {closedTrades.length > 10 && (
                  <button
                    onClick={() => setShowAllClosed(!showAllClosed)}
                    className="w-full py-2.5 border-t border-syn-border text-[10px] text-syn-text-tertiary hover:text-syn-text-secondary hover:bg-white/[0.02] transition-colors flex items-center justify-center gap-1"
                  >
                    {showAllClosed ? (
                      <>Show less <ChevronUp size={10} /></>
                    ) : (
                      <>Show all {closedTrades.length} trades <ChevronDown size={10} /></>
                    )}
                  </button>
                )}
              </div>
            )}

            {/* Latest Cycle (compact) */}
            {lastCycle && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Latest Cycle</h2>
                  <a href="/activity" className="text-[10px] text-syn-muted hover:text-syn-accent transition-colors flex items-center gap-0.5">
                    All activity <ChevronRight size={10} />
                  </a>
                </div>
                <CycleCard
                  cycle={lastCycle}
                  events={eventsByCycle[lastCycle.id] || []}
                  defaultOpen={false}
                />
              </div>
            )}

            {/* CTA banner */}
            <div className="bg-syn-surface border border-syn-accent/[0.15] rounded-xl p-3 bg-gradient-to-r from-syn-accent/[0.05] to-syn-secondary/[0.05]">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <Zap size={14} className="text-syn-accent shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-syn-text-secondary truncate">Contribute your API key to expand the hive</p>
                    <p className="text-[10px] text-syn-text-tertiary truncate">More agents = deeper analysis, better signals</p>
                  </div>
                </div>
                <a href="/register" className="shrink-0 inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-syn-accent text-white text-[10px] font-bold rounded-lg hover:bg-syn-accent-hover hover:shadow-lg hover:shadow-syn-accent/20 transition-all">
                  Contribute <ArrowRight size={10} />
                </a>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="w-full lg:w-[280px] shrink-0 space-y-3">
            <ActivityFeed trades={trades} />
            <PerformanceSnapshot stats={tradeStats} closedTrades={closedTrades} />
            <DisagreementSidebar />
            <LeaderboardSidebar agents={agents} />
          </div>
        </div>
      )}
    </div>
  );
}
