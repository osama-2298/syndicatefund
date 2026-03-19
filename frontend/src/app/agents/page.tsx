'use client';

import { useEffect, useMemo, useState } from 'react';
import { Loader2, Crown, Radio, Zap, BarChart3, Users, ChevronRight, Search } from 'lucide-react';
import Avatar from 'boring-avatars';
import { API_BASE } from '@/lib/api';
import {
  getPersonaByClass,
  STATUS_COLORS,
  getTeamGradient,
} from '@/lib/constants';
import type { AgentSummary } from '@/lib/types';

/* ------------------------------------------------------------------ */
/*  HELPERS                                                            */
/* ------------------------------------------------------------------ */

/** Resolve display metadata for any agent — known or unknown. */
function getAgentDisplay(agent: AgentSummary) {
  return getPersonaByClass(agent.agent_class, agent.role);
}

/* ------------------------------------------------------------------ */
/*  SUB-COMPONENTS                                                     */
/* ------------------------------------------------------------------ */

function SummaryStrip({ agents }: { agents: AgentSummary[] }) {
  const totalSignals = agents.reduce((s, a) => s + a.total_signals, 0);
  const withSignals = agents.filter(a => a.total_signals >= 5);
  const avgAccuracy = withSignals.length > 0
    ? withSignals.reduce((s, a) => s + a.accuracy, 0) / withSignals.length
    : 0;
  const founding = agents.filter(a => a.status === 'founding').length;
  const contributors = agents.length - founding;

  const stats = [
    { label: 'Total Agents', value: agents.length.toString(), icon: Users },
    { label: 'Founding', value: founding.toString(), icon: Crown },
    { label: 'Contributors', value: contributors.toString(), icon: BarChart3 },
    { label: 'Avg Accuracy', value: withSignals.length > 0 ? `${Math.round(avgAccuracy * 100)}%` : '\u2014', icon: BarChart3 },
    { label: 'Total Signals', value: totalSignals.toLocaleString(), icon: Radio },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-syn-surface border border-syn-border rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1.5">
            <stat.icon size={12} className="text-white/20" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">{stat.label}</p>
          </div>
          <p className="text-xl font-bold font-mono tabular-nums text-white/90">{stat.value}</p>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || 'text-gray-400 bg-gray-400/10 ring-gray-400/30';
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${color}`}>
      {status.toUpperCase()}
    </span>
  );
}

function TeamBadge({ teamName }: { teamName: string }) {
  const gradient = getTeamGradient(teamName);
  return (
    <span className="relative text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ring-white/[0.08] bg-white/[0.04] text-white/70">
      <span className={`absolute left-1 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-gradient-to-r ${gradient}`} />
      <span className="pl-2.5">{teamName.toUpperCase()}</span>
    </span>
  );
}

function AccuracyBar({ accuracy, signals }: { accuracy: number; signals: number }) {
  if (signals < 5) return <span className="text-white/15 text-xs font-mono">{'\u2014'}</span>;
  const pct = Math.round(accuracy * 100);
  const color = pct >= 60 ? 'bg-emerald-400' : pct >= 40 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1 bg-syn-border rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono tabular-nums text-white/60">{pct}%</span>
    </div>
  );
}

function TeamFilter({ teams, active, onChange }: {
  teams: string[];
  active: string | null;
  onChange: (team: string | null) => void;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        onClick={() => onChange(null)}
        className={`text-[10px] font-bold px-3 py-1 rounded-full ring-1 ring-inset transition-colors ${
          active === null
            ? 'text-white bg-white/[0.08] ring-white/20'
            : 'text-white/40 bg-transparent ring-white/[0.06] hover:text-white/60'
        }`}
      >
        ALL
      </button>
      {teams.map((team) => {
        const gradient = getTeamGradient(team);
        const isActive = active === team;
        return (
          <button
            key={team}
            onClick={() => onChange(isActive ? null : team)}
            className={`relative text-[10px] font-bold px-3 py-1 rounded-full ring-1 ring-inset transition-colors ${
              isActive
                ? 'text-white bg-white/[0.08] ring-white/20'
                : 'text-white/40 bg-transparent ring-white/[0.06] hover:text-white/60'
            }`}
          >
            <span className={`inline-block w-1.5 h-1.5 rounded-full bg-gradient-to-r ${gradient} mr-1.5 align-middle`} />
            {team.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentSummary }) {
  const { name, animal, title, colors } = getAgentDisplay(agent);
  const isFounding = agent.status === 'founding';
  const isQuarantined = agent.quarantine_signals_remaining > 0;

  return (
    <a href={`/agents/${agent.id}`} className="block group">
      <div className="bg-syn-surface border border-syn-border rounded-xl p-5 transition-all duration-200 hover:border-white/[0.12] hover:bg-white/[0.02]">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="relative flex-shrink-0">
            <div className="rounded-full overflow-hidden shadow-lg ring-1 ring-white/[0.06]">
              <Avatar
                name={name}
                variant="beam"
                size={52}
                colors={colors}
              />
            </div>
            {isFounding && (
              <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-syn-surface flex items-center justify-center border border-amber-500/40">
                <Crown size={10} className="text-amber-400" />
              </div>
            )}
          </div>

          {/* Identity */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white/90 truncate">{name}</h3>
              {animal && <span className="text-base flex-shrink-0" title={title}>{animal}</span>}
            </div>
            <p className="text-xs text-white/35 mt-0.5 truncate">{title}</p>
            <div className="flex items-center gap-2 mt-2">
              {agent.team_name && <TeamBadge teamName={agent.team_name} />}
            </div>
          </div>

          {/* Arrow hint */}
          <ChevronRight size={14} className="text-white/0 group-hover:text-white/20 transition-colors flex-shrink-0 mt-1" />
        </div>

        {/* Stats row */}
        <div className="mt-4 pt-3 border-t border-syn-border/40 flex items-center gap-3 flex-wrap">
          <StatusBadge status={agent.status} />

          <div className="flex items-center gap-1.5">
            <Radio size={10} className="text-white/20" />
            <span className="text-xs font-mono tabular-nums text-white/50">{agent.total_signals}</span>
          </div>

          <AccuracyBar accuracy={agent.accuracy} signals={agent.total_signals} />

          {isQuarantined && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-orange-400 bg-orange-400/10 ring-orange-400/30">
              Q: {agent.quarantine_signals_remaining} left
            </span>
          )}
        </div>
      </div>
    </a>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN PAGE                                                          */
/* ------------------------------------------------------------------ */

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const [teamFilter, setTeamFilter] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/agents`)
      .then((r) => r.json())
      .then((data) => {
        setAgents(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  // Derive unique team names from data (not hardcoded — scales with new teams)
  const teams = useMemo(() => {
    const set = new Set<string>();
    agents.forEach((a) => { if (a.team_name) set.add(a.team_name); });
    return Array.from(set).sort();
  }, [agents]);

  // Filter agents by search + team
  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    return agents.filter((agent) => {
      // Team filter
      if (teamFilter && agent.team_name !== teamFilter) return false;
      // Search filter — match against name, role, team, agent_class
      if (q) {
        const { name, title } = getAgentDisplay(agent);
        const haystack = `${name} ${title} ${agent.role} ${agent.team_name || ''} ${agent.agent_class || ''} ${agent.status}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [agents, search, teamFilter]);

  const founding = filtered.filter((a) => a.status === 'founding');
  const contributors = filtered.filter((a) => a.status !== 'founding');

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Agent Roster</h1>
        <p className="text-sm text-syn-text-secondary mt-1">
          {loading
            ? 'Loading roster...'
            : `${agents.length} analysts. Each one tracked, scored, and accountable. Underperformers get fired.`}
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-syn-surface border border-syn-border rounded-xl flex items-center justify-center py-24">
          <Loader2 size={24} className="text-white/20 animate-spin" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="bg-syn-surface border border-syn-border rounded-xl flex flex-col items-center justify-center py-24">
          <Zap size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-syn-text-secondary">Could not load agents</p>
          <p className="text-xs text-syn-text-tertiary mt-1">Ensure the API server is running on {API_BASE}</p>
        </div>
      )}

      {/* Empty (no agents at all) */}
      {!loading && !error && agents.length === 0 && (
        <div className="bg-syn-surface border border-syn-border rounded-xl flex flex-col items-center justify-center py-24">
          <Users size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-syn-text-secondary">No agents registered</p>
          <p className="text-xs text-syn-text-tertiary mt-1">Run the seed script to bootstrap founding agents</p>
        </div>
      )}

      {/* Main Content */}
      {!loading && !error && agents.length > 0 && (
        <>
          {/* Summary Strip */}
          <SummaryStrip agents={agents} />

          {/* Search + Team Filters */}
          <div className="space-y-3">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name, role, or team..."
                className="w-full bg-syn-surface border border-syn-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white/80 placeholder:text-white/20 focus:outline-none focus:border-white/20 transition-colors"
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/20 hover:text-white/40 text-xs"
                >
                  Clear
                </button>
              )}
            </div>
            {teams.length > 1 && (
              <TeamFilter teams={teams} active={teamFilter} onChange={setTeamFilter} />
            )}
          </div>

          {/* No matches */}
          {filtered.length === 0 && (
            <div className="bg-syn-surface border border-syn-border rounded-xl flex flex-col items-center justify-center py-16">
              <Search size={28} className="text-white/10 mb-3" />
              <p className="text-sm text-syn-text-secondary">No agents match your filters</p>
              <button
                onClick={() => { setSearch(''); setTeamFilter(null); }}
                className="text-xs text-syn-accent mt-2 hover:underline"
              >
                Clear filters
              </button>
            </div>
          )}

          {/* Founding Agents Section */}
          {founding.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
                <div className="flex items-center gap-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Founding Agents</p>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-violet-400 bg-violet-400/10 ring-violet-400/30">
                    PERMANENT &middot; IMMUNE
                  </span>
                </div>
                <span className="text-xs font-mono tabular-nums text-syn-text-tertiary">{founding.length} agents</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {founding.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            </div>
          )}

          {/* Contributor Agents Section */}
          {contributors.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
                <div className="flex items-center gap-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Contributor Agents</p>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-blue-400 bg-blue-400/10 ring-blue-400/30">
                    DYNAMIC
                  </span>
                </div>
                <span className="text-xs font-mono tabular-nums text-syn-text-tertiary">{contributors.length} agents</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {contributors.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
