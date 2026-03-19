'use client';

import { useEffect, useState, useMemo } from 'react';
import { Loader2, Radio, Users, Hash, ChevronDown, ChevronUp, MessageSquare, TrendingUp, Shield, BarChart3, Zap, Award } from 'lucide-react';
import { API_BASE } from '@/lib/api';
import type { AgentComm } from '@/lib/types';
import { COMM_TYPE_CONFIG } from '@/lib/constants';
import CommCard from '@/components/CommCard';

/* ------------------------------------------------------------------ */
/*  FILTER TABS                                                        */
/* ------------------------------------------------------------------ */

interface FilterTab {
  key: string | null;
  label: string;
  types: string[];
  icon: typeof Radio;
}

const filterTabs: FilterTab[] = [
  { key: null, label: 'All', types: [], icon: Radio },
  { key: 'agents', label: 'Agents', types: ['agent_signal'], icon: Users },
  { key: 'managers', label: 'Managers', types: ['manager_synthesis'], icon: BarChart3 },
  { key: 'executives', label: 'Executives', types: ['ceo_directive', 'coo_selection', 'cro_rules', 'ceo_review'], icon: Shield },
  { key: 'trades', label: 'Trades', types: ['aggregation', 'trade_execution'], icon: TrendingUp },
];

const DEFAULT_TEAMS = ['technical', 'sentiment', 'fundamental', 'macro', 'onchain'];

/* ------------------------------------------------------------------ */
/*  HELPERS                                                            */
/* ------------------------------------------------------------------ */

function groupByCycle(comms: AgentComm[]): Map<number | null, AgentComm[]> {
  const groups = new Map<number | null, AgentComm[]>();
  for (const c of comms) {
    const key = c.cycle_id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(c);
  }
  return groups;
}

function orderWithinCycle(comms: AgentComm[]): AgentComm[] {
  const typeOrder: Record<string, number> = {
    ceo_directive: 0, coo_selection: 1, cro_rules: 2,
    agent_signal: 3, manager_synthesis: 4, aggregation: 5,
    trade_execution: 6, ceo_review: 7,
  };
  return [...comms].sort((a, b) => {
    const oa = typeOrder[a.comm_type] ?? 3;
    const ob = typeOrder[b.comm_type] ?? 3;
    if (oa !== ob) return oa - ob;
    if (a.symbol && b.symbol && a.symbol !== b.symbol) return a.symbol.localeCompare(b.symbol);
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });
}

/* ------------------------------------------------------------------ */
/*  SECTION HEADERS                                                    */
/* ------------------------------------------------------------------ */

function SectionDivider({ label, icon: Icon, color = 'text-syn-muted' }: { label: string; icon: typeof Radio; color?: string }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="h-px flex-1 bg-syn-border/50" />
      <div className={`flex items-center gap-1.5 ${color}`}>
        <Icon size={12} />
        <span className="text-[10px] font-bold uppercase tracking-[0.15em]">{label}</span>
      </div>
      <div className="h-px flex-1 bg-syn-border/50" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  CYCLE SECTION                                                      */
/* ------------------------------------------------------------------ */

function CycleSection({
  cycleId,
  comms,
  isExpanded,
  onToggle,
}: {
  cycleId: number | null;
  comms: AgentComm[];
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const ordered = useMemo(() => orderWithinCycle(comms), [comms]);

  const ceoDirective = ordered.find((c) => c.comm_type === 'ceo_directive');
  const regime = ceoDirective?.metadata?.regime || ceoDirective?.direction || '';
  const firstComm = ordered[0];

  // Group by pipeline stage
  const execComms = ordered.filter((c) => ['ceo_directive', 'coo_selection', 'cro_rules'].includes(c.comm_type));
  const reviewComms = ordered.filter((c) => c.comm_type === 'ceo_review');
  const tradeComms = ordered.filter((c) => c.comm_type === 'trade_execution');
  const aggregationComms = ordered.filter((c) => c.comm_type === 'aggregation');

  // Group agent signals + manager synthesis by symbol
  const signalComms = ordered.filter((c) => ['agent_signal', 'manager_synthesis'].includes(c.comm_type));
  const symbolGroups = new Map<string, AgentComm[]>();
  for (const c of signalComms) {
    const sym = c.symbol || '_none';
    if (!symbolGroups.has(sym)) symbolGroups.set(sym, []);
    symbolGroups.get(sym)!.push(c);
  }
  const sortedSymbols = Array.from(symbolGroups.keys()).filter(s => s !== '_none').sort();

  // Stats
  const agentCount = new Set(ordered.filter(c => c.comm_type === 'agent_signal').map(c => c.agent_class)).size;
  const coinCount = new Set(ordered.map(c => c.symbol).filter(Boolean)).size;

  return (
    <div className="border border-syn-border rounded-xl overflow-hidden bg-syn-surface/30">
      {/* Cycle header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 sm:px-5 py-3.5 bg-syn-surface hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">
              {cycleId !== null ? `Cycle #${cycleId}` : 'Latest Cycle'}
            </span>
            {regime && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                regime.toLowerCase().includes('bull') ? 'text-emerald-400 bg-emerald-400/10' :
                regime.toLowerCase().includes('bear') ? 'text-red-400 bg-red-400/10' :
                regime.toLowerCase().includes('crisis') ? 'text-red-300 bg-red-900/20' :
                'text-amber-400 bg-amber-400/10'
              }`}>
                {regime.toUpperCase()}
              </span>
            )}
          </div>
          <div className="hidden sm:flex items-center gap-3 text-[10px] text-syn-text-tertiary">
            <span>{comms.length} comms</span>
            <span className="text-syn-border">|</span>
            <span>{agentCount} agents</span>
            <span className="text-syn-border">|</span>
            <span>{coinCount} coins</span>
            {tradeComms.length > 0 && (
              <>
                <span className="text-syn-border">|</span>
                <span className="text-emerald-400">{tradeComms.length} trades</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {firstComm && (
            <span className="text-[10px] text-syn-text-tertiary hidden sm:inline">
              {new Date(firstComm.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              {' '}
              {new Date(firstComm.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })} UTC
            </span>
          )}
          {isExpanded ? <ChevronUp size={16} className="text-syn-text-tertiary" /> : <ChevronDown size={16} className="text-syn-text-tertiary" />}
        </div>
      </button>

      {/* Cycle content — pipeline stages */}
      {isExpanded && (
        <div className="px-4 sm:px-5 py-4 space-y-4 bg-syn-bg/50 border-t border-syn-border/50">

          {/* Stage 1: Executive Decisions */}
          {execComms.length > 0 && (
            <div className="space-y-3">
              <SectionDivider label="Executive Decisions" icon={Shield} color="text-amber-400/70" />
              <div className="space-y-3">
                {execComms.map((c) => <CommCard key={c.id} comm={c} />)}
              </div>
            </div>
          )}

          {/* Stage 2: Agent Analysis by coin */}
          {sortedSymbols.length > 0 && (
            <div className="space-y-4">
              <SectionDivider label="Agent Analysis" icon={MessageSquare} color="text-blue-400/70" />
              {sortedSymbols.map((sym) => {
                const symComms = symbolGroups.get(sym) || [];
                const agents = symComms.filter(c => c.comm_type === 'agent_signal');
                const managers = symComms.filter(c => c.comm_type === 'manager_synthesis');

                return (
                  <div key={sym} className="space-y-2">
                    {/* Coin header */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-white/80">{sym.replace('USDT', '')}</span>
                      <span className="text-[10px] text-syn-text-tertiary">{agents.length} signals</span>
                      <div className="h-px flex-1 bg-syn-border/30" />
                    </div>
                    {/* Agent signals */}
                    <div className="grid gap-2 sm:grid-cols-2">
                      {agents.map((c) => <CommCard key={c.id} comm={c} />)}
                    </div>
                    {/* Manager synthesis */}
                    {managers.length > 0 && (
                      <div className="space-y-2">
                        {managers.map((c) => <CommCard key={c.id} comm={c} />)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Stage 3: Signal Aggregation */}
          {aggregationComms.length > 0 && (
            <div className="space-y-3">
              <SectionDivider label="Signal Aggregation" icon={BarChart3} color="text-emerald-400/70" />
              <div className="grid gap-2 sm:grid-cols-2">
                {aggregationComms.map((c) => <CommCard key={c.id} comm={c} />)}
              </div>
            </div>
          )}

          {/* Stage 4: Trade Execution */}
          {tradeComms.length > 0 && (
            <div className="space-y-3">
              <SectionDivider label="Trade Execution" icon={Zap} color="text-green-400/70" />
              <div className="grid gap-2 sm:grid-cols-2">
                {tradeComms.map((c) => <CommCard key={c.id} comm={c} />)}
              </div>
            </div>
          )}

          {/* Stage 5: CEO Review */}
          {reviewComms.length > 0 && (
            <div className="space-y-3">
              <SectionDivider label="CEO Review" icon={Award} color="text-violet-400/70" />
              {reviewComms.map((c) => <CommCard key={c.id} comm={c} />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN PAGE                                                          */
/* ------------------------------------------------------------------ */

export default function CommsPage() {
  const [comms, setComms] = useState<AgentComm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [teamFilter, setTeamFilter] = useState('all');
  const [symbolFilter, setSymbolFilter] = useState('all');
  const [expandedCycles, setExpandedCycles] = useState<Set<number | null>>(new Set());
  const [limit, setLimit] = useState(200);

  useEffect(() => {
    setLoading(true);
    setError(false);
    const qs = new URLSearchParams();
    qs.set('limit', String(limit));
    if (teamFilter !== 'all') qs.set('team', teamFilter);
    if (symbolFilter !== 'all') qs.set('symbol', symbolFilter);

    const tab = filterTabs.find((t) => t.key === activeTab);
    if (tab && tab.types.length === 1) qs.set('comm_type', tab.types[0]);

    fetch(`${API_BASE}/api/v1/comms?${qs}`)
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (!Array.isArray(data)) throw new Error('Invalid response');
        setComms(data);
        if (data.length > 0) {
          const latestCycleId = data[0]?.cycle_id;
          setExpandedCycles(new Set([latestCycleId]));
        }
      })
      .catch(() => { setComms([]); setError(true); })
      .finally(() => setLoading(false));
  }, [activeTab, teamFilter, symbolFilter, limit]);

  // Client-side filter for multi-type tabs
  const filteredComms = useMemo(() => {
    const tab = filterTabs.find((t) => t.key === activeTab);
    if (!tab || tab.types.length <= 1) return comms;
    return comms.filter((c) => tab.types.includes(c.comm_type));
  }, [comms, activeTab]);

  // Unique symbols for filter
  const symbols = useMemo(() => {
    const s = new Set(comms.map((c) => c.symbol).filter((v): v is string => Boolean(v)));
    return ['all', ...Array.from(s).sort()];
  }, [comms]);

  // Dynamic team list
  const teamOptions = useMemo(() => {
    const fromData = comms.map((c) => c.team).filter((v): v is string => Boolean(v));
    const merged = new Set(DEFAULT_TEAMS.concat(fromData));
    return ['all', ...Array.from(merged).sort()];
  }, [comms]);

  // Group by cycle
  const cycleGroups = useMemo(() => groupByCycle(filteredComms), [filteredComms]);
  const cycleIds = useMemo(() => {
    return Array.from(cycleGroups.keys()).sort((a, b) => (b ?? 0) - (a ?? 0));
  }, [cycleGroups]);

  // Stats
  const totalComms = filteredComms.length;
  const uniqueAgents = new Set(filteredComms.map((c) => c.agent_class).filter(Boolean)).size;
  const latestCycleId = cycleIds[0];
  const totalCycles = cycleIds.length;

  const toggleCycle = (id: number | null) => {
    setExpandedCycles((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Agent Comms</h1>
        <p className="text-sm text-syn-muted mt-1">
          Full transparency. Every agent&apos;s analysis, every decision, nothing hidden.
        </p>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-4 gap-2 sm:gap-3">
        {[
          { label: 'Total Comms', value: totalComms },
          { label: 'Active Agents', value: uniqueAgents },
          { label: 'Cycles', value: totalCycles },
          { label: 'Latest Cycle', value: latestCycleId != null ? `#${latestCycleId}` : '--' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-syn-surface border border-syn-border rounded-xl px-3 py-2.5 sm:px-4 sm:py-3">
            <p className="text-[9px] sm:text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">{label}</p>
            <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-white/90">{value}</p>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        {/* Type tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {filterTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key ?? 'all'}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg whitespace-nowrap transition-all duration-200 ${
                  isActive
                    ? 'bg-syn-accent text-white shadow-lg shadow-syn-accent/20'
                    : 'bg-syn-surface text-syn-text-secondary hover:text-white border border-syn-border hover:border-syn-border-hover'
                }`}
              >
                <Icon size={12} className={isActive ? 'text-white' : 'text-syn-text-tertiary'} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Dropdown filters */}
        <div className="flex items-center gap-2 sm:ml-auto">
          <select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            className="text-xs bg-syn-surface border border-syn-border rounded-lg px-2.5 py-1.5 text-syn-text-secondary hover:border-syn-border-hover transition-colors focus:outline-none focus:ring-1 focus:ring-syn-accent/50"
          >
            {teamOptions.map((t) => (
              <option key={t} value={t}>{t === 'all' ? 'All Teams' : t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
          <select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="text-xs bg-syn-surface border border-syn-border rounded-lg px-2.5 py-1.5 text-syn-text-secondary hover:border-syn-border-hover transition-colors focus:outline-none focus:ring-1 focus:ring-syn-accent/50"
          >
            {symbols.map((s) => (
              <option key={s} value={s}>{s === 'all' ? 'All Coins' : s.replace('USDT', '')}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Feed */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 className="animate-spin text-syn-accent" size={28} />
          <p className="text-xs text-syn-muted">Loading agent communications...</p>
        </div>
      ) : error && filteredComms.length === 0 ? (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-10 text-center">
          <Radio size={36} className="mx-auto text-white/10 mb-3" />
          <p className="text-sm text-syn-muted">Could not load comms data</p>
          <p className="text-xs text-syn-muted/50 mt-1">Ensure the API server is running</p>
        </div>
      ) : filteredComms.length === 0 ? (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-10 sm:p-14 text-center">
          <div className="w-16 h-16 rounded-2xl bg-syn-accent/5 border border-syn-accent/10 flex items-center justify-center mx-auto mb-4">
            <Radio size={28} className="text-syn-accent/40" />
          </div>
          <p className="text-sm font-medium text-syn-text-secondary">No agent comms yet</p>
          <p className="text-xs text-syn-muted mt-2 max-w-sm mx-auto">
            Communications will appear here after the next trading cycle completes. The pipeline runs every 4 hours &mdash; each cycle produces 50+ agent messages.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {cycleIds.map((cycleId) => (
            <CycleSection
              key={cycleId ?? 'null'}
              cycleId={cycleId}
              comms={cycleGroups.get(cycleId) || []}
              isExpanded={expandedCycles.has(cycleId)}
              onToggle={() => toggleCycle(cycleId)}
            />
          ))}

          {/* Load More */}
          {filteredComms.length >= limit && (
            <div className="text-center py-2">
              <button
                onClick={() => { setLoading(true); setLimit((prev) => prev + 200); }}
                disabled={loading}
                className="text-sm text-syn-accent hover:text-syn-accent-hover font-medium transition-colors disabled:opacity-50 px-4 py-2 rounded-lg hover:bg-syn-accent/5"
              >
                {loading ? 'Loading...' : 'Load More Cycles'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
