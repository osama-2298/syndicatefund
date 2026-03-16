'use client';

import { useEffect, useState } from 'react';
import { Loader2, Crown, Shield, Radio, Zap, BarChart3, Users } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* ------------------------------------------------------------------ */
/*  DESIGN CONSTANTS                                                   */
/* ------------------------------------------------------------------ */

const AGENT_COLORS: Record<string, string> = {
  TechnicalTrendAgent: 'from-blue-500 to-cyan-500',
  TechnicalSignalAgent: 'from-blue-400 to-indigo-500',
  TechnicalTimingAgent: 'from-sky-500 to-blue-500',
  SocialSentimentAgent: 'from-purple-500 to-pink-500',
  MarketSentimentAgent: 'from-violet-500 to-purple-600',
  SmartMoneySentimentAgent: 'from-fuchsia-500 to-purple-500',
  ValuationAgent: 'from-yellow-500 to-amber-500',
  CyclePositionAgent: 'from-amber-500 to-orange-500',
  CryptoMacroAgent: 'from-cyan-500 to-teal-500',
  ExternalMacroAgent: 'from-teal-500 to-emerald-500',
  NetworkHealthAgent: 'from-emerald-500 to-green-500',
  CapitalFlowAgent: 'from-green-500 to-lime-500',
};

const TEAM_COLORS: Record<string, string> = {
  technical: 'from-blue-500 to-cyan-500',
  sentiment: 'from-purple-500 to-pink-500',
  fundamental: 'from-yellow-500 to-amber-500',
  macro: 'from-cyan-500 to-teal-500',
  onchain: 'from-emerald-500 to-green-500',
  'on-chain': 'from-emerald-500 to-green-500',
};

const statusColors: Record<string, string> = {
  founding: 'text-amber-400 bg-amber-400/10 ring-amber-400/30',
  active: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/30',
  assigned: 'text-blue-400 bg-blue-400/10 ring-blue-400/30',
  registered: 'text-gray-400 bg-gray-400/10 ring-gray-400/30',
  probation: 'text-orange-400 bg-orange-400/10 ring-orange-400/30',
  fired: 'text-red-400 bg-red-400/10 ring-red-400/30',
};

/* ------------------------------------------------------------------ */
/*  TYPES                                                              */
/* ------------------------------------------------------------------ */

interface AgentSummary {
  id: string;
  contributor_id: string | null;
  team_id: string | null;
  team_name: string | null;
  role: string;
  agent_class: string | null;
  model: string;
  provider: string;
  status: string;
  total_signals: number;
  correct_signals: number;
  accuracy: number;
  total_cost_usd: number;
  quarantine_signals_remaining: number;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  HELPERS                                                            */
/* ------------------------------------------------------------------ */

function getAgentGradient(agent: AgentSummary): string {
  if (agent.agent_class && AGENT_COLORS[agent.agent_class]) {
    return AGENT_COLORS[agent.agent_class];
  }
  // Fallback: derive from team
  if (agent.team_name) {
    const key = agent.team_name.toLowerCase().replace(/[\s_]+/g, '-');
    if (TEAM_COLORS[key]) return TEAM_COLORS[key];
  }
  return 'from-amber-500 to-orange-500';
}

function getTeamGradient(teamName: string): string {
  const key = teamName.toLowerCase().replace(/[\s_]+/g, '-');
  return TEAM_COLORS[key] || 'from-amber-500 to-orange-500';
}

function getInitial(agent: AgentSummary): string {
  const name = agent.agent_class || agent.role;
  // Extract capital letters for abbreviation
  const caps = name.replace(/Agent$/, '').match(/[A-Z]/g);
  if (caps && caps.length >= 2) return caps.slice(0, 2).join('');
  return name.slice(0, 2).toUpperCase();
}

/* ------------------------------------------------------------------ */
/*  SUB-COMPONENTS                                                     */
/* ------------------------------------------------------------------ */

function SummaryStrip({ agents, founding, contributors }: {
  agents: AgentSummary[];
  founding: AgentSummary[];
  contributors: AgentSummary[];
}) {
  const totalSignals = agents.reduce((s, a) => s + a.total_signals, 0);
  const withSignals = agents.filter(a => a.total_signals >= 5);
  const avgAccuracy = withSignals.length > 0
    ? withSignals.reduce((s, a) => s + a.accuracy, 0) / withSignals.length
    : 0;

  const stats = [
    { label: 'Total Agents', value: agents.length.toString(), icon: Users },
    { label: 'Founding', value: founding.length.toString(), icon: Crown },
    { label: 'Contributors', value: contributors.length.toString(), icon: Shield },
    { label: 'Avg Accuracy', value: withSignals.length > 0 ? `${Math.round(avgAccuracy * 100)}%` : '\u2014', icon: BarChart3 },
    { label: 'Total Signals', value: totalSignals.toLocaleString(), icon: Radio },
  ];

  return (
    <div className="grid grid-cols-5 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-[#0d0d15] border border-white/[0.06] rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1.5">
            <stat.icon size={12} className="text-white/20" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">{stat.label}</p>
          </div>
          <p className="text-xl font-bold font-mono tabular-nums text-white/90">{stat.value}</p>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = statusColors[status] || 'text-gray-400 bg-gray-400/10 ring-gray-400/30';
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
  if (signals < 5) return <span className="text-white/15 text-xs font-mono">\u2014</span>;
  const pct = Math.round(accuracy * 100);
  const color = pct >= 60 ? 'bg-emerald-400' : pct >= 40 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1 bg-white/[0.06] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono tabular-nums text-white/60">{pct}%</span>
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentSummary }) {
  const gradient = getAgentGradient(agent);
  const initial = getInitial(agent);
  const isFounding = agent.status === 'founding';
  const isQuarantined = agent.quarantine_signals_remaining > 0;
  const displayName = agent.agent_class || agent.role;

  return (
    <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl p-4 hover:bg-white/[0.03] transition-colors group">
      <div className="flex items-start gap-3.5">
        {/* Gradient Avatar */}
        <div className="relative flex-shrink-0">
          <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg`}>
            <span className="text-sm font-bold text-white/90 drop-shadow">{initial}</span>
          </div>
          {isFounding && (
            <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#0d0d15] flex items-center justify-center border border-amber-500/40">
              <Crown size={10} className="text-amber-400" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-bold text-white/90 truncate">{displayName}</h3>
            {agent.team_name && <TeamBadge teamName={agent.team_name} />}
          </div>
          <p className="text-[11px] text-white/25 font-mono mt-1 truncate">
            {agent.provider}/{agent.model}
          </p>
        </div>
      </div>

      {/* Bottom stats row */}
      <div className="mt-3.5 pt-3 border-t border-white/[0.04] flex items-center gap-3 flex-wrap">
        <StatusBadge status={agent.status} />

        <div className="flex items-center gap-1.5">
          <Radio size={10} className="text-white/20" />
          <span className="text-xs font-mono tabular-nums text-white/50">{agent.total_signals}</span>
        </div>

        <AccuracyBar accuracy={agent.accuracy} signals={agent.total_signals} />

        {isQuarantined && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-orange-400 bg-orange-400/10 ring-orange-400/30">
            Q: {agent.quarantine_signals_remaining} remaining
          </span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN PAGE                                                          */
/* ------------------------------------------------------------------ */

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

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

  const founding = agents.filter((a) => a.status === 'founding');
  const contributors = agents.filter((a) => a.status !== 'founding');

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Agent Directory</h1>
        <p className="text-sm text-white/30 mt-1">
          {loading
            ? 'Loading roster...'
            : `${agents.length} agents deployed across ${new Set(agents.map(a => a.team_name).filter(Boolean)).size} teams`}
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex items-center justify-center py-24">
          <Loader2 size={24} className="text-white/20 animate-spin" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex flex-col items-center justify-center py-24">
          <Zap size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">Could not load agents</p>
          <p className="text-xs text-white/20 mt-1">Ensure the API server is running on {API_BASE}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && agents.length === 0 && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex flex-col items-center justify-center py-24">
          <Users size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">No agents registered</p>
          <p className="text-xs text-white/20 mt-1">Run the seed script to bootstrap founding agents</p>
        </div>
      )}

      {/* Main Content */}
      {!loading && !error && agents.length > 0 && (
        <>
          {/* Summary Strip */}
          <SummaryStrip agents={agents} founding={founding} contributors={contributors} />

          {/* Founding Agents Section */}
          {founding.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Founding Agents</p>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-amber-400 bg-amber-400/10 ring-amber-400/30">
                    PERMANENT &middot; IMMUNE
                  </span>
                </div>
                <span className="text-xs font-mono tabular-nums text-white/20">{founding.length} agents</span>
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
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Contributor Agents</p>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-blue-400 bg-blue-400/10 ring-blue-400/30">
                    DYNAMIC
                  </span>
                </div>
                <span className="text-xs font-mono tabular-nums text-white/20">{contributors.length} agents</span>
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
