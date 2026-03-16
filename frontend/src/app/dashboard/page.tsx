'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Shield, Activity, Clock, ArrowRight,
  ChevronRight, Zap,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants & Types
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const AGENT_COLORS: Record<string, string> = {
  'TechnicalTrendAgent': 'from-blue-500 to-cyan-500',
  'TechnicalSignalAgent': 'from-blue-400 to-indigo-500',
  'TechnicalTimingAgent': 'from-sky-500 to-blue-500',
  'SocialSentimentAgent': 'from-purple-500 to-pink-500',
  'MarketSentimentAgent': 'from-violet-500 to-purple-600',
  'SmartMoneySentimentAgent': 'from-fuchsia-500 to-purple-500',
  'ValuationAgent': 'from-yellow-500 to-amber-500',
  'CyclePositionAgent': 'from-amber-500 to-orange-500',
  'CryptoMacroAgent': 'from-cyan-500 to-teal-500',
  'ExternalMacroAgent': 'from-teal-500 to-emerald-500',
  'NetworkHealthAgent': 'from-emerald-500 to-green-500',
  'CapitalFlowAgent': 'from-green-500 to-lime-500',
};

const TEAM_COLORS: Record<string, string> = {
  'technical': 'from-blue-500 to-cyan-500',
  'sentiment': 'from-purple-500 to-pink-500',
  'fundamental': 'from-yellow-500 to-amber-500',
  'macro': 'from-cyan-500 to-teal-500',
  'onchain': 'from-emerald-500 to-green-500',
};

interface Position { symbol: string; side: string; entry_price: number; quantity: number; current_price: number; }
interface TradeEntry { symbol: string; side: string; entry_price: number; stop_loss: number; take_profit_1: number; conviction: number; confidence: number; risk_amount: number; exit_reason: string; asset_tier: string; }
interface CycleData { id: number; started_at: string; regime: string | null; coins_analyzed: number; signals_produced: number; orders_executed: number; duration_secs: number | null; }
interface AgentData { id: string; team_name: string | null; role: string; agent_class: string | null; status: string; total_signals: number; accuracy: number; provider: string; }
interface TeamData { id: string; name: string; active_agent_count: number; agent_count: number; weight: number; }

// ---------------------------------------------------------------------------
// Animated Number Component
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Tiny reusable pieces
// ---------------------------------------------------------------------------

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-3">{children}</h3>;
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-[#0d0d15] border border-white/[0.06] rounded-xl ${className}`}>{children}</div>;
}

function StatusDot({ active }: { active: boolean }) {
  return active ? (
    <span className="relative flex h-1.5 w-1.5">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
    </span>
  ) : (
    <span className="h-1.5 w-1.5 rounded-full bg-white/10" />
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [teams, setTeams] = useState<TeamData[]>([]);
  const [trades, setTrades] = useState<TradeEntry[]>([]);
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const [priceFlash, setPriceFlash] = useState<Record<string, 'up' | 'down' | ''>>({});
  const [loading, setLoading] = useState(true);
  const livePricesRef = useRef<Record<string, number>>({});

  // ---- Data fetching ----
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/portfolio`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/cycles?limit=5`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/agents`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/teams`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/portfolio/trades`).then(r => r.json()).catch(() => []),
    ]).then(([p, c, a, t, tr]) => {
      setPortfolio(p);
      setCycles(c);
      setAgents(a);
      setTeams(t);
      setTrades(Array.isArray(tr) ? tr : []);
    }).finally(() => setLoading(false));
  }, []);

  // ---- Live Binance price polling ----
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

  // ---- Derived data ----
  const positions: Position[] = portfolio?.positions ?? [];
  const cash = portfolio?.cash ?? 100000;
  const invested = positions.reduce((s, p) => s + p.quantity * (livePrices[p.symbol] || p.current_price || p.entry_price), 0);
  const totalValue = cash + invested;
  const returnPct = ((totalValue - 100000) / 100000) * 100;
  const returnUsd = totalValue - 100000;

  const openTradesBySymbol: Record<string, TradeEntry> = {};
  for (const t of trades) {
    if (t.exit_reason === 'OPEN') openTradesBySymbol[t.symbol] = t;
  }

  const activeAgents = agents.filter(a => ['founding', 'active', 'assigned'].includes(a.status));
  const totalSignals = agents.reduce((s, a) => s + a.total_signals, 0);
  const lastCycle = cycles?.[0];
  const totalOrders = cycles.reduce((s, c) => s + c.orders_executed, 0);

  // Top 5 agents by total_signals
  const topAgents = [...agents].sort((a, b) => b.total_signals - a.total_signals).slice(0, 5);

  // Recent closed trades for activity feed
  const recentTrades = trades
    .filter(t => t.exit_reason !== 'OPEN')
    .slice(0, 8);

  const pipelineSteps = ['Intelligence', 'CEO Directive', 'Coin Selection', 'Agent Analysis', 'Aggregation', 'Risk Check', 'Execution'];

  // ---- Loading state ----
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={20} className="animate-spin text-amber-400" />
      </div>
    );
  }

  // ---- Render ----
  return (
    <div className="slide-up">
      {/* Top bar — status strip */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-[#0d0d15] border border-white/[0.06] rounded-lg px-2.5 py-1">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
            </span>
            <span className="text-[10px] font-bold tracking-wider text-emerald-400">LIVE</span>
          </div>
          <span className="text-[10px] text-white/25 font-mono">
            {activeAgents.length} agents / {teams.length} teams / {totalSignals.toLocaleString()} signals
          </span>
        </div>
        <div className="flex items-center gap-3">
          {lastCycle && (
            <span className="text-[10px] text-white/25 font-mono flex items-center gap-1">
              <Clock size={10} className="text-white/20" />
              Last cycle {new Date(lastCycle.started_at).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* === 3-Column Terminal Layout === */}
      <div className="flex flex-col lg:flex-row gap-3">

        {/* ================================================================ */}
        {/* LEFT COLUMN — Portfolio Vitals + Regime + Pipeline               */}
        {/* ================================================================ */}
        <div className="w-full lg:w-[280px] shrink-0 space-y-3">

          {/* Portfolio Value — hero number with ambient glow */}
          <Card className="p-4 relative overflow-hidden">
            {/* Ambient glow */}
            <div className="absolute -top-8 -left-8 w-40 h-40 bg-amber-500/[0.04] rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-8 -right-8 w-32 h-32 bg-amber-500/[0.03] rounded-full blur-3xl pointer-events-none" />
            <SectionLabel>Portfolio Value</SectionLabel>
            <div className={`text-[28px] font-bold leading-none ${returnPct >= 0 ? 'text-white' : 'text-red-400'}`}>
              <AnimatedNumber value={totalValue} prefix="$" decimals={0} />
            </div>
            <div className={`mt-2 flex items-center gap-1.5 text-xs font-medium ${returnPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {returnPct >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
              <span className="font-mono tabular-nums">
                {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%
              </span>
              <span className="text-white/25 mx-0.5">|</span>
              <span className="font-mono tabular-nums">
                {returnUsd >= 0 ? '+' : ''}${returnUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </div>
          </Card>

          {/* Vitals strip */}
          <Card className="p-4 space-y-3">
            <SectionLabel>Capital Allocation</SectionLabel>
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-white/50">Invested</span>
                <span className="text-[13px] font-mono tabular-nums text-white">
                  <AnimatedNumber value={invested} prefix="$" decimals={0} />
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-white/50">Cash</span>
                <span className="text-[13px] font-mono tabular-nums text-white/50">
                  ${cash.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              {/* Allocation bar */}
              <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-700"
                  style={{ width: `${totalValue > 0 ? (invested / totalValue) * 100 : 0}%` }}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-white/25">
                  {totalValue > 0 ? ((invested / totalValue) * 100).toFixed(1) : '0'}% deployed
                </span>
                <span className="text-[10px] text-white/25">
                  {positions.length} position{positions.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </Card>

          {/* Market Regime */}
          <Card className="p-4">
            <SectionLabel>Market Regime</SectionLabel>
            {lastCycle?.regime ? (
              <div className="flex items-center gap-2.5">
                <div className={`flex items-center justify-center w-9 h-9 rounded-lg ring-1 ring-inset ${
                  lastCycle.regime === 'bull' ? 'bg-emerald-500/10 ring-emerald-500/20' :
                  lastCycle.regime === 'bear' ? 'bg-red-500/10 ring-red-500/20' :
                  lastCycle.regime === 'crisis' ? 'bg-red-900/20 ring-red-500/30' :
                  'bg-amber-500/10 ring-amber-500/20'
                }`}>
                  {lastCycle.regime === 'bull' ? <TrendingUp size={16} className="text-emerald-400" /> :
                   lastCycle.regime === 'bear' ? <TrendingDown size={16} className="text-red-400" /> :
                   <Shield size={16} className="text-amber-400" />}
                </div>
                <div>
                  <span className={`text-sm font-bold tracking-wide ${
                    lastCycle.regime === 'bull' ? 'text-emerald-400' :
                    lastCycle.regime === 'bear' ? 'text-red-400' :
                    lastCycle.regime === 'crisis' ? 'text-red-300' :
                    'text-amber-400'
                  }`}>
                    {lastCycle.regime.toUpperCase()}
                  </span>
                  <p className="text-[10px] text-white/25 mt-0.5">Set by CEO each cycle</p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-white/25">Awaiting first cycle</p>
            )}
          </Card>

          {/* Cycle Pipeline */}
          <Card className="p-4">
            <SectionLabel>Cycle Pipeline</SectionLabel>
            <div className="space-y-1">
              {pipelineSteps.map((step, i) => (
                <div key={step} className="flex items-center gap-2 group">
                  <span className="w-4 text-[9px] font-mono text-white/15 text-right">{i + 1}</span>
                  <div className={`flex-1 text-[11px] py-1 px-2 rounded transition-colors ${
                    lastCycle
                      ? 'bg-emerald-500/[0.04] text-emerald-400/50 ring-1 ring-inset ring-emerald-500/[0.08]'
                      : 'bg-white/[0.02] text-white/15 ring-1 ring-inset ring-white/[0.04]'
                  }`}>
                    {step}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[9px] text-white/20 mt-2.5 font-mono">Every 4h on UTC boundaries</p>
          </Card>

          {/* Quick stats */}
          <Card className="p-4">
            <SectionLabel>Cycle Stats</SectionLabel>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-[10px] text-white/25">Total Orders</p>
                <p className="text-lg font-bold font-mono tabular-nums">{totalOrders}</p>
              </div>
              <div>
                <p className="text-[10px] text-white/25">Signals</p>
                <p className="text-lg font-bold font-mono tabular-nums">{totalSignals.toLocaleString()}</p>
              </div>
            </div>
          </Card>
        </div>

        {/* ================================================================ */}
        {/* CENTER — Positions Table + Activity Feed                         */}
        {/* ================================================================ */}
        <div className="flex-1 min-w-0 space-y-3">

          {/* Positions Table */}
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Open Positions</span>
              </div>
              <span className="text-[10px] font-mono text-white/25">
                {positions.length} open / ${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })} deployed
              </span>
            </div>

            {positions.length === 0 ? (
              <div className="px-4 py-16 text-center">
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mx-auto mb-3">
                  <Activity size={16} className="text-white/10" />
                </div>
                <p className="text-xs text-white/25">No open positions</p>
                <p className="text-[10px] text-white/15 mt-1">Next cycle will analyze markets and generate trades</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-[9px] font-bold uppercase tracking-[0.15em] text-white/25 border-b border-white/[0.06]">
                      <th className="text-left pl-4 pr-2 py-2">Symbol</th>
                      <th className="text-left px-2 py-2">Side</th>
                      <th className="text-right px-2 py-2">Size</th>
                      <th className="text-right px-2 py-2">Entry</th>
                      <th className="text-right px-2 py-2">Price</th>
                      <th className="text-right px-2 py-2">SL</th>
                      <th className="text-right px-2 py-2">TP</th>
                      <th className="text-right px-2 py-2">P&L</th>
                      <th className="text-right pr-4 pl-2 py-2">Conv</th>
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
                      const riskAmt = trade?.risk_amount ?? 0;
                      const flash = priceFlash[pos.symbol];
                      const teamName = trade?.asset_tier; // might be useful later
                      const agentClass = trade ? Object.keys(AGENT_COLORS).find(k => k.toLowerCase().includes('technical')) : null;

                      // Determine team color for the row dot
                      const dotGradient = TEAM_COLORS['technical'] ?? 'from-white/20 to-white/10';

                      return (
                        <tr
                          key={i}
                          className={`border-b border-white/[0.03] transition-all duration-300 hover:bg-white/[0.02] hover:ring-1 hover:ring-inset hover:ring-white/[0.06] ${
                            flash === 'up' ? 'bg-emerald-500/[0.04]' :
                            flash === 'down' ? 'bg-red-500/[0.04]' : ''
                          }`}
                        >
                          {/* Symbol with team color dot */}
                          <td className="pl-4 pr-2 py-2.5">
                            <div className="flex items-center gap-2">
                              <div className={`w-2 h-2 rounded-full bg-gradient-to-br ${dotGradient} shrink-0`} />
                              <span className="text-[13px] font-bold text-white">
                                {pos.symbol.replace('USDT', '')}
                              </span>
                            </div>
                          </td>

                          {/* Side badge */}
                          <td className="px-2 py-2.5">
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                              pos.side === 'BUY'
                                ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20'
                                : 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20'
                            }`}>
                              {pos.side}
                            </span>
                          </td>

                          {/* Size */}
                          <td className="px-2 py-2.5 text-right">
                            <span className="text-[12px] font-mono tabular-nums text-white">
                              ${size.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </span>
                          </td>

                          {/* Entry */}
                          <td className="px-2 py-2.5 text-right">
                            <span className="text-[12px] font-mono tabular-nums text-white/40">
                              ${pos.entry_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                            </span>
                          </td>

                          {/* Live price — flashing */}
                          <td className={`px-2 py-2.5 text-right transition-colors duration-500 ${
                            flash === 'up' ? 'text-emerald-400' :
                            flash === 'down' ? 'text-red-400' : 'text-white'
                          }`}>
                            <span className="text-[12px] font-mono tabular-nums font-medium">
                              ${live.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                            </span>
                          </td>

                          {/* SL */}
                          <td className="px-2 py-2.5 text-right">
                            <span className="text-[12px] font-mono tabular-nums text-red-400/60">
                              {sl > 0 ? `$${sl.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '\u2014'}
                            </span>
                          </td>

                          {/* TP */}
                          <td className="px-2 py-2.5 text-right">
                            <span className="text-[12px] font-mono tabular-nums text-emerald-400/60">
                              {tp > 0 ? `$${tp.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '\u2014'}
                            </span>
                          </td>

                          {/* P&L */}
                          <td className="px-2 py-2.5 text-right">
                            <div className={`text-[12px] font-mono tabular-nums font-semibold ${pnlUsd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {pnlUsd >= 0 ? '+' : ''}{pnlUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                            </div>
                            <div className={`text-[9px] font-mono tabular-nums ${pnlUsd >= 0 ? 'text-emerald-400/50' : 'text-red-400/50'}`}>
                              {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                            </div>
                          </td>

                          {/* Conviction bar */}
                          <td className="pr-4 pl-2 py-2.5">
                            <div className="flex items-center justify-end gap-1.5">
                              <div className="w-12 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                                <div
                                  className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all"
                                  style={{ width: `${(conviction / 10) * 100}%` }}
                                />
                              </div>
                              <span className="text-[9px] font-mono text-white/25 w-4 text-right">{conviction}</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Recent Activity Feed */}
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Recent Activity</span>
              </div>
              <a href="/cycles" className="text-[10px] text-amber-400/50 hover:text-amber-400 transition-colors flex items-center gap-0.5">
                All cycles <ChevronRight size={10} />
              </a>
            </div>

            {/* Recent cycles as dense rows */}
            {cycles.length > 0 ? (
              <div className="divide-y divide-white/[0.03]">
                {cycles.map((c) => (
                  <div key={c.id} className="px-4 py-2.5 flex items-center gap-3 hover:bg-white/[0.02] transition-colors">
                    <span className="text-[10px] font-mono text-white/15 w-6 text-right">#{c.id}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          c.regime === 'bull' ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20' :
                          c.regime === 'bear' ? 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20' :
                          'bg-white/[0.04] text-white/30 ring-1 ring-inset ring-white/[0.06]'
                        }`}>
                          {(c.regime ?? 'N/A').toUpperCase()}
                        </span>
                        <span className="text-[11px] text-white/40">
                          {c.coins_analyzed} coins scanned
                        </span>
                        <span className="text-white/10">|</span>
                        <span className="text-[11px] text-white/40">
                          {c.signals_produced} signals
                        </span>
                        <span className="text-white/10">|</span>
                        <span className="text-[11px] text-white/40">
                          {c.orders_executed} trades
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {c.duration_secs && (
                        <span className="text-[10px] font-mono text-white/15">{Math.round(c.duration_secs)}s</span>
                      )}
                      <span className="text-[10px] font-mono text-white/20">
                        {new Date(c.started_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="px-4 py-8 text-center">
                <p className="text-xs text-white/25">No cycles recorded yet</p>
              </div>
            )}

            {/* Closed trades list */}
            {recentTrades.length > 0 && (
              <>
                <div className="px-4 py-2 border-t border-white/[0.06]">
                  <span className="text-[9px] font-bold uppercase tracking-[0.15em] text-white/20">Recent Closed Trades</span>
                </div>
                <div className="divide-y divide-white/[0.03]">
                  {recentTrades.map((t, i) => {
                    const pnlPct = t.entry_price > 0
                      ? ((t.take_profit_1 - t.entry_price) / t.entry_price * 100) * (t.side === 'BUY' ? 1 : -1)
                      : 0;
                    return (
                      <div key={i} className="px-4 py-2 flex items-center gap-3 hover:bg-white/[0.02] transition-colors">
                        <span className={`w-1 h-4 rounded-full ${t.side === 'BUY' ? 'bg-emerald-500/40' : 'bg-red-500/40'}`} />
                        <span className="text-[12px] font-bold text-white w-16">{t.symbol.replace('USDT', '')}</span>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          t.side === 'BUY'
                            ? 'bg-emerald-500/10 text-emerald-400/60'
                            : 'bg-red-500/10 text-red-400/60'
                        }`}>{t.side}</span>
                        <span className="flex-1" />
                        <span className="text-[10px] font-mono text-white/25">
                          ${t.entry_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                        </span>
                        <span className="text-white/10">{'\u2192'}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          t.exit_reason === 'TP_HIT' ? 'bg-emerald-500/10 text-emerald-400' :
                          t.exit_reason === 'SL_HIT' ? 'bg-red-500/10 text-red-400' :
                          'bg-white/[0.04] text-white/40'
                        }`}>
                          {t.exit_reason}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </Card>

          {/* CTA banner — compact */}
          <Card className="p-3 border-amber-500/[0.08] bg-gradient-to-r from-amber-500/[0.03] to-orange-500/[0.03]">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <Zap size={14} className="text-amber-400/60 shrink-0" />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-white/70 truncate">Contribute your API key to expand the hive</p>
                  <p className="text-[10px] text-white/25 truncate">More agents = deeper analysis, better signals</p>
                </div>
              </div>
              <a href="/register" className="shrink-0 inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-amber-500 to-orange-500 text-black text-[10px] font-bold rounded-lg hover:shadow-lg hover:shadow-amber-500/20 transition-all">
                Contribute <ArrowRight size={10} />
              </a>
            </div>
          </Card>
        </div>

        {/* ================================================================ */}
        {/* RIGHT COLUMN — Team Status + Agent Leaderboard                   */}
        {/* ================================================================ */}
        <div className="w-full lg:w-[280px] shrink-0 space-y-3">

          {/* Team Status Cards */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <SectionLabel>Team Status</SectionLabel>
              <a href="/org" className="text-[10px] text-amber-400/50 hover:text-amber-400 transition-colors flex items-center gap-0.5">
                Org <ChevronRight size={10} />
              </a>
            </div>
            <div className="space-y-1.5">
              {teams.map((team) => {
                const gradient = TEAM_COLORS[team.name.toLowerCase()] ?? 'from-white/20 to-white/10';
                const maxWeight = Math.max(...teams.map(t => t.weight), 1);
                return (
                  <div
                    key={team.id}
                    className="flex items-center gap-2.5 py-2 px-2.5 rounded-lg hover:bg-white/[0.02] transition-colors group relative overflow-hidden"
                  >
                    {/* Gradient left border */}
                    <div className={`absolute left-0 top-0 bottom-0 w-[2px] bg-gradient-to-b ${gradient}`} />

                    <div className="flex-1 min-w-0 ml-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[12px] font-semibold capitalize truncate text-white">{team.name}</span>
                        <StatusDot active={team.active_agent_count > 0} />
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-white/25">
                          {team.active_agent_count}/{team.agent_count} agents
                        </span>
                        <span className="text-[10px] font-mono text-white/25">{team.weight.toFixed(1)}x</span>
                      </div>
                      {/* Weight bar */}
                      <div className="mt-1.5 h-[3px] rounded-full bg-white/[0.04] overflow-hidden">
                        <div
                          className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all duration-500`}
                          style={{ width: `${(team.weight / maxWeight) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Agent Leaderboard */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <SectionLabel>Agent Leaderboard</SectionLabel>
              <a href="/agents" className="text-[10px] text-amber-400/50 hover:text-amber-400 transition-colors flex items-center gap-0.5">
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
                    {/* Rank */}
                    <span className="text-[10px] font-mono text-white/15 w-3 text-right">{i + 1}</span>

                    {/* Gradient avatar */}
                    <div className={`w-7 h-7 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center shrink-0`}>
                      <span className="text-[10px] font-bold text-white/90">{initial}</span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-white truncate max-w-[120px]">
                          {agentClass.replace('Agent', '')}
                        </span>
                        <span className="text-[10px] font-mono tabular-nums text-white/40">
                          {agent.total_signals}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-0.5">
                        <span className="text-[9px] text-white/25 capitalize">{agent.team_name ?? 'unassigned'}</span>
                        {agent.accuracy > 0 && (
                          <span className="text-[9px] font-mono text-emerald-400/50">{(agent.accuracy * 100).toFixed(0)}%</span>
                        )}
                      </div>
                      {/* Signal count bar */}
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
            {topAgents.length === 0 && (
              <p className="text-xs text-white/25 text-center py-4">No agents registered</p>
            )}
          </Card>

          {/* Active Agent count card */}
          <Card className="p-4">
            <SectionLabel>System Status</SectionLabel>
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-white/50">Active Agents</span>
                <span className="text-[13px] font-mono tabular-nums font-bold text-white">{activeAgents.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-white/50">Pending</span>
                <span className="text-[13px] font-mono tabular-nums text-white/25">{agents.length - activeAgents.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-white/50">Teams</span>
                <span className="text-[13px] font-mono tabular-nums text-white/25">{teams.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-white/50">Cycles Run</span>
                <span className="text-[13px] font-mono tabular-nums text-white/25">{cycles.length}</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
