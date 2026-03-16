'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Activity, ArrowLeft, Flame, Snowflake, Target } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const AGENT_NAMES: Record<string, string> = {
  TechnicalTrendAgent: 'Aria Chen',
  TechnicalSignalAgent: 'Leo Tanaka',
  TechnicalTimingAgent: 'Priya Sharma',
  SocialSentimentAgent: 'Dante Morales',
  MarketSentimentAgent: 'Zara Obi',
  SmartMoneySentimentAgent: 'Felix Strand',
  ValuationAgent: 'Mina Petrova',
  CyclePositionAgent: 'Ravi Anand',
  CryptoMacroAgent: 'Ingrid Holm',
  ExternalMacroAgent: 'Tariq Nasseri',
  NetworkHealthAgent: 'Yuki Sato',
  CapitalFlowAgent: 'Emeka Osei',
};

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

interface SignalItem {
  id: string;
  symbol: string;
  action: string;
  confidence: number;
  conviction: number | null;
  reasoning: string | null;
  outcome: string;
  created_at: string;
}

interface AgentStats {
  streak_count: number;
  streak_type: string;
  avg_conviction: number | null;
  contrarian_rate: number | null;
}

const STATUS_COLORS: Record<string, string> = {
  founding: 'bg-amber-500/10 text-amber-400 ring-amber-500/20',
  active: 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20',
  assigned: 'bg-blue-500/10 text-blue-400 ring-blue-500/20',
  registered: 'bg-white/[0.06] text-hive-muted ring-white/[0.08]',
  probation: 'bg-orange-500/10 text-orange-400 ring-orange-500/20',
  fired: 'bg-red-500/10 text-red-400 ring-red-500/20',
};

const OUTCOME_COLORS: Record<string, string> = {
  correct: 'bg-emerald-500/10 text-emerald-400',
  incorrect: 'bg-red-500/10 text-red-400',
  pending: 'bg-white/[0.04] text-hive-muted',
};

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
        <Activity size={24} className="animate-spin text-hive-accent" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="text-center py-20">
        <p className="text-hive-muted">Agent not found</p>
        <a href="/agents" className="text-xs text-hive-accent mt-2 inline-block">Back to Agents</a>
      </div>
    );
  }

  const personaName = AGENT_NAMES[agent.agent_class || ''] || agent.role;
  const accuracyPct = agent.accuracy * 100;
  const statusColor = STATUS_COLORS[agent.status] || STATUS_COLORS.registered;

  return (
    <div className="slide-up space-y-6">
      {/* Back link */}
      <a href="/agents" className="inline-flex items-center gap-1 text-xs text-hive-muted hover:text-hive-text transition-colors">
        <ArrowLeft size={12} /> Back to Agents
      </a>

      {/* Hero card */}
      <div className="glass-card p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{personaName}</h1>
            <p className="text-sm text-hive-muted mt-1">{agent.role}</p>
            <div className="flex items-center gap-3 mt-3">
              {agent.team_name && (
                <span className="text-[10px] font-medium bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20 px-2 py-0.5 rounded capitalize">
                  {agent.team_name}
                </span>
              )}
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${statusColor}`}>
                {agent.status.toUpperCase()}
              </span>
              <span className="text-[10px] text-hive-muted">{agent.model} / {agent.provider}</span>
            </div>
          </div>
          {stats && stats.streak_count >= 3 && (
            <div className="flex items-center gap-1 px-3 py-2 rounded-lg bg-white/[0.03]">
              {stats.streak_type === 'win' ? (
                <Flame size={20} className="text-amber-400" />
              ) : (
                <Snowflake size={20} className="text-blue-400" />
              )}
              <span className="text-lg font-bold">{stats.streak_count}</span>
              <span className="text-[10px] text-hive-muted">{stats.streak_type} streak</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Total Signals</p>
          <p className="mt-1 text-2xl font-bold">{agent.total_signals}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Accuracy</p>
          <p className={`mt-1 text-2xl font-bold ${accuracyPct >= 60 ? 'text-emerald-400' : accuracyPct >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
            {agent.total_signals >= 5 ? `${accuracyPct.toFixed(1)}%` : 'N/A'}
          </p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Current Streak</p>
          <p className="mt-1 text-2xl font-bold flex items-center gap-1">
            {stats ? (
              <>
                {stats.streak_count}
                {stats.streak_type === 'win' && stats.streak_count > 0 && <Flame size={16} className="text-amber-400" />}
                {stats.streak_type === 'loss' && stats.streak_count > 0 && <Snowflake size={16} className="text-blue-400" />}
              </>
            ) : '0'}
          </p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Avg Conviction</p>
          <p className="mt-1 text-2xl font-bold">
            {stats?.avg_conviction != null ? `${stats.avg_conviction}/10` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Recent Signals */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-2">
          <Target size={14} className="text-hive-accent" />
          <h2 className="text-sm font-semibold">Recent Signals</h2>
        </div>
        {signals.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-hive-muted">No signals recorded yet</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
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
                  'bg-white/[0.04] text-hive-muted';
                return (
                  <tr key={sig.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-xs text-hive-muted">
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
                            <div className="h-full bg-hive-accent rounded-full" style={{ width: `${(sig.conviction / 10) * 100}%` }} />
                          </div>
                          <span className="text-xs">{sig.conviction}/10</span>
                        </div>
                      ) : (
                        <span className="text-xs text-hive-muted">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-hive-muted max-w-[200px] truncate">
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
        )}
      </div>
    </div>
  );
}
