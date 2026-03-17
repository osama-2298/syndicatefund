'use client';

import { useEffect, useState, useRef } from 'react';
import {
  TrendingUp, TrendingDown, Shield, Activity, Clock, ArrowRight,
  ChevronRight, Zap, Swords,
} from 'lucide-react';
import CycleCard, { type CycleData, type PipelineEvent } from '@/components/CycleCard';
import { AGENT_COLORS, TEAM_COLORS } from '@/lib/constants';
import { API_BASE } from '@/lib/api';

interface Position { symbol: string; side: string; entry_price: number; quantity: number; current_price: number; }
interface TradeEntry { symbol: string; side: string; entry_price: number; stop_loss: number; take_profit_1: number; conviction: number; confidence: number; risk_amount: number; exit_reason: string; asset_tier: string; }
interface AgentData { id: string; team_name: string | null; role: string; agent_class: string | null; status: string; total_signals: number; accuracy: number; provider: string; }

// -- Animated Number --

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

// -- Sidebar: Disagreement Card --

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

// -- Sidebar: Leaderboard Card --

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

// -- Dashboard --

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [trades, setTrades] = useState<TradeEntry[]>([]);
  const [eventsByCycle, setEventsByCycle] = useState<Record<number, PipelineEvent[]>>({});
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const [priceFlash, setPriceFlash] = useState<Record<string, 'up' | 'down' | ''>>({});
  const [loading, setLoading] = useState(true);
  const livePricesRef = useRef<Record<string, number>>({});

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/portfolio`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/cycles?limit=3`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/agents`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/portfolio/trades`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/events?limit=200`).then(r => r.json()).catch(() => []),
    ]).then(([p, c, a, tr, evts]) => {
      setPortfolio(p);
      setCycles(c);
      setAgents(a);
      setTrades(Array.isArray(tr) ? tr : []);

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
    }).finally(() => setLoading(false));
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

  // Derived data
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

  const hasCycles = cycles.length > 0;
  const hasPositions = positions.length > 0;
  const hasData = hasCycles || hasPositions;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={20} className="animate-spin text-syn-accent" />
      </div>
    );
  }

  return (
    <div className="slide-up">
      {/* Portfolio Stats Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
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
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Agents</p>
          <p className="text-lg font-bold font-mono tabular-nums">{activeAgents.length}</p>
          <p className="text-[10px] text-syn-text-tertiary mt-1">{totalSignals.toLocaleString()} signals</p>
        </div>
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Regime</p>
          {lastCycle?.regime ? (
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
          ) : (
            <p className="text-xs text-syn-text-tertiary">Awaiting</p>
          )}
        </div>
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Positions</p>
          <p className="text-lg font-bold font-mono tabular-nums">{positions.length}</p>
          <p className="text-[10px] text-syn-text-tertiary mt-1">${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })} deployed</p>
        </div>
      </div>

      {/* Welcome message when no data */}
      {!hasData && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-10 text-center mb-6">
          <p className="text-sm text-syn-text-secondary font-medium mb-1">Welcome to Syndicate</p>
          <p className="text-xs text-syn-text-tertiary max-w-md mx-auto">
            The pipeline runs every 4 hours. Once the first cycle completes, you&apos;ll see the latest analysis here with positions and trade activity.
          </p>
        </div>
      )}

      {/* Main: Latest Cycle Hero + Sidebar */}
      {hasData && (
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Main column */}
          <div className="flex-1 min-w-0 space-y-4">
            {/* Latest cycle hero card */}
            {lastCycle && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-sm font-bold text-syn-text-secondary">Latest Cycle</h2>
                  <a href="/activity" className="text-[10px] text-syn-muted hover:text-syn-accent transition-colors flex items-center gap-0.5">
                    All activity <ChevronRight size={10} />
                  </a>
                </div>
                <CycleCard
                  cycle={lastCycle}
                  events={eventsByCycle[lastCycle.id] || []}
                  defaultOpen={true}
                />
              </div>
            )}

            {/* Positions Table */}
            {hasPositions && (
              <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-syn-border flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full bg-syn-accent" />
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
            <DisagreementSidebar />
            <LeaderboardSidebar agents={agents} />
          </div>
        </div>
      )}
    </div>
  );
}
