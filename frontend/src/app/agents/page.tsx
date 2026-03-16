'use client';

import { useEffect, useState } from 'react';
import { Bot, Loader2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

const statusColors: Record<string, string> = {
  founding: 'text-amber-400 bg-amber-400/10 ring-amber-400/30',
  active: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/30',
  assigned: 'text-blue-400 bg-blue-400/10 ring-blue-400/30',
  registered: 'text-gray-400 bg-gray-400/10 ring-gray-400/30',
  probation: 'text-orange-400 bg-orange-400/10 ring-orange-400/30',
  fired: 'text-red-400 bg-red-400/10 ring-red-400/30',
};

function StatusBadge({ status }: { status: string }) {
  const color = statusColors[status] || 'text-gray-400 bg-gray-400/10 ring-gray-400/30';
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${color}`}>
      {status.toUpperCase()}
    </span>
  );
}

function AccuracyBar({ accuracy, signals }: { accuracy: number; signals: number }) {
  if (signals < 5) return <span className="text-white/20 text-sm">{'\u2014'}</span>;
  const pct = Math.round(accuracy * 100);
  const color = pct >= 60 ? 'bg-emerald-400' : pct >= 40 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2 justify-end">
      <div className="w-14 h-1 bg-white/[0.06] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-white/60">{pct}%</span>
    </div>
  );
}

function AgentTable({
  agents,
  label,
  labelBadge,
  showQuarantine = false,
}: {
  agents: AgentSummary[];
  label: string;
  labelBadge?: string;
  showQuarantine?: boolean;
}) {
  if (agents.length === 0) return null;
  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">{label}</p>
        {labelBadge && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-amber-400 bg-amber-400/10 ring-amber-400/30">
            {labelBadge}
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Agent</th>
              <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Team</th>
              <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Model</th>
              <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Status</th>
              <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Signals</th>
              <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Accuracy</th>
              {showQuarantine && (
                <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Quarantine</th>
              )}
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr key={agent.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-3">
                  <span className="text-sm font-medium text-white/90">{agent.agent_class || agent.role}</span>
                </td>
                <td className="px-5 py-3 text-sm text-white/40">{agent.team_name ?? '\u2014'}</td>
                <td className="px-5 py-3 text-xs text-white/30 font-mono">{agent.model}</td>
                <td className="px-5 py-3"><StatusBadge status={agent.status} /></td>
                <td className="px-5 py-3 text-right text-sm tabular-nums text-white/60">{agent.total_signals}</td>
                <td className="px-5 py-3 text-right">
                  <AccuracyBar accuracy={agent.accuracy} signals={agent.total_signals} />
                </td>
                {showQuarantine && (
                  <td className="px-5 py-3 text-right text-sm text-white/30">
                    {agent.quarantine_signals_remaining > 0
                      ? `${agent.quarantine_signals_remaining} left`
                      : '\u2014'}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

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
    <div className="slide-up space-y-8">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-white/[0.04]">
          <Bot size={20} className="text-amber-400/60" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
          <p className="text-sm text-white/40 mt-1">
            {loading
              ? 'Loading agents...'
              : `${agents.length} total \u2014 ${founding.length} founding, ${contributors.length} contributor`}
          </p>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="glass-card flex items-center justify-center py-20">
          <Loader2 size={24} className="text-white/20 animate-spin" />
        </div>
      )}

      {/* Error / Empty State */}
      {!loading && error && (
        <div className="glass-card flex flex-col items-center justify-center py-20">
          <Bot size={40} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">Could not load agents</p>
          <p className="text-xs text-white/20 mt-1">Make sure the API server is running</p>
        </div>
      )}

      {!loading && !error && agents.length === 0 && (
        <div className="glass-card flex flex-col items-center justify-center py-20">
          <Bot size={40} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">No agents registered</p>
          <p className="text-xs text-white/20 mt-1">Run the seed script to create system agents</p>
        </div>
      )}

      {/* Founding Agents Table */}
      {!loading && !error && (
        <>
          <AgentTable
            agents={founding}
            label="Founding Agents"
            labelBadge="PERMANENT"
          />
          <AgentTable
            agents={contributors}
            label="Contributor Agents"
            showQuarantine
          />
        </>
      )}
    </div>
  );
}
