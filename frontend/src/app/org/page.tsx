'use client';

import { useEffect, useState } from 'react';
import { Loader2, ChevronDown, ChevronRight, Users, Cpu, Crown } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Agent {
  id: string;
  team_name: string | null;
  role: string;
  agent_class: string | null;
  model: string;
  provider: string;
  status: string;
  total_signals: number;
  correct_signals: number;
  accuracy: number;
}

interface Team {
  id: string;
  name: string;
  discipline: string;
  weight: number;
  is_system: boolean;
  agent_count: number;
  active_agent_count: number;
}

const agentNames: Record<string, string> = {
  TechnicalTrendAgent: 'Lena Karlsson',
  TechnicalSignalAgent: 'David Osei',
  TechnicalTimingAgent: 'Mika Tanaka',
  SocialSentimentAgent: 'Priya Sharma',
  MarketSentimentAgent: 'Alexei Volkov',
  SmartMoneySentimentAgent: 'Sofia Reyes',
  ValuationAgent: 'Henrik Larsen',
  CyclePositionAgent: 'Amara Obi',
  CryptoMacroAgent: 'Lucas Weber',
  ExternalMacroAgent: 'Fatima Al-Rashid',
  NetworkHealthAgent: 'Jin Park',
  CapitalFlowAgent: 'Camille Dubois',
};

const managerNames: Record<string, string> = {
  technical: 'Oscar Brennan',
  sentiment: 'Yara Haddad',
  fundamental: 'Isaac Thornton',
  macro: 'Zara Kimathi',
  onchain: 'Nikolai Petrov',
};

const teamGradients: Record<string, { border: string; dot: string; bg: string }> = {
  technical: {
    border: 'border-l-amber-400',
    dot: 'bg-gradient-to-br from-amber-400 to-orange-500',
    bg: 'bg-amber-400/5',
  },
  sentiment: {
    border: 'border-l-rose-400',
    dot: 'bg-gradient-to-br from-rose-400 to-pink-500',
    bg: 'bg-rose-400/5',
  },
  fundamental: {
    border: 'border-l-emerald-400',
    dot: 'bg-gradient-to-br from-emerald-400 to-teal-500',
    bg: 'bg-emerald-400/5',
  },
  macro: {
    border: 'border-l-blue-400',
    dot: 'bg-gradient-to-br from-blue-400 to-indigo-500',
    bg: 'bg-blue-400/5',
  },
  onchain: {
    border: 'border-l-purple-400',
    dot: 'bg-gradient-to-br from-purple-400 to-violet-500',
    bg: 'bg-purple-400/5',
  },
};

const statusColors: Record<string, { dot: string; label: string }> = {
  founding: { dot: 'bg-amber-400', label: 'text-amber-400' },
  active: { dot: 'bg-emerald-400', label: 'text-emerald-400' },
  assigned: { dot: 'bg-blue-400', label: 'text-blue-400' },
  registered: { dot: 'bg-gray-400', label: 'text-gray-400' },
  probation: { dot: 'bg-orange-400', label: 'text-orange-400' },
  fired: { dot: 'bg-red-400', label: 'text-red-400' },
};

function getAgentDisplayName(agent: Agent): { name: string; role: string } {
  if (agent.agent_class && agentNames[agent.agent_class]) {
    return {
      name: agentNames[agent.agent_class],
      role: agent.agent_class.replace(/([A-Z])/g, ' $1').trim(),
    };
  }
  return { name: agent.role, role: agent.model };
}

function getTeamGradient(name: string) {
  return (
    teamGradients[name] || {
      border: 'border-l-gray-400',
      dot: 'bg-gradient-to-br from-gray-400 to-gray-500',
      bg: 'bg-gray-400/5',
    }
  );
}

/* ────────────────────────────────────────────────── */
/*  Card components                                   */
/* ────────────────────────────────────────────────── */

function CeoNode() {
  return (
    <div className="flex justify-center mb-8">
      <div className="relative">
        {/* Glow */}
        <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-amber-400/20 to-orange-500/20 blur-lg" />
        <div className="relative bg-[#0d0d15] border-2 border-amber-400/30 rounded-2xl px-8 py-5 text-center min-w-[260px]">
          <div className="flex items-center justify-center gap-2 mb-1">
            <Crown size={14} className="text-amber-400" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">
              Chief Executive Officer
            </span>
          </div>
          <p className="text-lg font-bold text-white">Marcus Blackwell</p>
          <p className="text-xs text-white/30 mt-0.5">Strategic leadership & market direction</p>
        </div>
      </div>
    </div>
  );
}

function ConnectorVertical({ className = '' }: { className?: string }) {
  return (
    <div className={`flex justify-center ${className}`}>
      <div className="w-px h-6 bg-white/[0.08]" />
    </div>
  );
}

function ConnectorHorizontal() {
  return <div className="flex-1 h-px bg-white/[0.08] self-center" />;
}

function ExecCard({
  title,
  name,
  subtitle,
  badge,
  badgeColor,
  children,
}: {
  title: string;
  name: string;
  subtitle: string;
  badge?: string;
  badgeColor?: string;
  children?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const hasChildren = !!children;

  return (
    <div className="flex-1 min-w-0">
      <div
        onClick={() => hasChildren && setOpen(!open)}
        className={`bg-[#0d0d15] border border-white/[0.06] rounded-xl p-4 ${
          hasChildren ? 'cursor-pointer hover:border-white/[0.10]' : ''
        } transition-all`}
      >
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-white/25">
            {title}
          </span>
          {badge && (
            <span
              className={`text-[9px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
                badgeColor || 'bg-white/[0.04] text-white/30 ring-white/[0.08]'
              }`}
            >
              {badge}
            </span>
          )}
        </div>
        <p className="text-sm font-bold text-white">{name}</p>
        <p className="text-[11px] text-white/30 mt-0.5">{subtitle}</p>
        {hasChildren && (
          <div className="flex items-center gap-1 mt-2 text-[10px] text-white/20">
            {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            <span>{open ? 'Collapse' : 'Expand'}</span>
          </div>
        )}
      </div>
      {open && hasChildren && (
        <div className="mt-2 space-y-1.5 pl-3 border-l border-white/[0.06] ml-4">{children}</div>
      )}
    </div>
  );
}

function SubRoleCard({ name, subtitle }: { name: string; subtitle: string }) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3 py-2">
      <p className="text-xs font-medium text-white/60">{name}</p>
      <p className="text-[10px] text-white/25">{subtitle}</p>
    </div>
  );
}

function TeamCard({
  team,
  agents,
}: {
  team: Team;
  agents: Agent[];
}) {
  const [open, setOpen] = useState(false);
  const gradient = getTeamGradient(team.name);
  const managerName = managerNames[team.name] || 'Manager';

  return (
    <div>
      <div
        onClick={() => setOpen(!open)}
        className={`bg-[#0d0d15] border border-white/[0.06] rounded-xl p-4 cursor-pointer hover:border-white/[0.10] transition-all border-l-2 ${gradient.border}`}
      >
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white capitalize">{team.name} Team</span>
            <span
              className={`text-[9px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
                team.is_system
                  ? 'bg-amber-400/10 text-amber-400 ring-amber-400/20'
                  : 'bg-blue-400/10 text-blue-400 ring-blue-400/20'
              }`}
            >
              {team.is_system ? 'SYSTEM' : 'DYNAMIC'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono tabular-nums text-white/25">
              {team.weight.toFixed(1)}x
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white/[0.04] text-white/30 ring-1 ring-inset ring-white/[0.06]">
              {agents.length} agents
            </span>
          </div>
        </div>
        <p className="text-[11px] text-white/25">
          Managed by {managerName} — {team.discipline}
        </p>
        <div className="flex items-center gap-1 mt-2 text-[10px] text-white/20">
          {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          <span>{open ? 'Hide agents' : 'Show agents'}</span>
        </div>
      </div>

      {/* Agent nodes */}
      {open && (
        <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 pl-4 border-l-2 ml-4 border-white/[0.04]">
          {/* Manager card */}
          <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3.5 py-3 flex items-center gap-3">
            <div
              className={`w-7 h-7 rounded-full ${gradient.dot} flex items-center justify-center flex-shrink-0`}
            >
              <Users size={12} className="text-white/80" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-white/70 truncate">{managerName}</p>
              <p className="text-[10px] text-white/25 capitalize">{team.name} Manager</p>
            </div>
          </div>

          {agents.map((agent) => {
            const { name, role } = getAgentDisplayName(agent);
            const status = statusColors[agent.status] || statusColors.registered;

            return (
              <div
                key={agent.id}
                className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3.5 py-3 flex items-center gap-3"
              >
                <div
                  className={`w-7 h-7 rounded-full ${gradient.dot} flex items-center justify-center flex-shrink-0 opacity-60`}
                >
                  <Cpu size={11} className="text-white/80" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-medium text-white/60 truncate">{name}</p>
                    <span className={`w-1.5 h-1.5 rounded-full ${status.dot} flex-shrink-0`} />
                  </div>
                  <p className="text-[10px] text-white/20 truncate">{role}</p>
                </div>
                <div className="flex-shrink-0 text-right">
                  {agent.total_signals > 0 ? (
                    <div>
                      <p className="text-[11px] font-mono tabular-nums text-white/40">
                        {Math.round(agent.accuracy * 100)}%
                      </p>
                      <p className="text-[9px] text-white/15 font-mono tabular-nums">
                        {agent.total_signals} sig
                      </p>
                    </div>
                  ) : (
                    <p className="text-[10px] text-white/15">New</p>
                  )}
                </div>
              </div>
            );
          })}

          {agents.length === 0 && (
            <div className="col-span-2 bg-white/[0.01] border border-white/[0.03] rounded-lg px-3.5 py-3 text-center">
              <p className="text-xs text-white/20">No agents assigned yet</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────── */
/*  Main page                                         */
/* ────────────────────────────────────────────────── */

export default function OrgPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/teams`).then((r) => r.json()),
      fetch(`${API_BASE}/api/v1/agents`).then((r) => r.json()),
    ])
      .then(([t, a]) => {
        setTeams(t);
        setAgents(a);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const agentsByTeam: Record<string, Agent[]> = {};
  const unassigned: Agent[] = [];
  for (const agent of agents) {
    if (agent.team_name) {
      if (!agentsByTeam[agent.team_name]) agentsByTeam[agent.team_name] = [];
      agentsByTeam[agent.team_name].push(agent);
    } else {
      unassigned.push(agent);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3">
          <Loader2 size={18} className="text-amber-400/60 animate-spin" />
          <p className="text-sm text-white/30">Loading organization...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto slide-up">
      {/* ── Header ── */}
      <div className="mb-10">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-3">
          Organization
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-white">Org Chart</h1>
        <p className="text-sm text-white/40 mt-1">
          <span className="font-mono tabular-nums">{teams.length}</span> teams,{' '}
          <span className="font-mono tabular-nums">{agents.length}</span> agents. Click nodes to
          expand.
        </p>
      </div>

      {/* ── Org chart ── */}
      <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl p-6 md:p-8">
        {/* Tier 1: CEO */}
        <CeoNode />

        {/* Vertical connector from CEO */}
        <ConnectorVertical />

        {/* Horizontal rail */}
        <div className="flex items-stretch gap-0 mb-0">
          <div className="flex-1 flex flex-col items-center">
            <div className="h-px w-1/2 bg-white/[0.08] self-end" />
          </div>
          <div className="flex-1">
            <div className="h-px bg-white/[0.08]" />
          </div>
          <div className="flex-1 flex flex-col items-center">
            <div className="h-px w-1/2 bg-white/[0.08] self-start" />
          </div>
        </div>

        {/* Tier 2: COO, CRO, Board */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
          <div>
            <ConnectorVertical className="hidden md:flex" />
            <ExecCard
              title="Chief Operating Officer"
              name="Elena Vasquez"
              subtitle="Coin selection — picks which assets to analyze each cycle based on volume, momentum, and CEO strategy"
            />
          </div>

          <div>
            <ConnectorVertical className="hidden md:flex" />
            <ExecCard
              title="Chief Risk Officer"
              name="Tobias Richter"
              subtitle="Risk management — position limits, drawdown thresholds, and confidence minimums"
            >
              <SubRoleCard
                name="James Hartley — Risk Manager"
                subtitle="Position sizing (quarter-Kelly), drawdown halt, confidence gates"
              />
            </ExecCard>
          </div>

          <div>
            <ConnectorVertical className="hidden md:flex" />
            <ExecCard
              title="Board of Directors"
              name="Governance"
              subtitle="Organizational structure and agent lifecycle"
              badge="META"
              badgeColor="bg-purple-400/10 text-purple-400 ring-purple-400/20"
            >
              <SubRoleCard
                name="Victor Okafor — CSO"
                subtitle="Team creation and dissolution"
              />
              <SubRoleCard
                name="Nadia Chen — CTO"
                subtitle="Agent assignment and prompt writing"
              />
              <SubRoleCard
                name="Raphael Moreno — CPO"
                subtitle="Probation and firing pipeline"
              />
            </ExecCard>
          </div>
        </div>

        {/* ── Section: Analysis teams ── */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px flex-1 bg-white/[0.04]" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">
              Analysis Division
            </span>
            <div className="h-px flex-1 bg-white/[0.04]" />
          </div>

          <div className="space-y-3">
            {teams.map((team) => (
              <TeamCard key={team.id} team={team} agents={agentsByTeam[team.name] || []} />
            ))}
          </div>
        </div>

        {/* ── Section: Operations ── */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px flex-1 bg-white/[0.04]" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">
              Operations
            </span>
            <div className="h-px flex-1 bg-white/[0.04]" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <ExecCard
              title="Head of Portfolio"
              name="Diana Frost"
              subtitle="Segment allocation across L1s, DeFi, L2s, Memes, AI, Infrastructure"
            />
            <ExecCard
              title="Head of Execution"
              name="Kai Nakamura"
              subtitle="Trade lifecycle — paper trading, monitoring, SL/TP/trailing stops"
            >
              <SubRoleCard name="Paper Trader" subtitle="Executes orders" />
              <SubRoleCard name="Trade Monitor" subtitle="SL / TP / trailing stops" />
              <SubRoleCard name="Trade Ledger" subtitle="P&L tracking and calibration" />
            </ExecCard>
            <ExecCard
              title="Signal Aggregator"
              name="Soren Lindqvist"
              subtitle="Deterministic (no LLM) — Bayesian log-odds combination with gates and detection"
            >
              <SubRoleCard name="Bayesian log-odds" subtitle="Signal combination" />
              <SubRoleCard name="Macro & Technical gates" subtitle="Override thresholds" />
              <SubRoleCard name="Polarization detection" subtitle="Team disagreement flagging" />
              <SubRoleCard name="Close-call detection" subtitle="Marginal signal alerting" />
            </ExecCard>
          </div>
        </div>

        {/* ── Section: Unassigned agents ── */}
        {unassigned.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="h-px flex-1 bg-white/[0.04]" />
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/25">
                Unassigned — Awaiting Board Review
              </span>
              <div className="h-px flex-1 bg-white/[0.04]" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {unassigned.map((agent) => {
                const status = statusColors[agent.status] || statusColors.registered;
                return (
                  <div
                    key={agent.id}
                    className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3.5 py-3 flex items-center gap-3"
                  >
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-gray-400/30 to-gray-500/30 flex items-center justify-center flex-shrink-0">
                      <Cpu size={11} className="text-white/40" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-medium text-white/50 truncate">{agent.role}</p>
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${status.dot} flex-shrink-0`}
                        />
                      </div>
                      <p className="text-[10px] text-white/20 truncate">
                        {agent.model} / {agent.provider}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
