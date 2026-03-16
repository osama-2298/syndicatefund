'use client';

import { useEffect, useState } from 'react';
import {
  Activity, Play, Brain, Search, Target, Shield, Users, Scale,
  CheckCircle, XCircle, DollarSign, Swords, BarChart3,
  TrendingUp, TrendingDown, ChevronDown, ChevronRight, Clock,
  ArrowRight, Zap,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PipelineEvent {
  id: string;
  cycle_id: number | null;
  event_type: string;
  timestamp: string;
  stage: string;
  actor: string;
  title: string;
  detail: Record<string, any> | null;
  elapsed_ms: number | null;
}

interface CycleData {
  id: number;
  started_at: string;
  completed_at: string | null;
  regime: string | null;
  coins_analyzed: number;
  signals_produced: number;
  orders_executed: number;
  duration_secs: number | null;
}

// ── Pipeline Flow Node ──
function FlowNode({ icon: Icon, label, value, color, active }: {
  icon: typeof Brain;
  label: string;
  value: string;
  color: string;
  active: boolean;
}) {
  return (
    <div className={`flex flex-col items-center gap-1 ${active ? 'opacity-100' : 'opacity-30'}`}>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${active ? color : 'bg-white/[0.03]'}`}>
        <Icon size={18} className={active ? 'text-white' : 'text-white/20'} />
      </div>
      <span className="text-[10px] font-medium text-hive-muted">{label}</span>
      {value && <span className="text-[11px] font-bold">{value}</span>}
    </div>
  );
}

function FlowArrow() {
  return <ArrowRight size={14} className="text-white/10 mt-[-8px] shrink-0" />;
}

// ── Coin Decision Card ──
function CoinCard({ symbol, action, confidence, consensus, blocked, reason, bullTeams, bearTeams, polarization }: {
  symbol: string;
  action: string;
  confidence: number;
  consensus: number;
  blocked: boolean;
  reason: string;
  bullTeams: { team: string; score: number }[];
  bearTeams: { team: string; score: number }[];
  polarization: number;
}) {
  const base = symbol.replace('USDT', '');
  const confPct = Math.round(confidence * 100);
  const hasFight = bullTeams.length > 0 && bearTeams.length > 0;
  const totalBull = bullTeams.reduce((s, t) => s + Math.abs(t.score), 0);
  const totalBear = bearTeams.reduce((s, t) => s + Math.abs(t.score), 0);
  const bullPct = totalBull + totalBear > 0 ? (totalBull / (totalBull + totalBear)) * 100 : 50;

  return (
    <div className={`rounded-xl border p-3 ${
      blocked ? 'border-white/[0.04] bg-white/[0.01]' :
      action === 'BUY' ? 'border-emerald-500/20 bg-emerald-500/[0.03]' :
      action === 'SELL' || action === 'SHORT' ? 'border-red-500/20 bg-red-500/[0.03]' :
      'border-white/[0.04] bg-white/[0.01]'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold">{base}</span>
        {blocked ? (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/[0.04] text-hive-muted ring-1 ring-inset ring-white/[0.06]">BLOCKED</span>
        ) : (
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
            action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20' :
            action === 'SELL' || action === 'SHORT' ? 'bg-red-500/10 text-red-400 ring-red-500/20' :
            'bg-white/[0.04] text-hive-muted ring-white/[0.06]'
          }`}>{action}</span>
        )}
      </div>

      {/* Bull vs Bear bar */}
      {hasFight ? (
        <div className="mb-2">
          <div className="flex h-2 rounded-full overflow-hidden">
            <div className="bg-emerald-500 transition-all" style={{ width: `${bullPct}%` }} />
            <div className="bg-red-500 transition-all" style={{ width: `${100 - bullPct}%` }} />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[9px] text-emerald-400">{bullTeams.length} bull</span>
            <span className="text-[9px] text-red-400">{bearTeams.length} bear</span>
          </div>
        </div>
      ) : (
        <div className="mb-2">
          <div className="h-2 rounded-full overflow-hidden bg-white/[0.04]">
            <div className={`h-full rounded-full ${
              action === 'BUY' ? 'bg-emerald-500' : action === 'SELL' || action === 'SHORT' ? 'bg-red-500' : 'bg-white/10'
            }`} style={{ width: `${confPct}%` }} />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[9px] text-hive-muted">{confPct}% confidence</span>
          </div>
        </div>
      )}

      {/* Reason if blocked */}
      {blocked && reason && (
        <p className="text-[9px] text-hive-muted/60 truncate">{reason}</p>
      )}
      {polarization > 0.5 && (
        <div className="flex items-center gap-1 mt-1">
          <Swords size={10} className="text-red-400" />
          <span className="text-[9px] text-red-400 font-medium">{Math.round(polarization * 100)}% split</span>
        </div>
      )}
    </div>
  );
}

// ── Main Cycle Card ──
function CycleCard({ cycle, events, defaultOpen }: { cycle: CycleData; events: PipelineEvent[]; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  const regime = cycle.regime || 'unknown';
  const regimeColor = regime === 'bull' ? 'text-emerald-400 bg-emerald-500/10 ring-emerald-500/20'
    : regime === 'bear' ? 'text-red-400 bg-red-500/10 ring-red-500/20'
    : regime === 'crisis' ? 'text-red-300 bg-red-900/20 ring-red-500/30'
    : 'text-amber-400 bg-amber-500/10 ring-amber-500/20';
  const RegimeIcon = regime === 'bull' ? TrendingUp : regime === 'bear' ? TrendingDown : Shield;

  // Extract data from events
  const ceoEvent = events.find(e => e.event_type === 'ceo_directive');
  const cooEvent = events.find(e => e.event_type === 'coo_selection' && e.actor !== 'Hot Coin Detector');
  const riskEvent = events.find(e => e.event_type === 'risk_check');
  const pmEvent = events.find(e => e.event_type === 'pm_review');
  const disagreements = events.filter(e => e.event_type === 'disagreement');
  const tradesExecuted = events.filter(e => e.event_type === 'trade_executed');
  const verdicts = events.filter(e => e.event_type === 'verdict');
  const aggregations = events.filter(e => e.event_type === 'aggregation_result');

  const nCoins = cooEvent?.detail?.coins?.length || cycle.coins_analyzed || 0;
  const nSignals = cycle.signals_produced || aggregations.length || 0;
  const nPassed = riskEvent?.detail?.passed || 0;
  const nApprovedPM = pmEvent?.detail?.orders_after || 0;
  const nTrades = tradesExecuted.length || cycle.orders_executed || 0;
  const nClashes = disagreements.length;

  // Build coin decision data by merging verdicts + disagreements
  const coinData: Record<string, {
    symbol: string; action: string; confidence: number; consensus: number;
    blocked: boolean; reason: string;
    bullTeams: { team: string; score: number }[];
    bearTeams: { team: string; score: number }[];
    polarization: number;
  }> = {};

  for (const v of verdicts) {
    const sym = v.detail?.symbol || '';
    coinData[sym] = {
      symbol: sym,
      action: v.detail?.action || 'HOLD',
      confidence: v.detail?.confidence || 0,
      consensus: v.detail?.consensus || 0,
      blocked: v.detail?.blocked || false,
      reason: v.detail?.reason || '',
      bullTeams: [], bearTeams: [], polarization: 0,
    };
  }
  for (const d of disagreements) {
    const sym = d.detail?.symbol || '';
    if (coinData[sym]) {
      coinData[sym].bullTeams = d.detail?.bullish_teams || [];
      coinData[sym].bearTeams = d.detail?.bearish_teams || [];
      coinData[sym].polarization = d.detail?.polarization || 0;
    } else {
      coinData[sym] = {
        symbol: sym, action: 'HOLD', confidence: 0, consensus: 0,
        blocked: true, reason: 'teams undecided',
        bullTeams: d.detail?.bullish_teams || [],
        bearTeams: d.detail?.bearish_teams || [],
        polarization: d.detail?.polarization || 0,
      };
    }
  }
  const coins = Object.values(coinData);

  return (
    <div className="glass-card overflow-hidden">
      {/* Cycle header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-6 py-5 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-4">
          {open ? <ChevronDown size={16} className="text-hive-muted" /> : <ChevronRight size={16} className="text-hive-muted" />}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold ring-1 ring-inset ${regimeColor}`}>
            <RegimeIcon size={12} />
            {regime.toUpperCase()}
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold">Cycle #{cycle.id}</h3>
            <p className="text-[10px] text-hive-muted mt-0.5">
              {new Date(cycle.started_at).toLocaleDateString()} at {new Date(cycle.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              {cycle.duration_secs ? ` — ${Math.round(cycle.duration_secs / 60)}min` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] bg-white/[0.04] px-2 py-1 rounded text-hive-muted">{nCoins} coins</span>
          {nTrades > 0 && (
            <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded font-medium">{nTrades} trades</span>
          )}
          {nClashes > 0 && (
            <span className="text-[10px] bg-red-500/10 text-red-400 px-2 py-1 rounded font-medium">{nClashes} clashes</span>
          )}
        </div>
      </button>

      {/* Expanded content */}
      {open && (
        <div className="border-t border-white/[0.06]">
          {/* ── Pipeline Flow Graph ── */}
          <div className="px-6 py-5 border-b border-white/[0.03]">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4">Pipeline Flow</p>
            <div className="flex items-start justify-between gap-2 overflow-x-auto">
              <FlowNode icon={Search} label="Intel" value={ceoEvent ? `F&G ${ceoEvent.detail?.regime || '?'}` : ''} color="bg-blue-500/20" active={true} />
              <FlowArrow />
              <FlowNode icon={Brain} label="CEO" value={regime.toUpperCase()} color={regime === 'bull' ? 'bg-emerald-500/20' : regime === 'bear' ? 'bg-red-500/20' : 'bg-amber-500/20'} active={!!ceoEvent} />
              <FlowArrow />
              <FlowNode icon={Target} label="Coins" value={`${nCoins}`} color="bg-amber-500/20" active={nCoins > 0} />
              <FlowArrow />
              <FlowNode icon={Users} label="Teams" value={`${nSignals} sig`} color="bg-blue-500/20" active={nSignals > 0} />
              <FlowArrow />
              <FlowNode icon={Swords} label="Clashes" value={nClashes > 0 ? `${nClashes}` : '0'} color="bg-red-500/20" active={nClashes > 0} />
              <FlowArrow />
              <FlowNode icon={Shield} label="Risk" value={`${nPassed} pass`} color="bg-orange-500/20" active={nPassed > 0} />
              <FlowArrow />
              <FlowNode icon={DollarSign} label="Trades" value={`${nTrades}`} color="bg-emerald-500/20" active={nTrades > 0} />
            </div>
          </div>

          {/* ── Coin Decision Cards ── */}
          {coins.length > 0 && (
            <div className="px-6 py-5 border-b border-white/[0.03]">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-3">Coin Decisions</p>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {coins.map((coin) => (
                  <CoinCard key={coin.symbol} {...coin} />
                ))}
              </div>
            </div>
          )}

          {/* ── Trades Executed ── */}
          {tradesExecuted.length > 0 && (
            <div className="px-6 py-4 border-b border-white/[0.03]">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-2">Trades Executed</p>
              <div className="space-y-2">
                {tradesExecuted.map((t) => {
                  const sym = (t.detail?.symbol || '').replace('USDT', '');
                  const side = t.detail?.side || '?';
                  return (
                    <div key={t.id} className="flex items-center gap-3">
                      <DollarSign size={14} className="text-emerald-400" />
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
                        side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20' : 'bg-red-500/10 text-red-400 ring-red-500/20'
                      }`}>{side}</span>
                      <span className="text-sm font-semibold">{sym}</span>
                      <span className="text-sm text-hive-muted">@ ${(t.detail?.price || 0).toLocaleString()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Replay link */}
          <div className="px-6 py-3 bg-white/[0.01]">
            <a href={`/cycles/${cycle.id}`} className="inline-flex items-center gap-2 text-xs text-hive-accent hover:text-amber-300 transition-colors font-medium">
              <Play size={12} /> Watch full replay step by step
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──
export default function ActivityPage() {
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [eventsByCycle, setEventsByCycle] = useState<Record<number, PipelineEvent[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/cycles?limit=10`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/events?limit=200`).then(r => r.json()).catch(() => []),
    ]).then(([cyclesData, eventsData]) => {
      let c: CycleData[] = Array.isArray(cyclesData) ? cyclesData : [];
      const e = Array.isArray(eventsData) ? eventsData : [];

      const grouped: Record<number, PipelineEvent[]> = {};
      const ungrouped: PipelineEvent[] = [];

      for (const event of e) {
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
      } else if (ungrouped.length > 0 && c.length === 0) {
        grouped[-1] = ungrouped;
        c = [{ id: -1, started_at: ungrouped[0]?.timestamp || '', completed_at: null, regime: null,
               coins_analyzed: 0, signals_produced: 0, orders_executed: 0, duration_secs: null }];
      }

      setCycles(c);
      for (const cid of Object.keys(grouped)) {
        grouped[Number(cid)] = grouped[Number(cid)].reverse();
      }
      setEventsByCycle(grouped);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={24} className="animate-spin text-hive-accent" />
      </div>
    );
  }

  const cyclesWithEvents = cycles.filter(c => (eventsByCycle[c.id] || []).length > 0);

  return (
    <div className="slide-up space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <Activity size={20} className="text-hive-accent" />
          <h1 className="text-2xl font-bold tracking-tight">Activity</h1>
        </div>
        <p className="text-sm text-hive-muted mt-1">
          Every decision the AI makes, organized by cycle. The latest cycle is expanded by default.
        </p>
      </div>

      {cyclesWithEvents.length === 0 ? (
        <div className="glass-card p-10 text-center">
          <Clock size={32} className="mx-auto text-white/10 mb-3" />
          <p className="text-sm text-hive-muted">No cycle activity recorded yet.</p>
          <p className="text-xs text-hive-muted/50 mt-1">The pipeline runs every 4 hours. Activity will appear here after the next cycle completes.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {cyclesWithEvents.map((cycle, i) => (
            <CycleCard
              key={cycle.id}
              cycle={cycle}
              events={eventsByCycle[cycle.id] || []}
              defaultOpen={i === 0}
            />
          ))}
        </div>
      )}
    </div>
  );
}
