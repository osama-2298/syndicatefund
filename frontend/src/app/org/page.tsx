'use client';

import { useEffect, useState } from 'react';

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

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    founding: 'bg-amber-400',
    active: 'bg-hive-green',
    assigned: 'bg-hive-blue',
    registered: 'bg-gray-400',
    probation: 'bg-orange-400',
    fired: 'bg-hive-red',
  };
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${colors[status] || 'bg-gray-400'} flex-shrink-0`} />;
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-4 h-4 text-hive-muted transition-transform duration-200 ${open ? 'rotate-90' : ''}`}
      fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function TreeNode({
  label,
  subtitle,
  badge,
  badgeColor,
  icon,
  children,
  defaultOpen = false,
  depth = 0,
}: {
  label: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
  icon?: string;
  children?: React.ReactNode;
  defaultOpen?: boolean;
  depth?: number;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const hasChildren = !!children;

  return (
    <div className={depth > 0 ? 'ml-6 border-l border-hive-border/40 pl-4' : ''}>
      <button
        onClick={() => hasChildren && setOpen(!open)}
        className={`w-full flex items-center gap-3 py-2.5 px-3 rounded-lg transition-colors text-left group
          ${hasChildren ? 'hover:bg-hive-border/20 cursor-pointer' : 'cursor-default'}
          ${depth === 0 ? 'bg-hive-card border border-hive-border' : ''}`}
      >
        {hasChildren && <Chevron open={open} />}
        {!hasChildren && <span className="w-4" />}

        {icon && <span className="text-lg">{icon}</span>}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`font-medium ${depth === 0 ? 'text-base' : 'text-sm'}`}>{label}</span>
            {badge && (
              <span className={`text-xs px-1.5 py-0.5 rounded ${badgeColor || 'bg-hive-border text-hive-muted'}`}>
                {badge}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-hive-muted mt-0.5 truncate">{subtitle}</p>}
        </div>
      </button>

      {open && hasChildren && (
        <div className="mt-1 space-y-0.5">
          {children}
        </div>
      )}
    </div>
  );
}

function AgentNode({ agent }: { agent: Agent }) {
  const accuracy = agent.total_signals > 0 ? `${Math.round(agent.accuracy * 100)}%` : '—';
  return (
    <div className="ml-6 border-l border-hive-border/40 pl-4">
      <div className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-hive-border/10">
        <span className="w-4" />
        <StatusDot status={agent.status} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">{agent.agent_class || agent.role}</p>
          <p className="text-xs text-hive-muted">{agent.model} · {agent.provider}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            agent.status === 'founding' ? 'bg-amber-500/20 text-amber-400' :
            agent.status === 'active' ? 'bg-hive-green/20 text-hive-green' :
            agent.status === 'registered' ? 'bg-gray-500/20 text-gray-400' :
            'bg-hive-border text-hive-muted'
          }`}>
            {agent.status}
          </span>
          {agent.total_signals > 0 && (
            <p className="text-xs text-hive-muted mt-0.5">{accuracy} · {agent.total_signals} sigs</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OrgPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/teams`).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/agents`).then(r => r.json()),
    ]).then(([t, a]) => {
      setTeams(t);
      setAgents(a);
    }).catch(() => {}).finally(() => setLoading(false));
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
      <div className="flex items-center justify-center py-20">
        <p className="text-hive-muted">Loading organization...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-2 py-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Organization</h1>
        <p className="text-hive-muted">
          Click any node to expand. {teams.length} teams · {agents.length} agents
        </p>
      </div>

      {/* CEO — Top of the tree */}
      <TreeNode
        label="CEO"
        subtitle="Market regime classification, strategic directives, team weight allocation, post-cycle review"
        badge="EXECUTIVE"
        badgeColor="bg-hive-accent/20 text-hive-accent"
        icon="👑"
        defaultOpen={false}
        depth={0}
      >
        {/* COO */}
        <TreeNode label="COO" subtitle="Coin selection — picks which assets to analyze each cycle" icon="🎯" depth={1} />

        {/* CRO */}
        <TreeNode label="CRO" subtitle="Risk rules — sets position limits, drawdown thresholds, confidence minimums" icon="🛡" depth={1} />

        {/* Board of Directors */}
        <TreeNode
          label="Board of Directors"
          subtitle="Manages organizational structure, agent assignment, and performance"
          badge="META-AGENTS"
          badgeColor="bg-purple-500/20 text-purple-400"
          icon="🏛"
          depth={1}
        >
          <TreeNode label="CSO — Chief Strategy Officer" subtitle="Team creation & dissolution, coverage gap analysis" depth={2} />
          <TreeNode label="CTO — Chief Talent Officer" subtitle="Agent assignment, system prompt writing, guardrails" depth={2} />
          <TreeNode label="CPO — Chief Performance Officer" subtitle="Probation & firing pipeline, accuracy monitoring" depth={2} />
        </TreeNode>

        {/* Analysis Teams */}
        {teams.map((team) => {
          const teamAgents = agentsByTeam[team.name] || [];
          return (
            <TreeNode
              key={team.id}
              label={`${team.name.charAt(0).toUpperCase() + team.name.slice(1)} Team`}
              subtitle={team.discipline.slice(0, 80)}
              badge={team.is_system ? 'SYSTEM' : 'DYNAMIC'}
              badgeColor={team.is_system ? 'bg-amber-500/20 text-amber-400' : 'bg-hive-blue/20 text-hive-blue'}
              icon={
                team.name === 'technical' ? '📊' :
                team.name === 'sentiment' ? '💬' :
                team.name === 'fundamental' ? '📈' :
                team.name === 'macro' ? '🌐' :
                team.name === 'onchain' ? '⛓' : '📋'
              }
              depth={1}
            >
              {/* Team Manager */}
              <div className="ml-6 border-l border-hive-border/40 pl-4">
                <div className="flex items-center gap-3 py-2 px-3 rounded-lg bg-hive-border/10">
                  <span className="w-4" />
                  <span className="text-sm">🧠</span>
                  <div>
                    <p className="text-sm font-medium capitalize">{team.name} Manager</p>
                    <p className="text-xs text-hive-muted">Synthesizes agent signals → team signal · {team.weight.toFixed(1)}x weight</p>
                  </div>
                </div>
              </div>

              {/* Agents */}
              {teamAgents.map((agent) => (
                <AgentNode key={agent.id} agent={agent} />
              ))}

              {teamAgents.length === 0 && (
                <div className="ml-6 border-l border-hive-border/40 pl-4">
                  <p className="py-2 px-3 text-sm text-hive-muted">No agents assigned</p>
                </div>
              )}
            </TreeNode>
          );
        })}

        {/* Portfolio Managers */}
        <TreeNode
          label="Portfolio Managers"
          subtitle="Segment-based allocation (L1s, DeFi, L2s, Memes, AI, Infra)"
          icon="💼"
          depth={1}
        />

        {/* Risk Manager */}
        <TreeNode
          label="Risk Manager"
          subtitle="Enforces CRO rules — position sizing, drawdown limits, confidence gates"
          icon="⚠️"
          depth={1}
        />

        {/* Execution */}
        <TreeNode
          label="Execution Engine"
          subtitle="Paper trader, trade monitor (SL/TP/trailing stops), trade ledger"
          icon="⚡"
          depth={1}
        />
      </TreeNode>

      {/* Unassigned Agents */}
      {unassigned.length > 0 && (
        <TreeNode
          label={`Unassigned Agents (${unassigned.length})`}
          subtitle="Waiting for Board of Directors to assign to teams"
          badge="PENDING"
          badgeColor="bg-gray-500/20 text-gray-400"
          icon="⏳"
          defaultOpen={true}
          depth={0}
        >
          {unassigned.map((agent) => (
            <AgentNode key={agent.id} agent={agent} />
          ))}
        </TreeNode>
      )}
    </div>
  );
}
