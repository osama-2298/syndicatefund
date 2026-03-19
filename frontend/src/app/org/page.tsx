'use client';

import { useEffect, useState } from 'react';
import { Loader2, ChevronDown, ChevronRight, Crown } from 'lucide-react';
import Avatar from 'boring-avatars';
import { AGENT_NAMES, MANAGER_NAMES, getPersona, getPersonaByClass, DEFAULT_AVATAR_COLORS } from '@/lib/constants';
import { API_BASE } from '@/lib/api';

/* ━━━ Types ━━━ */

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

/* ━━━ Constants ━━━ */

const TEAM_PALETTE = [
  { dot: 'bg-blue-400', accent: 'text-blue-400' },
  { dot: 'bg-rose-400', accent: 'text-rose-400' },
  { dot: 'bg-emerald-400', accent: 'text-emerald-400' },
  { dot: 'bg-cyan-400', accent: 'text-cyan-400' },
  { dot: 'bg-purple-400', accent: 'text-purple-400' },
  { dot: 'bg-amber-400', accent: 'text-amber-400' },
  { dot: 'bg-pink-400', accent: 'text-pink-400' },
  { dot: 'bg-teal-400', accent: 'text-teal-400' },
  { dot: 'bg-indigo-400', accent: 'text-indigo-400' },
  { dot: 'bg-orange-400', accent: 'text-orange-400' },
];

const KNOWN_TEAM_IDX: Record<string, number> = {
  technical: 0, sentiment: 1, fundamental: 2, macro: 3, onchain: 4,
};

/** Deterministic color for any team — known teams get their fixed color, new teams get a hash-based pick */
function teamColor(name: string) {
  if (name in KNOWN_TEAM_IDX) return TEAM_PALETTE[KNOWN_TEAM_IDX[name]];
  const hash = name.split('').reduce((h, c) => h + c.charCodeAt(0), 0);
  return TEAM_PALETTE[hash % TEAM_PALETTE.length];
}

const STATUS_DOT: Record<string, string> = {
  founding: 'bg-violet-400',
  active: 'bg-emerald-400',
  assigned: 'bg-blue-400',
  registered: 'bg-gray-400',
  probation: 'bg-orange-400',
  fired: 'bg-red-400',
};

function agentDisplay(a: Agent) {
  const persona = getPersonaByClass(a.agent_class, a.role);
  return {
    name: persona.name,
    role: persona.title || a.agent_class?.replace(/([A-Z])/g, ' $1').trim() || a.model,
    animal: persona.animal,
    colors: persona.colors,
  };
}

/* ━━━ Tree primitives ━━━ */

function TreeGroup({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`relative border-l border-white/[0.06] pl-5 space-y-2 ${className}`}>
      {children}
    </div>
  );
}

function TreeNode({ children, dot, className = '' }: { children: React.ReactNode; dot?: string; className?: string }) {
  return (
    <div className={`relative ${className}`}>
      <div className="absolute -left-5 top-5 w-5 h-px bg-white/[0.06]" />
      <div className={`absolute -left-[23px] top-[17px] w-[7px] h-[7px] rounded-full ${dot || 'bg-white/20'}`} />
      {children}
    </div>
  );
}

/* ━━━ Section header ━━━ */

function SectionHead({
  label,
  color,
  badge,
  badgeColor,
  meta,
}: {
  label: string;
  color: string;
  badge?: string;
  badgeColor?: string;
  meta?: string;
}) {
  return (
    <div className="flex items-center gap-3 flex-wrap pt-3 pb-1">
      <span className={`text-xs font-bold uppercase tracking-wider ${color}`}>{label}</span>
      {badge && (
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${badgeColor}`}>
          {badge}
        </span>
      )}
      {meta && (
        <span className="text-[10px] text-syn-text-tertiary font-mono tabular-nums">{meta}</span>
      )}
      <div className="h-px flex-1 bg-white/[0.04]" />
    </div>
  );
}

/* ━━━ Card components ━━━ */

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
  const expandable = !!children;
  const persona = getPersona(name);

  return (
    <div>
      <div
        onClick={() => expandable && setOpen(!open)}
        className={`bg-white/[0.02] border border-white/[0.06] rounded-xl p-4 ${
          expandable ? 'cursor-pointer hover:border-white/[0.12]' : ''
        } transition-colors`}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-text-tertiary">
            {title}
          </span>
          {badge && (
            <span
              className={`text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${
                badgeColor || 'bg-white/[0.04] text-syn-text-tertiary ring-white/[0.06]'
              }`}
            >
              {badge}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 rounded-full overflow-hidden ring-1 ring-white/[0.06]">
            <Avatar name={name} variant="beam" size={32} colors={persona.colors} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <p className="text-sm font-semibold text-white">{name}</p>
              {persona.animal && <span className="text-sm">{persona.animal}</span>}
            </div>
            <p className="text-xs text-syn-text-tertiary mt-0.5 line-clamp-2">{subtitle}</p>
          </div>
        </div>
        {expandable && (
          <div className="flex items-center gap-1 mt-2 text-[10px] text-syn-text-tertiary">
            {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            <span>{open ? 'Collapse' : 'Expand'}</span>
          </div>
        )}
      </div>
      {open && children && (
        <div className="mt-1.5 space-y-1 pl-3 border-l border-white/[0.04] ml-4">
          {children}
        </div>
      )}
    </div>
  );
}

function SubRole({ name, subtitle }: { name: string; subtitle: string }) {
  // Extract persona name from "Name — Title" format if present
  const displayName = name.includes('—') ? name.split('—')[0].trim() : name;
  const persona = getPersona(displayName);
  const hasPersona = !!persona.animal;

  return (
    <div className="bg-white/[0.01] border border-white/[0.04] rounded-lg px-3 py-2">
      <div className="flex items-center gap-2">
        {hasPersona && (
          <div className="flex-shrink-0 rounded-full overflow-hidden ring-1 ring-white/[0.04]">
            <Avatar name={displayName} variant="beam" size={20} colors={persona.colors} />
          </div>
        )}
        <div className="min-w-0">
          <div className="flex items-center gap-1">
            <p className="text-xs font-medium text-syn-text-secondary">{name}</p>
            {persona.animal && <span className="text-xs">{persona.animal}</span>}
          </div>
          <p className="text-[10px] text-syn-text-tertiary">{subtitle}</p>
        </div>
      </div>
    </div>
  );
}

function TeamCard({ team, agents }: { team: Team; agents: Agent[] }) {
  const [open, setOpen] = useState(false);
  const managerName = MANAGER_NAMES[team.name] || 'Manager';
  const managerPersona = getPersona(managerName);
  const accent = teamColor(team.name).accent;

  return (
    <div>
      <div
        onClick={() => setOpen(!open)}
        className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4 cursor-pointer hover:border-white/[0.12] transition-colors"
      >
        <div className="flex flex-wrap items-center justify-between gap-y-1 mb-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white capitalize">{team.name} Team</span>
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
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white/[0.04] text-syn-text-tertiary ring-1 ring-inset ring-white/[0.06]">
              {agents.length} agents
            </span>
          </div>
        </div>
        <p className="text-xs text-syn-text-tertiary">
          Managed by <span className={accent}>{managerName}</span>
          {managerPersona.animal && <span className="ml-1">{managerPersona.animal}</span>}
          {' — '}{team.discipline}
        </p>
        <div className="flex items-center gap-1 mt-2 text-[10px] text-syn-text-tertiary">
          {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          <span>{open ? 'Hide agents' : 'Show agents'}</span>
        </div>
      </div>

      {/* Expanded: agents as sub-tree */}
      {open && (
        <TreeGroup className="mt-1">
          {/* Manager node */}
          <TreeNode dot="bg-white/30">
            <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3.5 py-2.5 flex items-center gap-3">
              <div className="flex-shrink-0 rounded-full overflow-hidden ring-1 ring-white/[0.06]">
                <Avatar name={managerName} variant="beam" size={24} colors={managerPersona.colors} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <p className="text-xs font-medium text-syn-text-secondary">{managerName}</p>
                  {managerPersona.animal && <span className="text-xs">{managerPersona.animal}</span>}
                </div>
                <p className="text-[10px] text-syn-text-tertiary capitalize">{team.name} Team Manager</p>
              </div>
            </div>
          </TreeNode>

          {/* Agent nodes */}
          {agents.map((agent) => {
            const { name, role, animal, colors } = agentDisplay(agent);
            const sd = STATUS_DOT[agent.status] || STATUS_DOT.registered;
            return (
              <TreeNode key={agent.id} dot={sd}>
                <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3.5 py-2.5 flex items-center gap-3">
                  <div className="flex-shrink-0 rounded-full overflow-hidden ring-1 ring-white/[0.04]">
                    <Avatar name={name} variant="beam" size={24} colors={colors} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1">
                      <p className="text-xs font-medium text-syn-text-secondary truncate">{name}</p>
                      {animal && <span className="text-xs flex-shrink-0">{animal}</span>}
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
              </TreeNode>
            );
          })}

          {agents.length === 0 && (
            <TreeNode dot="bg-gray-400/30">
              <div className="bg-white/[0.01] border border-white/[0.03] rounded-lg px-3.5 py-2.5 text-center">
                <p className="text-xs text-syn-text-tertiary">No agents assigned yet</p>
              </div>
            </TreeNode>
          )}
        </TreeGroup>
      )}
    </div>
  );
}

/* ━━━ Main page ━━━ */

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

  const totalAnalysts = Object.values(agentsByTeam).reduce((s, a) => s + a.length, 0);

  return (
    <div className="max-w-5xl mx-auto slide-up">
      {/* ── Header ── */}
      <div className="mb-10">
        <h1 className="text-2xl font-bold tracking-tight text-white">Org Chart</h1>
        <p className="text-sm text-syn-text-secondary mt-1">
          Full corporate hierarchy.{' '}
          <span className="font-mono tabular-nums">{teams.length}</span> teams,{' '}
          <span className="font-mono tabular-nums">{agents.length}</span> agents. Zero humans. Click
          nodes to expand.
        </p>
      </div>

      {/* ── Pipeline flow legend ── */}
      <div className="bg-syn-surface border border-syn-border rounded-xl px-4 sm:px-6 py-3.5 mb-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-text-tertiary mb-2">
          Pipeline flow per cycle
        </p>
        <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap text-[10px] sm:text-xs">
          {[
            { label: 'CEO', color: 'text-syn-accent/80' },
            { label: 'COO', color: 'text-blue-400/80' },
            { label: 'Analysis', color: 'text-emerald-400/80' },
            { label: 'Aggregator', color: 'text-cyan-400/80' },
            { label: 'Risk', color: 'text-red-400/80' },
            { label: 'Portfolio', color: 'text-purple-400/80' },
            { label: 'Execution', color: 'text-orange-400/80' },
          ].map((step, i, arr) => (
            <span key={step.label} className="flex items-center gap-1.5 sm:gap-2">
              <span className={`${step.color} font-medium whitespace-nowrap`}>{step.label}</span>
              {i < arr.length - 1 && <span className="text-syn-text-tertiary">→</span>}
            </span>
          ))}
        </div>
      </div>

      {/* ═══ Org tree ═══ */}
      <div className="bg-syn-surface border border-syn-border rounded-xl p-4 sm:p-6 md:p-8">
        {/* ── CEO (root) ── */}
        <div className="relative mb-0">
          <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-violet-400/15 to-purple-500/15 blur-lg" />
          <div className="relative bg-syn-surface border-2 border-syn-accent/30 rounded-2xl px-6 py-5">
            <div className="flex items-center gap-2 mb-3">
              <Crown size={14} className="text-syn-accent" />
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">
                Chief Executive Officer
              </span>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-shrink-0 rounded-full overflow-hidden ring-2 ring-syn-accent/30 shadow-lg">
                <Avatar name="Marcus Blackwell" variant="beam" size={48} colors={getPersona('Marcus Blackwell').colors} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-lg font-bold text-white">Marcus Blackwell</p>
                  <span className="text-lg">{getPersona('Marcus Blackwell').animal}</span>
                </div>
                <p className="text-xs text-syn-text-tertiary mt-0.5">
                  Strategic leadership & market direction — oversees all divisions
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Tree trunk from CEO ── */}
        <TreeGroup className="mt-0 pt-3">
          {/* ━━ Branch: Executive Team ━━ */}
          <TreeNode dot="bg-amber-400">
            <SectionHead
              label="Executive Team"
              color="text-amber-400"
              meta="3 direct reports"
            />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
              <ExecCard
                title="Chief Operating Officer"
                name="Elena Vasquez"
                subtitle="Selects which coins to analyze each cycle — her picks flow down to Analysis"
                badge="STEP 1"
                badgeColor="bg-blue-400/10 text-blue-400 ring-blue-400/20"
              />
              <ExecCard
                title="Chief Risk Officer"
                name="Tobias Richter"
                subtitle="Sets risk rules per cycle — enforced by Risk Manager in Operations"
              >
                <SubRole
                  name="James Hartley — Risk Manager"
                  subtitle="Enforces CRO rules: position sizing, drawdown halt, confidence gates"
                />
              </ExecCard>
              <ExecCard
                title="Board of Directors"
                name="Governance"
                subtitle="Organizational structure and agent lifecycle"
                badge="META"
                badgeColor="bg-purple-400/10 text-purple-400 ring-purple-400/20"
              >
                <SubRole name="Victor Okafor — CSO" subtitle="Team creation and dissolution" />
                <SubRole name="Nadia Chen — CTO" subtitle="Agent assignment and prompt writing" />
                <SubRole
                  name="Raphael Moreno — CPO"
                  subtitle="Probation and firing pipeline"
                />
              </ExecCard>
            </div>
          </TreeNode>

          {/* ━━ Branch: Analysis Division ━━ */}
          <TreeNode dot="bg-emerald-400">
            <SectionHead
              label="Analysis Division"
              color="text-emerald-400"
              badge="STEP 2"
              badgeColor="bg-emerald-400/10 text-emerald-400 ring-emerald-400/20"
              meta={`${teams.length} teams · ${totalAnalysts} agents`}
            />
            <TreeGroup className="mt-2">
              {teams.map((team) => (
                <TreeNode key={team.id} dot={teamColor(team.name).dot}>
                  <TeamCard team={team} agents={agentsByTeam[team.name] || []} />
                </TreeNode>
              ))}
            </TreeGroup>
          </TreeNode>

          {/* ━━ Branch: Operations Pipeline ━━ */}
          <TreeNode dot="bg-cyan-400">
            <SectionHead
              label="Operations Pipeline"
              color="text-cyan-400"
              badge="STEPS 3–6"
              badgeColor="bg-cyan-400/10 text-cyan-400 ring-cyan-400/20"
            />
            <TreeGroup className="mt-2">
              <TreeNode dot="bg-cyan-400">
                <ExecCard
                  title="Signal Aggregator"
                  name="Soren Lindqvist"
                  subtitle="Combines all team signals into one recommendation per coin — deterministic, no LLM"
                  badge="STEP 3"
                  badgeColor="bg-cyan-400/10 text-cyan-400 ring-cyan-400/20"
                >
                  <SubRole
                    name="Bayesian log-odds"
                    subtitle="Weighted signal combination by team accuracy"
                  />
                  <SubRole
                    name="Macro & Technical gates"
                    subtitle="Bearish macro suppresses buys fund-wide"
                  />
                  <SubRole
                    name="Polarization detection"
                    subtitle="Flags team disagreement"
                  />
                  <SubRole name="Close-call detection" subtitle="Flags marginal signals" />
                </ExecCard>
              </TreeNode>

              <TreeNode dot="bg-red-400">
                <ExecCard
                  title="Risk Manager"
                  name="James Hartley"
                  subtitle="Enforces CRO Tobias Richter's rules on aggregated signals — gates, sizes, and halts"
                  badge="STEP 4"
                  badgeColor="bg-red-400/10 text-red-400 ring-red-400/20"
                >
                  <SubRole
                    name="Confidence & consensus gates"
                    subtitle="Kills signals below CRO thresholds"
                  />
                  <SubRole
                    name="Position sizing"
                    subtitle="Quarter-Kelly allocation per trade"
                  />
                  <SubRole
                    name="Drawdown halt"
                    subtitle="Blocks all trading if daily loss exceeded"
                  />
                  <SubRole
                    name="Open positions cap"
                    subtitle="Max concurrent positions enforced"
                  />
                </ExecCard>
              </TreeNode>

              <TreeNode dot="bg-purple-400">
                <ExecCard
                  title="Head of Portfolio"
                  name="Diana Frost"
                  subtitle="Reviews risk-approved orders against segment allocation limits — CEO sector weights applied"
                  badge="STEP 5"
                  badgeColor="bg-purple-400/10 text-purple-400 ring-purple-400/20"
                >
                  <SubRole
                    name="Segment allocation"
                    subtitle="L1s / DeFi / L2s / Memes / AI / Infrastructure"
                  />
                </ExecCard>
              </TreeNode>

              <TreeNode dot="bg-orange-400">
                <ExecCard
                  title="Head of Execution"
                  name="Kai Nakamura"
                  subtitle="Executes final portfolio-approved orders and monitors live positions"
                  badge="STEP 6"
                  badgeColor="bg-orange-400/10 text-orange-400 ring-orange-400/20"
                >
                  <SubRole
                    name="Paper Trader"
                    subtitle="Executes buy/sell against virtual portfolio"
                  />
                  <SubRole
                    name="Trade Monitor"
                    subtitle="SL / TP / trailing stops between cycles"
                  />
                  <SubRole
                    name="Trade Ledger"
                    subtitle="P&L, holding time, exit reason tracking"
                  />
                </ExecCard>
              </TreeNode>
            </TreeGroup>
          </TreeNode>

          {/* ━━ Branch: Research Division ━━ */}
          <TreeNode dot="bg-indigo-400">
            <SectionHead label="Research Division" color="text-indigo-400" />
            <TreeGroup className="mt-2">
              <TreeNode dot="bg-indigo-400">
                <ExecCard
                  title="Head of Research"
                  name="Dr. Elara Voss"
                  subtitle="Orchestrates research, produces weekly digests"
                  badge="LEAD"
                  badgeColor="bg-indigo-400/10 text-indigo-400 ring-indigo-400/20"
                />
              </TreeNode>
              <TreeNode dot="bg-indigo-300/60">
                <ExecCard
                  title="Quantitative Researcher"
                  name="Dr. Kai Moretti"
                  subtitle="Signal health, decay detection, data source evaluation"
                />
              </TreeNode>
              <TreeNode dot="bg-indigo-300/60">
                <ExecCard
                  title="Strategy Researcher"
                  name="Dr. Noor Hadid"
                  subtitle="Trade attribution, regime analysis, hypothesis testing"
                />
              </TreeNode>
            </TreeGroup>
            <div className="mt-2 ml-5">
              <a
                href="/research"
                className="text-xs text-syn-accent hover:text-violet-300 transition-colors inline-flex items-center gap-1"
              >
                View research reports →
              </a>
            </div>
          </TreeNode>
        </TreeGroup>
      </div>

      {/* ── Unassigned agents ── */}
      {unassigned.length > 0 && (
        <div className="mt-4 bg-syn-surface border border-syn-border rounded-xl p-4 sm:p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px flex-1 bg-white/[0.04]" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-text-tertiary">
              Unassigned — Awaiting Board Review
            </span>
            <div className="h-px flex-1 bg-white/[0.04]" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            {unassigned.map((agent) => {
              const { name, animal, colors } = agentDisplay(agent);
              const sd = STATUS_DOT[agent.status] || STATUS_DOT.registered;
              return (
                <div
                  key={agent.id}
                  className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3.5 py-3 flex items-center gap-3"
                >
                  <div className="flex-shrink-0 rounded-full overflow-hidden ring-1 ring-white/[0.04]">
                    <Avatar name={name} variant="beam" size={28} colors={colors} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium text-syn-text-secondary truncate">
                        {name}
                      </p>
                      {animal && <span className="text-xs flex-shrink-0">{animal}</span>}
                      <span className={`w-1.5 h-1.5 rounded-full ${sd} flex-shrink-0`} />
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
  );
}
