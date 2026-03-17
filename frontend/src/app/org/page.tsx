'use client';

import { useEffect, useState } from 'react';
import { Loader2, ChevronDown, ChevronRight, Users, Cpu, Crown } from 'lucide-react';
import { AGENT_NAMES, MANAGER_NAMES } from '@/lib/constants';
import { API_BASE } from '@/lib/api';

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

const teamGradients: Record<string, { border: string; dot: string; bg: string }> = {
  technical: {
    border: 'border-l-blue-400',
    dot: 'bg-gradient-to-br from-blue-400 to-cyan-500',
    bg: 'bg-blue-400/5',
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
    border: 'border-l-cyan-400',
    dot: 'bg-gradient-to-br from-cyan-400 to-indigo-500',
    bg: 'bg-cyan-400/5',
  },
  onchain: {
    border: 'border-l-purple-400',
    dot: 'bg-gradient-to-br from-purple-400 to-violet-500',
    bg: 'bg-purple-400/5',
  },
};

const statusColors: Record<string, { dot: string; label: string }> = {
  founding: { dot: 'bg-violet-400', label: 'text-violet-400' },
  active: { dot: 'bg-emerald-400', label: 'text-emerald-400' },
  assigned: { dot: 'bg-blue-400', label: 'text-blue-400' },
  registered: { dot: 'bg-gray-400', label: 'text-gray-400' },
  probation: { dot: 'bg-orange-400', label: 'text-orange-400' },
  fired: { dot: 'bg-red-400', label: 'text-red-400' },
};

function getAgentDisplayName(agent: Agent): { name: string; role: string } {
  if (agent.agent_class && AGENT_NAMES[agent.agent_class]) {
    return {
      name: AGENT_NAMES[agent.agent_class],
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
        <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-violet-400/20 to-purple-500/20 blur-lg" />
        <div className="relative bg-syn-surface border-2 border-syn-accent/30 rounded-2xl px-8 py-5 text-center min-w-[260px]">
          <div className="flex items-center justify-center gap-2 mb-1">
            <Crown size={14} className="text-syn-accent" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">
              Chief Executive Officer
            </span>
          </div>
          <p className="text-lg font-bold text-white">Marcus Blackwell</p>
          <p className="text-xs text-syn-text-tertiary mt-0.5">Strategic leadership & market direction</p>
        </div>
      </div>
    </div>
  );
}

function ConnectorVertical({ className = '' }: { className?: string }) {
  return (
    <div className={`flex justify-center ${className}`}>
      <div className="w-px h-6 bg-syn-border" />
    </div>
  );
}

function ConnectorHorizontal() {
  return <div className="flex-1 h-px bg-syn-border self-center" />;
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
        className={`bg-syn-surface border border-syn-border rounded-xl p-4 ${
          hasChildren ? 'cursor-pointer hover:border-white/[0.10]' : ''
        } transition-all`}
      >
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-text-tertiary">
            {title}
          </span>
          {badge && (
            <span
              className={`text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
                badgeColor || 'bg-white/[0.04] text-syn-text-tertiary ring-syn-border'
              }`}
            >
              {badge}
            </span>
          )}
        </div>
        <p className="text-sm font-bold text-white">{name}</p>
        <p className="text-xs text-syn-text-tertiary mt-0.5">{subtitle}</p>
        {hasChildren && (
          <div className="flex items-center gap-1 mt-2 text-[10px] text-syn-text-tertiary">
            {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            <span>{open ? 'Collapse' : 'Expand'}</span>
          </div>
        )}
      </div>
      {open && hasChildren && (
        <div className="mt-2 space-y-1.5 pl-3 border-l border-syn-border ml-4">{children}</div>
      )}
    </div>
  );
}

function SubRoleCard({ name, subtitle }: { name: string; subtitle: string }) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3 py-2">
      <p className="text-xs font-medium text-syn-text-secondary">{name}</p>
      <p className="text-[10px] text-syn-text-tertiary">{subtitle}</p>
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
  const managerName = MANAGER_NAMES[team.name] || 'Manager';

  return (
    <div>
      <div
        onClick={() => setOpen(!open)}
        className={`bg-syn-surface border border-syn-border rounded-xl p-4 cursor-pointer hover:border-white/[0.10] transition-all border-l-2 ${gradient.border}`}
      >
        <div className="flex flex-wrap items-center justify-between gap-y-1 mb-1.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white capitalize">{team.name} Team</span>
            <span
              className={`text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
                team.is_system
                  ? 'bg-syn-accent/10 text-syn-accent ring-syn-accent/20'
                  : 'bg-blue-400/10 text-blue-400 ring-blue-400/20'
              }`}
            >
              {team.is_system ? 'SYSTEM' : 'DYNAMIC'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono tabular-nums text-syn-text-tertiary">
              {team.weight.toFixed(1)}x
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white/[0.04] text-syn-text-tertiary ring-1 ring-inset ring-syn-border">
              {agents.length} agents
            </span>
          </div>
        </div>
        <p className="text-xs text-syn-text-tertiary">
          Managed by {managerName} — {team.discipline}
        </p>
        <div className="flex items-center gap-1 mt-2 text-[10px] text-syn-text-tertiary">
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
              <p className="text-xs font-semibold text-syn-text-secondary truncate">{managerName}</p>
              <p className="text-[10px] text-syn-text-tertiary capitalize">{team.name} Manager</p>
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
                    <p className="text-xs font-medium text-syn-text-secondary truncate">{name}</p>
                    <span className={`w-1.5 h-1.5 rounded-full ${status.dot} flex-shrink-0`} />
                  </div>
                  <p className="text-[10px] text-syn-text-tertiary truncate">{role}</p>
                </div>
                <div className="flex-shrink-0 text-right">
                  {agent.total_signals > 0 ? (
                    <div>
                      <p className="text-xs font-mono tabular-nums text-white/40">
                        {Math.round(agent.accuracy * 100)}%
                      </p>
                      <p className="text-[10px] text-syn-text-tertiary font-mono tabular-nums">
                        {agent.total_signals} sig
                      </p>
                    </div>
                  ) : (
                    <p className="text-[10px] text-syn-text-tertiary">New</p>
                  )}
                </div>
              </div>
            );
          })}

          {agents.length === 0 && (
            <div className="col-span-full bg-white/[0.01] border border-white/[0.03] rounded-lg px-3.5 py-3 text-center">
              <p className="text-xs text-syn-text-tertiary">No agents assigned yet</p>
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
          <Loader2 size={18} className="text-syn-accent animate-spin" />
          <p className="text-sm text-syn-text-tertiary">Loading organization...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto slide-up">
      {/* ── Header ── */}
      <div className="mb-10">
        <h1 className="text-2xl font-bold tracking-tight text-white">Org Chart</h1>
        <p className="text-sm text-syn-text-secondary mt-1">
          A full corporate hierarchy. <span className="font-mono tabular-nums">{teams.length}</span> teams, <span className="font-mono tabular-nums">{agents.length}</span> analysts, 3 researchers, 6 executives. Zero humans. Click to expand.
        </p>
      </div>

      {/* ── Pipeline flow legend ── */}
      <div className="bg-syn-surface border border-syn-border rounded-xl px-4 sm:px-6 py-3.5 mb-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-text-tertiary mb-2">Pipeline flow per cycle</p>
        {/* Full legend — hidden on very small screens */}
        <div className="hidden sm:flex items-center gap-2 flex-wrap text-xs">
          <span className="text-syn-accent/80 font-medium">CEO</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-blue-400/80 font-medium">COO</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-emerald-400/80 font-medium">Analysis</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-cyan-400/80 font-medium">Aggregator</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-red-400/80 font-medium">Risk</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-purple-400/80 font-medium">Portfolio</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-orange-400/80 font-medium">Execution</span>
        </div>
        {/* Compact legend — shown only on very small screens */}
        <div className="flex sm:hidden items-center gap-1.5 text-[10px] overflow-x-auto">
          <span className="text-syn-accent/80 font-medium whitespace-nowrap">CEO</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-blue-400/80 font-medium whitespace-nowrap">COO</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-emerald-400/80 font-medium whitespace-nowrap">Analysis</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-cyan-400/80 font-medium whitespace-nowrap">Agg</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-red-400/80 font-medium whitespace-nowrap">Risk</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-purple-400/80 font-medium whitespace-nowrap">Port</span>
          <span className="text-syn-text-tertiary">→</span>
          <span className="text-orange-400/80 font-medium whitespace-nowrap">Exec</span>
        </div>
      </div>

      {/* ── Org chart ── */}
      <div className="bg-syn-surface border border-syn-border rounded-xl p-4 sm:p-6 md:p-8">
        {/* Tier 1: CEO */}
        <CeoNode />

        {/* Vertical connector from CEO */}
        <ConnectorVertical />

        {/* Horizontal rail — hidden on mobile where grid stacks vertically */}
        <div className="hidden md:flex items-stretch gap-0 mb-0">
          <div className="flex-1 flex flex-col items-center">
            <div className="h-px w-1/2 bg-syn-border self-end" />
          </div>
          <div className="flex-1">
            <div className="h-px bg-syn-border" />
          </div>
          <div className="flex-1 flex flex-col items-center">
            <div className="h-px w-1/2 bg-syn-border self-start" />
          </div>
        </div>

        {/* Tier 2: COO, CRO, Board */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
          <div>
            <ConnectorVertical className="hidden md:flex" />
            <ExecCard
              title="Chief Operating Officer"
              name="Elena Vasquez"
              subtitle="Selects which coins to analyze each cycle — her picks flow down to the Analysis Division"
              badge="STEP 1"
              badgeColor="bg-blue-400/10 text-blue-400 ring-blue-400/20"
            />
          </div>

          <div>
            <ConnectorVertical className="hidden md:flex" />
            <ExecCard
              title="Chief Risk Officer"
              name="Tobias Richter"
              subtitle="Sets risk rules per cycle — enforced by the Risk Manager in Operations below"
            >
              <SubRoleCard
                name="James Hartley — Risk Manager"
                subtitle="Enforces CRO rules in Operations: position sizing, drawdown halt, confidence gates"
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

        {/* Flow: COO → Analysis */}
        <div className="flex items-center justify-center gap-2 mb-4">
          <div className="text-[10px] text-blue-400/40 font-medium">COO selected coins</div>
          <div className="text-syn-text-tertiary">↓</div>
        </div>

        {/* ── Section: Analysis teams ── */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px flex-1 bg-white/[0.04]" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400/60">
              Analysis Division
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset bg-emerald-400/10 text-emerald-400 ring-emerald-400/20">
              STEP 2
            </span>
            <div className="h-px flex-1 bg-white/[0.04]" />
          </div>

          <div className="space-y-3">
            {teams.map((team) => (
              <TeamCard key={team.id} team={team} agents={agentsByTeam[team.name] || []} />
            ))}
          </div>
        </div>

        {/* Flow: Analysis → Operations */}
        <div className="flex items-center justify-center gap-2 mb-4">
          <div className="text-[10px] text-emerald-400/40 font-medium">Team signals per coin</div>
          <div className="text-syn-text-tertiary">↓</div>
        </div>

        {/* ── Section: Operations ── */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px flex-1 bg-white/[0.04]" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-400/60">
              Operations
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset bg-cyan-400/10 text-cyan-400 ring-cyan-400/20">
              STEPS 3–6
            </span>
            <div className="h-px flex-1 bg-white/[0.04]" />
          </div>

          <div className="space-y-3">
            {/* Step 3: Aggregator */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <ExecCard
                title="Signal Aggregator"
                name="Soren Lindqvist"
                subtitle="Combines all team signals into one recommendation per coin — deterministic, no LLM"
                badge="STEP 3"
                badgeColor="bg-cyan-400/10 text-cyan-400 ring-cyan-400/20"
              >
                <SubRoleCard name="Bayesian log-odds" subtitle="Weighted signal combination by team accuracy" />
                <SubRoleCard name="Macro & Technical gates" subtitle="Bearish macro suppresses buys fund-wide" />
                <SubRoleCard name="Polarization detection" subtitle="Flags team disagreement" />
                <SubRoleCard name="Close-call detection" subtitle="Flags marginal signals" />
              </ExecCard>

              {/* Step 4: Risk — enforces CRO rules */}
              <ExecCard
                title="Risk Manager"
                name="James Hartley"
                subtitle="Enforces CRO Tobias Richter's rules on aggregated signals — gates, sizes, and halts"
                badge="STEP 4"
                badgeColor="bg-red-400/10 text-red-400 ring-red-400/20"
              >
                <SubRoleCard name="Confidence & consensus gates" subtitle="Kills signals below CRO thresholds" />
                <SubRoleCard name="Position sizing" subtitle="Quarter-Kelly allocation per trade" />
                <SubRoleCard name="Drawdown halt" subtitle="Blocks all trading if daily loss exceeded" />
                <SubRoleCard name="Open positions cap" subtitle="Max concurrent positions enforced" />
              </ExecCard>
            </div>

            {/* Step 5-6: Portfolio & Execution */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <ExecCard
                title="Head of Portfolio"
                name="Diana Frost"
                subtitle="Reviews risk-approved orders against segment allocation limits — CEO sector weights applied"
                badge="STEP 5"
                badgeColor="bg-purple-400/10 text-purple-400 ring-purple-400/20"
              >
                <SubRoleCard name="L1s / DeFi / L2s" subtitle="Segment allocation" />
                <SubRoleCard name="Memes / AI / Infrastructure" subtitle="Segment allocation" />
              </ExecCard>
              <ExecCard
                title="Head of Execution"
                name="Kai Nakamura"
                subtitle="Executes final portfolio-approved orders and monitors live positions"
                badge="STEP 6"
                badgeColor="bg-orange-400/10 text-orange-400 ring-orange-400/20"
              >
                <SubRoleCard name="Paper Trader" subtitle="Executes buy/sell against virtual portfolio" />
                <SubRoleCard name="Trade Monitor" subtitle="SL / TP / trailing stops between cycles" />
                <SubRoleCard name="Trade Ledger" subtitle="P&L, holding time, exit reason tracking" />
              </ExecCard>
            </div>
          </div>
        </div>

        {/* ── Section: Research Division ── */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px flex-1 bg-white/[0.04]" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400/60">
              Research Division
            </span>
            <div className="h-px flex-1 bg-white/[0.04]" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <ExecCard
              title="Head of Research"
              name="Dr. Elara Voss"
              subtitle="Orchestrates research, produces weekly digests"
              badge="LEAD"
              badgeColor="bg-indigo-400/10 text-indigo-400 ring-indigo-400/20"
            />
            <ExecCard
              title="Quantitative Researcher"
              name="Dr. Kai Moretti"
              subtitle="Signal health, decay detection, data source evaluation"
            />
            <ExecCard
              title="Strategy Researcher"
              name="Dr. Noor Hadid"
              subtitle="Trade attribution, regime analysis, hypothesis testing"
            />
          </div>
          <div className="mt-3 text-center">
            <a href="/research" className="text-xs text-syn-accent hover:text-violet-300 transition-colors inline-flex items-center gap-1">
              View research reports →
            </a>
          </div>
        </div>

        {/* ── Section: Unassigned agents ── */}
        {unassigned.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="h-px flex-1 bg-white/[0.04]" />
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-text-tertiary">
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
                        <p className="text-xs font-medium text-syn-text-secondary truncate">{agent.role}</p>
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${status.dot} flex-shrink-0`}
                        />
                      </div>
                      <p className="text-[10px] text-syn-text-tertiary truncate">
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
