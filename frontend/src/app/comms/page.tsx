'use client';

import { useEffect, useState, useMemo } from 'react';
import { Loader2, Radio, Users, Hash } from 'lucide-react';
import { API_BASE } from '@/lib/api';
import type { AgentComm } from '@/lib/types';
import { COMM_TYPE_CONFIG, AGENT_NAMES, MANAGER_NAMES, EXECUTIVE_NAMES } from '@/lib/constants';
import CommCard from '@/components/CommCard';

/* ------------------------------------------------------------------ */
/*  FILTER TABS                                                        */
/* ------------------------------------------------------------------ */

interface FilterTab {
  key: string | null;
  label: string;
  types: string[];
}

const filterTabs: FilterTab[] = [
  { key: null, label: 'All', types: [] },
  { key: 'agents', label: 'Agents', types: ['agent_signal'] },
  { key: 'managers', label: 'Managers', types: ['manager_synthesis'] },
  { key: 'executives', label: 'Executives', types: ['ceo_directive', 'coo_selection', 'cro_rules', 'ceo_review'] },
  { key: 'trades', label: 'Trades', types: ['aggregation', 'trade_execution'] },
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

function groupBySymbol(comms: AgentComm[]): Map<string | null, AgentComm[]> {
  const groups = new Map<string | null, AgentComm[]>();
  for (const c of comms) {
    const key = c.symbol;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(c);
  }
  return groups;
}

function orderWithinCycle(comms: AgentComm[]): AgentComm[] {
  // Executive comms first, then by symbol, then trades/review last
  const typeOrder: Record<string, number> = {
    ceo_directive: 0,
    coo_selection: 1,
    cro_rules: 2,
    agent_signal: 3,
    manager_synthesis: 4,
    aggregation: 5,
    trade_execution: 6,
    ceo_review: 7,
  };
  return [...comms].sort((a, b) => {
    const oa = typeOrder[a.comm_type] ?? 3;
    const ob = typeOrder[b.comm_type] ?? 3;
    if (oa !== ob) return oa - ob;
    // Within same type, sort by symbol then by time
    if (a.symbol && b.symbol && a.symbol !== b.symbol) return a.symbol.localeCompare(b.symbol);
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });
}

/* ------------------------------------------------------------------ */
/*  COMPONENT                                                          */
/* ------------------------------------------------------------------ */

export default function CommsPage() {
  const [comms, setComms] = useState<AgentComm[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [teamFilter, setTeamFilter] = useState('all');
  const [symbolFilter, setSymbolFilter] = useState('all');
  const [expandedCycles, setExpandedCycles] = useState<Set<number | null>>(new Set());
  const [limit, setLimit] = useState(200);

  useEffect(() => {
    setLoading(true);
    const qs = new URLSearchParams();
    qs.set('limit', String(limit));
    if (teamFilter !== 'all') qs.set('team', teamFilter);
    if (symbolFilter !== 'all') qs.set('symbol', symbolFilter);

    const tab = filterTabs.find((t) => t.key === activeTab);
    if (tab && tab.types.length === 1) {
      qs.set('comm_type', tab.types[0]);
    }

    fetch(`${API_BASE}/api/v1/comms?${qs}`)
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (!Array.isArray(data)) throw new Error('Invalid response');
        setComms(data);
        // Auto-expand latest cycle
        if (data.length > 0) {
          const latestCycleId = data[0]?.cycle_id;
          setExpandedCycles(new Set([latestCycleId]));
        }
      })
      .catch(() => setComms([]))
      .finally(() => setLoading(false));
  }, [activeTab, teamFilter, symbolFilter, limit]);

  // Client-side filter for multi-type tabs
  const filteredComms = useMemo(() => {
    const tab = filterTabs.find((t) => t.key === activeTab);
    if (!tab || tab.types.length <= 1) return comms;
    return comms.filter((c) => tab.types.includes(c.comm_type));
  }, [comms, activeTab]);

  // Unique symbols for filter dropdown
  const symbols = useMemo(() => {
    const s = new Set(comms.map((c) => c.symbol).filter((v): v is string => Boolean(v)));
    return ['all', ...Array.from(s).sort()];
  }, [comms]);

  // Dynamic team list — includes contributor-created teams
  const teamOptions = useMemo(() => {
    const fromData = comms.map((c) => c.team).filter((v): v is string => Boolean(v));
    // Merge default teams + any new teams from data
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

  const toggleCycle = (id: number | null) => {
    setExpandedCycles((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Agent Comms</h1>
        <p className="text-syn-text-secondary mt-1 text-sm sm:text-base">
          Full transparency. Every agent&apos;s analysis, every decision, nothing hidden.
        </p>
      </div>

      {/* Stats Strip */}
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        {[
          { label: 'Total Comms', value: totalComms, icon: Radio },
          { label: 'Active Agents', value: uniqueAgents, icon: Users },
          { label: 'Latest Cycle', value: latestCycleId !== null && latestCycleId !== undefined ? `#${latestCycleId}` : '--', icon: Hash },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-syn-surface border border-syn-border rounded-xl p-3 sm:p-4">
            <div className="flex items-center gap-2 text-syn-text-tertiary mb-1">
              <Icon size={14} />
              <span className="text-xs">{label}</span>
            </div>
            <div className="text-lg sm:text-xl font-bold text-white">{value}</div>
          </div>
        ))}
      </div>

      {/* Filter Bar */}
      <div className="space-y-3">
        {/* Type tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {filterTabs.map((tab) => (
            <button
              key={tab.key ?? 'all'}
              onClick={() => setActiveTab(tab.key)}
              className={`text-xs font-medium px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
                activeTab === tab.key
                  ? 'bg-syn-accent text-white'
                  : 'bg-syn-surface text-syn-text-secondary hover:text-white border border-syn-border'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dropdowns row */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-syn-text-tertiary">Team:</label>
          <select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            className="text-xs bg-syn-surface border border-syn-border rounded-lg px-2 py-1.5 text-syn-text-secondary"
          >
            {teamOptions.map((t) => (
              <option key={t} value={t}>{t === 'all' ? 'All Teams' : t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>

          <label className="text-xs text-syn-text-tertiary">Coin:</label>
          <select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="text-xs bg-syn-surface border border-syn-border rounded-lg px-2 py-1.5 text-syn-text-secondary"
          >
            {symbols.map((s) => (
              <option key={s} value={s}>{s === 'all' ? 'All Coins' : s.replace('USDT', '')}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Feed */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-syn-accent" size={28} />
        </div>
      ) : filteredComms.length === 0 ? (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-8 sm:p-12 text-center">
          <Radio className="mx-auto text-syn-text-tertiary mb-3" size={32} />
          <p className="text-syn-text-secondary text-sm">No agent comms yet.</p>
          <p className="text-syn-text-tertiary text-xs mt-1">
            Comms will appear here after the next trading cycle completes.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {cycleIds.map((cycleId) => {
            const cycleComms = orderWithinCycle(cycleGroups.get(cycleId) || []);
            const isExpanded = expandedCycles.has(cycleId);
            const firstComm = cycleComms[0];
            const ceoDirective = cycleComms.find((c) => c.comm_type === 'ceo_directive');
            const regime = ceoDirective?.direction || ceoDirective?.metadata?.regime || '';

            // Group by symbol within cycle
            const symbolGroups = groupBySymbol(cycleComms.filter((c) => c.symbol));
            const execComms = cycleComms.filter((c) => ['ceo_directive', 'coo_selection', 'cro_rules'].includes(c.comm_type));
            const reviewComms = cycleComms.filter((c) => ['ceo_review'].includes(c.comm_type));
            const tradeComms = cycleComms.filter((c) => c.comm_type === 'trade_execution');

            return (
              <div key={cycleId ?? 'null'} className="border border-syn-border rounded-xl overflow-hidden">
                {/* Cycle header */}
                <button
                  onClick={() => toggleCycle(cycleId)}
                  className="w-full flex items-center justify-between px-4 sm:px-6 py-3 bg-syn-surface hover:bg-syn-surface-hover transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-white">
                      {cycleId !== null ? `Cycle #${cycleId}` : 'Latest Cycle'}
                    </span>
                    {regime && (
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 ${
                        regime.toLowerCase().includes('bull') ? 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20' :
                        regime.toLowerCase().includes('bear') ? 'text-red-400 bg-red-400/10 ring-red-400/20' :
                        'text-amber-400 bg-amber-400/10 ring-amber-400/20'
                      }`}>
                        {regime.toUpperCase()}
                      </span>
                    )}
                    <span className="text-xs text-syn-text-tertiary">{cycleComms.length} comms</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {firstComm && (
                      <span className="text-xs text-syn-text-tertiary">
                        {new Date(firstComm.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        {' '}
                        {new Date(firstComm.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })} UTC
                      </span>
                    )}
                    <span className="text-syn-text-tertiary text-xs">{isExpanded ? '\u25B2' : '\u25BC'}</span>
                  </div>
                </button>

                {/* Cycle content */}
                {isExpanded && (
                  <div className="px-4 sm:px-6 py-4 space-y-4 bg-syn-bg">
                    {/* Executive comms */}
                    {execComms.length > 0 && (
                      <div className="space-y-3">
                        {execComms.map((c) => (
                          <CommCard key={c.id} comm={c} />
                        ))}
                      </div>
                    )}

                    {/* Per-symbol sections */}
                    {Array.from(symbolGroups.entries())
                      .filter(([sym]) => sym !== null)
                      .sort(([a], [b]) => (a || '').localeCompare(b || ''))
                      .map(([sym, symComms]) => {
                        // Exclude executive/review/trade comms (already shown above/below)
                        const coinComms = symComms.filter((c) =>
                          ['agent_signal', 'manager_synthesis', 'aggregation'].includes(c.comm_type)
                        );
                        if (coinComms.length === 0) return null;

                        return (
                          <div key={sym}>
                            <div className="flex items-center gap-2 py-2">
                              <div className="h-px flex-1 bg-syn-border" />
                              <span className="text-xs font-mono font-bold text-syn-text-secondary">
                                {sym?.replace('USDT', '')}
                              </span>
                              <div className="h-px flex-1 bg-syn-border" />
                            </div>
                            <div className="space-y-3">
                              {coinComms.map((c) => (
                                <CommCard key={c.id} comm={c} />
                              ))}
                            </div>
                          </div>
                        );
                      })}

                    {/* Trade comms */}
                    {tradeComms.length > 0 && (
                      <div>
                        <div className="flex items-center gap-2 py-2">
                          <div className="h-px flex-1 bg-syn-border" />
                          <span className="text-xs font-mono font-bold text-emerald-400">TRADES</span>
                          <div className="h-px flex-1 bg-syn-border" />
                        </div>
                        <div className="space-y-3">
                          {tradeComms.map((c) => (
                            <CommCard key={c.id} comm={c} />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* CEO Review */}
                    {reviewComms.length > 0 && (
                      <div className="space-y-3">
                        {reviewComms.map((c) => (
                          <CommCard key={c.id} comm={c} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Load More */}
          {filteredComms.length >= limit && (
            <div className="text-center">
              <button
                onClick={() => { setLoading(true); setLimit((prev) => prev + 200); }}
                disabled={loading}
                className="text-sm text-syn-accent hover:text-syn-accent-hover font-medium transition-colors disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
