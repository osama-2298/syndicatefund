'use client';

import { useEffect, useState } from 'react';
import { Loader2, Crown, Shield, Radio, Zap, BarChart3, Users } from 'lucide-react';
import { API_BASE } from '@/lib/api';
import {
  AGENT_COLORS,
  TEAM_COLORS,
  STATUS_COLORS,
  getAgentGradient,
  getTeamGradient,
  getAgentInitial,
} from '@/lib/constants';
import type { AgentSummary } from '@/lib/types';

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

function AgentCard({ agent }: { agent: AgentSummary }) {
  const gradient = getAgentGradient(agent.agent_class, agent.team_name);
  const initial = getAgentInitial(agent.agent_class, agent.role);
  const isFounding = agent.status === 'founding';
  const isQuarantined = agent.quarantine_signals_remaining > 0;
  const displayName = agent.agent_class || agent.role;

  return (
    <div className="bg-syn-surface border border-syn-border rounded-xl p-4 hover:bg-white/[0.03] transition-colors group">
      <div className="flex items-start gap-3.5">
        {/* Gradient Avatar */}
        <div className="relative flex-shrink-0">
          <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg`}>
            <span className="text-sm font-bold text-white/90 drop-shadow">{initial}</span>
          </div>
          {isFounding && (
            <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-syn-surface flex items-center justify-center border border-amber-500/40">
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
          <p className="text-xs text-white/25 font-mono mt-1 truncate">
            {agent.provider}/{agent.model}
          </p>
        </div>
      </div>

      {/* Bottom stats row */}
      <div className="mt-3.5 pt-3 border-t border-syn-border/40 flex items-center gap-3 flex-wrap">
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

      {/* Empty */}
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
          <SummaryStrip agents={agents} founding={founding} contributors={contributors} />

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
