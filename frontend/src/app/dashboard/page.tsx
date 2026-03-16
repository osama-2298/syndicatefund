'use client';

import { useEffect, useState } from 'react';
import {
  Wallet, TrendingUp, TrendingDown, BarChart3, Bot,
  Zap, Shield, Activity, Clock, ArrowRight, Signal,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Position { symbol: string; side: string; entry_price: number; quantity: number; current_price: number; }
interface TradeEntry { symbol: string; side: string; entry_price: number; stop_loss: number; take_profit_1: number; conviction: number; confidence: number; risk_amount: number; exit_reason: string; asset_tier: string; }
interface CycleData { id: number; started_at: string; regime: string | null; coins_analyzed: number; signals_produced: number; orders_executed: number; duration_secs: number | null; }
interface AgentData { id: string; team_name: string | null; role: string; agent_class: string | null; status: string; total_signals: number; accuracy: number; provider: string; }
interface TeamData { id: string; name: string; active_agent_count: number; agent_count: number; weight: number; }

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [teams, setTeams] = useState<TeamData[]>([]);
  const [trades, setTrades] = useState<TradeEntry[]>([]);
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const [priceFlash, setPriceFlash] = useState<Record<string, 'up' | 'down' | ''>>({});
  const [loading, setLoading] = useState(true);

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

  // Poll live prices from Binance every 10 seconds
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
          const prev = livePrices[item.symbol];
          if (prev && price !== prev) {
            flashes[item.symbol] = price > prev ? 'up' : 'down';
          }
        }
        setLivePrices(newPrices);
        if (Object.keys(flashes).length > 0) {
          setPriceFlash(flashes);
          setTimeout(() => setPriceFlash({}), 1000);
        }
      } catch {}
    };

    fetchPrices();
    const interval = setInterval(fetchPrices, 10000);
    return () => clearInterval(interval);
  }, [portfolio]);

  const positions: Position[] = portfolio?.positions ?? [];
  const cash = portfolio?.cash ?? 100000;
  const invested = positions.reduce((s, p) => s + p.quantity * (p.current_price || p.entry_price), 0);
  const totalValue = cash + invested;
  const returnPct = ((totalValue - 100000) / 100000) * 100;
  const returnUsd = totalValue - 100000;

  // Build lookup: symbol -> trade entry (for SL/TP data)
  const openTradesBySymbol: Record<string, TradeEntry> = {};
  for (const t of trades) {
    if (t.exit_reason === 'OPEN') {
      openTradesBySymbol[t.symbol] = t;
    }
  }

  const activeAgents = agents.filter(a => ['founding', 'active', 'assigned'].includes(a.status));
  const totalSignals = agents.reduce((s, a) => s + a.total_signals, 0);
  const lastCycle = cycles?.[0];
  const totalOrders = cycles.reduce((s, c) => s + c.orders_executed, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={24} className="animate-spin text-amber-400" />
      </div>
    );
  }

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-white/40 mt-1">Autonomous AI hedge fund — {activeAgents.length} agents across {teams.length} teams</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="glass-card flex items-center gap-2 px-3 py-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
            </span>
            <span className="text-xs font-medium text-emerald-400">LIVE</span>
          </div>
          {lastCycle && (
            <div className="glass-card flex items-center gap-1.5 px-3 py-1.5">
              <Clock size={12} className="text-white/30" />
              <span className="text-xs text-white/40">{new Date(lastCycle.started_at).toLocaleTimeString()}</span>
            </div>
          )}
        </div>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5">
          <div className="flex items-start justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30">Portfolio</p>
            <Wallet size={16} className="text-white/10" />
          </div>
          <p className={`mt-2 text-2xl font-bold tracking-tight ${returnPct >= 0 ? 'text-white' : 'text-red-400'}`}>
            ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
          <div className={`mt-1.5 flex items-center gap-1 text-xs font-medium ${returnPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {returnPct >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}% (${returnUsd >= 0 ? '+' : ''}${returnUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })})
          </div>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-start justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30">Active Agents</p>
            <Bot size={16} className="text-white/10" />
          </div>
          <p className="mt-2 text-2xl font-bold tracking-tight">{activeAgents.length}</p>
          <p className="mt-1.5 text-xs text-white/40">{teams.length} teams · {agents.length - activeAgents.length} pending</p>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-start justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30">Signals Produced</p>
            <Zap size={16} className="text-white/10" />
          </div>
          <p className="mt-2 text-2xl font-bold tracking-tight">{totalSignals.toLocaleString()}</p>
          <p className="mt-1.5 text-xs text-white/40">{totalOrders} trades executed</p>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-start justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30">Deployed Capital</p>
            <BarChart3 size={16} className="text-white/10" />
          </div>
          <p className="mt-2 text-2xl font-bold tracking-tight">${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
          <p className="mt-1.5 text-xs text-white/40">${cash.toLocaleString(undefined, { maximumFractionDigits: 0 })} available</p>
        </div>
      </div>

      {/* Team Overview */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Analysis Teams</p>
          <a href="/org" className="text-xs text-amber-400/80 hover:text-amber-300 transition-colors flex items-center gap-1">
            Org Chart <ArrowRight size={12} />
          </a>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {teams.map((team) => (
            <div key={team.id} className="glass-card-hover p-3 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span className={`h-2 w-2 rounded-full ${team.active_agent_count > 0 ? 'bg-emerald-400' : 'bg-white/10'}`} />
                <span className="text-xs font-semibold capitalize truncate">{team.name}</span>
              </div>
              <div className="flex items-end justify-between">
                <span className="text-lg font-bold">{team.active_agent_count}</span>
                <span className="text-[10px] text-white/30">{team.weight.toFixed(1)}x</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Positions + Regime side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Open Positions - 2/3 width */}
        <div className="lg:col-span-2 glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Signal size={14} className="text-amber-400" />
              <h2 className="text-sm font-semibold">Open Positions</h2>
            </div>
            {positions.length > 0 && (
              <span className="text-xs text-white/40">${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })} invested</span>
            )}
          </div>
          {positions.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <BarChart3 size={28} className="mx-auto text-white/10 mb-3" />
              <p className="text-sm text-white/40">No open positions</p>
              <p className="text-xs text-white/20 mt-1">Next cycle will analyze markets and generate trades</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-[10px] font-semibold uppercase tracking-widest text-white/30 border-b border-white/[0.06]">
                  <th className="text-left px-4 py-2.5">Symbol</th>
                  <th className="text-left px-4 py-2.5">Side</th>
                  <th className="text-right px-4 py-2.5">Size</th>
                  <th className="text-right px-4 py-2.5">Entry</th>
                  <th className="text-right px-4 py-2.5">Live Price</th>
                  <th className="text-right px-4 py-2.5">SL</th>
                  <th className="text-right px-4 py-2.5">TP</th>
                  <th className="text-right px-4 py-2.5">P&L</th>
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
                  const conviction = trade?.conviction;
                  const riskAmt = trade?.risk_amount ?? 0;
                  const flash = priceFlash[pos.symbol];
                  return (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-semibold text-sm">{pos.symbol.replace('USDT', '')}</span>
                        {conviction != null && (
                          <span className="ml-1.5 text-[10px] text-white/30">{conviction}/10</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
                          pos.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20'
                            : 'bg-red-500/10 text-red-400 ring-red-500/20'
                        }`}>{pos.side}</span>
                      </td>
                      <td className="px-4 py-3 text-right text-sm">${size.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                      <td className="px-4 py-3 text-right text-sm text-white/40">${pos.entry_price.toLocaleString()}</td>
                      <td className={`px-4 py-3 text-right text-sm font-mono tabular-nums transition-colors duration-300 ${
                        flash === 'up' ? 'text-emerald-400 bg-emerald-400/5' :
                        flash === 'down' ? 'text-red-400 bg-red-400/5' : 'text-white'
                      }`}>
                        ${live.toLocaleString()}
                        <span className="ml-1 text-[9px] text-white/20">LIVE</span>
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-red-400/70">
                        {sl > 0 ? `$${sl.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '\u2014'}
                        {riskAmt > 0 && <span className="block text-[10px] text-white/30">-${riskAmt.toFixed(0)} risk</span>}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-emerald-400/70">
                        {tp > 0 ? `$${tp.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '\u2014'}
                      </td>
                      <td className={`px-4 py-3 text-right text-sm font-semibold ${pnlUsd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pnlUsd >= 0 ? '+' : ''}${pnlUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                        <span className="text-[10px] ml-1 opacity-60">({pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%)</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Right sidebar - Market Regime + Cycle info */}
        <div className="space-y-4">
          <div className="glass-card p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-3">Market Regime</p>
            {lastCycle?.regime ? (
              <>
                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold ring-1 ring-inset ${
                  lastCycle.regime === 'bull' ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20' :
                  lastCycle.regime === 'bear' ? 'bg-red-500/10 text-red-400 ring-red-500/20' :
                  lastCycle.regime === 'crisis' ? 'bg-red-900/20 text-red-300 ring-red-500/30' :
                  'bg-amber-500/10 text-amber-400 ring-amber-500/20'
                }`}>
                  {lastCycle.regime === 'bull' ? <TrendingUp size={14} /> : lastCycle.regime === 'bear' ? <TrendingDown size={14} /> : <Shield size={14} />}
                  {lastCycle.regime.toUpperCase()}
                </div>
                <p className="text-xs text-white/30 mt-2">Set by CEO agent each cycle</p>
              </>
            ) : (
              <p className="text-sm text-white/40">Awaiting first cycle</p>
            )}
          </div>

          <div className="glass-card p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-3">Cycle Pipeline</p>
            <div className="space-y-2">
              {['Intelligence', 'CEO Directive', 'Coin Selection', 'Agent Analysis', 'Aggregation', 'Risk Check', 'Execution'].map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <span className="w-5 text-[10px] text-white/20 text-right">{i + 1}</span>
                  <div className={`flex-1 text-xs py-1 px-2 rounded ${
                    lastCycle ? 'bg-emerald-500/5 text-emerald-400/60 ring-1 ring-inset ring-emerald-500/10'
                      : 'bg-white/[0.02] text-white/20 ring-1 ring-inset ring-white/[0.04]'
                  }`}>{step}</div>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-white/30 mt-3">Runs every 4h on UTC boundaries</p>
          </div>
        </div>
      </div>

      {/* Recent Cycles */}
      {cycles.length > 0 && (
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={14} className="text-amber-400" />
              <h2 className="text-sm font-semibold">Recent Cycles</h2>
            </div>
            <a href="/cycles" className="text-xs text-amber-400/80 hover:text-amber-300 transition-colors flex items-center gap-1">
              View all <ArrowRight size={12} />
            </a>
          </div>
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-white/30 border-b border-white/[0.06]">
                <th className="text-left px-5 py-2.5">#</th>
                <th className="text-left px-5 py-2.5">Time</th>
                <th className="text-left px-5 py-2.5">Regime</th>
                <th className="text-right px-5 py-2.5">Coins</th>
                <th className="text-right px-5 py-2.5">Signals</th>
                <th className="text-right px-5 py-2.5">Trades</th>
                <th className="text-right px-5 py-2.5">Duration</th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((c) => (
                <tr key={c.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-3 text-sm text-white/40">{c.id}</td>
                  <td className="px-5 py-3 text-sm">{new Date(c.started_at).toLocaleString()}</td>
                  <td className="px-5 py-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
                      c.regime === 'bull' ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20' :
                      c.regime === 'bear' ? 'bg-red-500/10 text-red-400 ring-red-500/20' :
                      'bg-white/[0.04] text-white/40 ring-white/[0.06]'
                    }`}>{(c.regime ?? 'N/A').toUpperCase()}</span>
                  </td>
                  <td className="px-5 py-3 text-right text-sm">{c.coins_analyzed}</td>
                  <td className="px-5 py-3 text-right text-sm">{c.signals_produced}</td>
                  <td className="px-5 py-3 text-right text-sm">{c.orders_executed}</td>
                  <td className="px-5 py-3 text-right text-sm text-white/40">{c.duration_secs ? `${Math.round(c.duration_secs)}s` : '\u2014'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* CTA */}
      <div className="glass-card p-6 border-amber-400/10 bg-gradient-to-r from-amber-500/[0.04] to-orange-500/[0.04]">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold mb-1">Contribute your API key to expand the hive</h3>
            <p className="text-xs text-white/40">More agents = more coins scanned, deeper analysis, better signals. Your key, your agents.</p>
          </div>
          <a href="/register" className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-black text-xs font-bold rounded-xl hover:shadow-lg hover:shadow-amber-500/20 transition-all">
            Contribute <ArrowRight size={14} />
          </a>
        </div>
      </div>
    </div>
  );
}
