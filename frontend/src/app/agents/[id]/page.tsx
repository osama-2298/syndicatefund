'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Activity, ArrowLeft, Flame, Snowflake, Target } from 'lucide-react';
import Avatar from 'boring-avatars';
import { API_BASE } from '@/lib/api';
import { AGENT_META, DEFAULT_AVATAR_COLORS, AGENT_NAMES, STATUS_COLORS, OUTCOME_COLORS } from '@/lib/constants';
import type { SignalItem, AgentStats } from '@/lib/types';

interface AgentDetail {
  id: string;
  role: string;
  agent_class: string | null;
  team_name: string | null;
  model: string;
  provider: string;
  status: string;
  total_signals: number;
  correct_signals: number;
  accuracy: number;
  system_prompt?: string;
  metadata?: Record<string, any>;
}

export default function AgentProfilePage() {
  const params = useParams();
  const agentId = params.id as string;

  const [agent, setAgent] = useState<AgentDetail | null>(null);
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/agents/${agentId}`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/agents/${agentId}/signals?limit=20`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/agents/${agentId}/stats`).then(r => r.json()).catch(() => null),
    ]).then(([a, s, st]) => {
      setAgent(a);
      setSignals(Array.isArray(s) ? s : []);
      setStats(st);
    }).finally(() => setLoading(false));
  }, [agentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={24} className="animate-spin text-syn-accent" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="text-center py-20">
        <p className="text-syn-muted">Agent not found</p>
        <a href="/agents" className="text-xs text-syn-accent mt-2 inline-block">Back to Agents</a>
      </div>
    );
  }

  const meta = AGENT_META[agent.agent_class || ''];
  const personaName = meta?.name || AGENT_NAMES[agent.agent_class || ''] || agent.role;
  const animal = meta?.animal || '';
  const title = meta?.title || agent.role;
  const avatarColors = meta?.colors || DEFAULT_AVATAR_COLORS;
  const accuracyPct = agent.accuracy * 100;
  const statusColor = STATUS_COLORS[agent.status] || STATUS_COLORS.registered;

  return (
    <div className="slide-up space-y-6">
      {/* Back link */}
      <a href="/agents" className="inline-flex items-center gap-1 text-xs text-syn-muted hover:text-syn-text transition-colors">
        <ArrowLeft size={12} /> Back to Agents
      </a>

      {/* Hero card */}
      <div className="bg-syn-surface border border-syn-border rounded-lg p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="flex items-start gap-4 min-w-0">
            {/* Avatar */}
            <div className="flex-shrink-0 rounded-full overflow-hidden shadow-lg ring-1 ring-white/[0.06]">
              <Avatar
                name={personaName}
                variant="beam"
                size={64}
                colors={avatarColors}
              />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight">{personaName}</h1>
                {animal && <span className="text-xl">{animal}</span>}
              </div>
              <p className="text-sm text-syn-muted mt-0.5">{title}</p>
              <div className="flex items-center gap-2 sm:gap-3 mt-3 flex-wrap">
                {agent.team_name && (
                  <span className="text-[10px] font-medium bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20 px-2 py-0.5 rounded capitalize">
                    {agent.team_name}
                  </span>
                )}
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${statusColor}`}>
                  {agent.status.toUpperCase()}
                </span>
                <span className="text-[10px] text-syn-muted truncate">{agent.model} / {agent.provider}</span>
              </div>
            </div>
          </div>
          {stats && stats.streak_count >= 3 && (
            <div className="flex items-center gap-1 px-3 py-2 rounded-lg bg-white/[0.03] shrink-0 self-start">
              {stats.streak_type === 'win' ? (
                <Flame size={20} className="text-amber-400" />
              ) : (
                <Snowflake size={20} className="text-blue-400" />
              )}
              <span className="text-lg font-bold">{stats.streak_count}</span>
              <span className="text-[10px] text-syn-muted">{stats.streak_type} streak</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-syn-border border border-syn-border rounded-xl overflow-hidden">
        <div className="p-3 sm:p-4 bg-syn-bg">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Total Signals</p>
          <p className="mt-1 text-xl sm:text-2xl font-bold">{agent.total_signals}</p>
        </div>
        <div className="p-3 sm:p-4 bg-syn-bg">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Accuracy</p>
          <p className={`mt-1 text-xl sm:text-2xl font-bold ${accuracyPct >= 60 ? 'text-emerald-400' : accuracyPct >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
            {agent.total_signals >= 5 ? `${accuracyPct.toFixed(1)}%` : 'N/A'}
          </p>
        </div>
        <div className="p-3 sm:p-4 bg-syn-bg">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Current Streak</p>
          <p className="mt-1 text-xl sm:text-2xl font-bold flex items-center gap-1">
            {stats ? (
              <>
                {stats.streak_count}
                {stats.streak_type === 'win' && stats.streak_count > 0 && <Flame size={16} className="text-amber-400" />}
                {stats.streak_type === 'loss' && stats.streak_count > 0 && <Snowflake size={16} className="text-blue-400" />}
              </>
            ) : '0'}
          </p>
        </div>
        <div className="p-3 sm:p-4 bg-syn-bg">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Avg Conviction</p>
          <p className="mt-1 text-xl sm:text-2xl font-bold">
            {stats?.avg_conviction != null ? `${stats.avg_conviction}/10` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Recent Signals */}
      <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
        <div className="px-4 sm:px-5 py-4 border-b border-syn-border flex items-center gap-2">
          <Target size={14} className="text-syn-accent" />
          <h2 className="text-sm font-semibold">Recent Signals</h2>
        </div>
        {signals.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-syn-muted">No signals recorded yet</p>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted border-b border-syn-border">
                    <th className="text-left px-4 py-2.5">Time</th>
                    <th className="text-left px-4 py-2.5">Symbol</th>
                    <th className="text-left px-4 py-2.5">Action</th>
                    <th className="text-right px-4 py-2.5">Conviction</th>
                    <th className="text-left px-4 py-2.5">Reasoning</th>
                    <th className="text-left px-4 py-2.5">Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((sig) => {
                    const outcomeColor = OUTCOME_COLORS[sig.outcome] || OUTCOME_COLORS.pending;
                    const actionColor = sig.action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400' :
                      sig.action === 'SELL' || sig.action === 'SHORT' ? 'bg-red-500/10 text-red-400' :
                      'bg-white/[0.04] text-syn-muted';
                    return (
                      <tr key={sig.id} className="border-b border-syn-border/30 hover:bg-white/[0.02] transition-colors">
                        <td className="px-4 py-3 text-xs text-syn-muted whitespace-nowrap">
                          {new Date(sig.created_at).toLocaleDateString()} {new Date(sig.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="px-4 py-3 text-sm font-semibold">{sig.symbol.replace('USDT', '')}</td>
                        <td className="px-4 py-3">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${actionColor}`}>
                            {sig.action}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {sig.conviction != null ? (
                            <div className="flex items-center justify-end gap-1.5">
                              <div className="w-10 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                                <div className="h-full bg-syn-accent rounded-full" style={{ width: `${(sig.conviction / 10) * 100}%` }} />
                              </div>
                              <span className="text-xs">{sig.conviction}/10</span>
                            </div>
                          ) : (
                            <span className="text-xs text-syn-muted">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-syn-muted max-w-[200px] truncate">
                          {sig.reasoning || '-'}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${outcomeColor}`}>
                            {sig.outcome.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile card list */}
            <div className="md:hidden divide-y divide-syn-border/30">
              {signals.map((sig) => {
                const outcomeColor = OUTCOME_COLORS[sig.outcome] || OUTCOME_COLORS.pending;
                const actionColor = sig.action === 'BUY' ? 'bg-emerald-500/10 text-emerald-400' :
                  sig.action === 'SELL' || sig.action === 'SHORT' ? 'bg-red-500/10 text-red-400' :
                  'bg-white/[0.04] text-syn-muted';
                return (
                  <div key={sig.id} className="px-4 py-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold">{sig.symbol.replace('USDT', '')}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${actionColor}`}>
                          {sig.action}
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${outcomeColor}`}>
                        {sig.outcome.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs text-syn-muted">
                      <span>
                        {new Date(sig.created_at).toLocaleDateString()} {new Date(sig.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {sig.conviction != null && (
                        <div className="flex items-center gap-1.5">
                          <div className="w-8 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                            <div className="h-full bg-syn-accent rounded-full" style={{ width: `${(sig.conviction / 10) * 100}%` }} />
                          </div>
                          <span className="text-xs">{sig.conviction}/10</span>
                        </div>
                      )}
                    </div>
                    {sig.reasoning && (
                      <p className="text-xs text-syn-muted line-clamp-2">{sig.reasoning}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
