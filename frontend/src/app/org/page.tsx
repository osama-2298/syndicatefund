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
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status] || 'bg-gray-400'} flex-shrink-0`} />;
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-3.5 h-3.5 text-hive-muted transition-transform duration-150 ${open ? 'rotate-90' : ''}`}
      fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function Node({
  label,
  subtitle,
  badge,
  badgeColor,
  children,
  defaultOpen = false,
  leaf = false,
  right,
}: {
  label: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
  children?: React.ReactNode;
  defaultOpen?: boolean;
  leaf?: boolean;
  right?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const hasChildren = !!children && !leaf;

  return (
    <div className="relative">
      <button
        onClick={() => hasChildren && setOpen(!open)}
        className={`w-full flex items-center gap-2 py-1.5 px-2 rounded transition-colors text-left
          ${hasChildren ? 'hover:bg-hive-border/20 cursor-pointer' : 'cursor-default'}`}
      >
        <span className="w-4 flex-shrink-0 flex items-center justify-center">
          {hasChildren ? <Chevron open={open} /> : <span className="w-1.5 h-1.5 rounded-full bg-hive-border" />}
        </span>

        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className="text-sm font-medium">{label}</span>
          {badge && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${badgeColor || 'bg-hive-border text-hive-muted'}`}>
              {badge}
            </span>
          )}
          {subtitle && <span className="text-xs text-hive-muted truncate hidden md:inline">{subtitle}</span>}
        </div>

        {right && <div className="flex-shrink-0">{right}</div>}
      </button>

      {open && hasChildren && (
        <div className="ml-4 pl-4 border-l border-hive-border/30">
          {children}
        </div>
      )}
    </div>
  );
}

function Leaf({
  label,
  sublabel,
  status,
  right,
}: {
  label: string;
  sublabel?: string;
  status?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2 py-1.5 px-2">
      <span className="w-4 flex-shrink-0 flex items-center justify-center">
        {status ? <StatusDot status={status} /> : <span className="w-1.5 h-1.5 rounded-full bg-hive-border" />}
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-sm">{label}</span>
        {sublabel && <span className="text-xs text-hive-muted ml-2">{sublabel}</span>}
      </div>
      {right && <div className="flex-shrink-0 text-xs text-hive-muted">{right}</div>}
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
    return <div className="flex items-center justify-center py-20"><p className="text-hive-muted">Loading...</p></div>;
  }

  return (
    <div className="max-w-3xl mx-auto py-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Organization</h1>
        <p className="text-hive-muted text-sm">
          {teams.length} teams, {agents.length} agents. Click to expand.
        </p>
      </div>

      <div className="bg-hive-card border border-hive-border rounded-xl p-3">
        <Node label="CEO" subtitle="Strategic leadership" badge="EXECUTIVE" badgeColor="bg-hive-accent/20 text-hive-accent" defaultOpen={true}>

          <Node label="COO" subtitle="Coin selection">
            <Leaf label="Selects which coins to analyze each cycle based on volume, momentum, and CEO strategy" />
          </Node>

          <Node label="CRO" subtitle="Risk management">
            <Leaf label="Sets position limits, drawdown thresholds, and confidence minimums per cycle" />
            <Node label="Risk Manager" subtitle="Enforces CRO rules on all trades">
              <Leaf label="Position sizing (quarter-Kelly)" />
              <Leaf label="Drawdown halt" />
              <Leaf label="Confidence gates" />
            </Node>
          </Node>

          <Node label="Board of Directors" subtitle="Organizational governance" badge="META" badgeColor="bg-purple-500/20 text-purple-400">
            <Leaf label="CSO — Chief Strategy Officer" sublabel="Team creation and dissolution" />
            <Leaf label="CTO — Chief Talent Officer" sublabel="Agent assignment and prompt writing" />
            <Leaf label="CPO — Chief Performance Officer" sublabel="Probation and firing pipeline" />
          </Node>

          <Node label="Analysis Division" subtitle={`${teams.length} teams, ${agents.filter(a => a.team_name).length} assigned agents`} defaultOpen={true}>
            {teams.map((team) => {
              const ta = agentsByTeam[team.name] || [];
              return (
                <Node
                  key={team.id}
                  label={`${team.name.charAt(0).toUpperCase() + team.name.slice(1)} Team`}
                  badge={team.is_system ? 'SYSTEM' : 'DYNAMIC'}
                  badgeColor={team.is_system ? 'bg-amber-500/20 text-amber-400' : 'bg-hive-blue/20 text-hive-blue'}
                  right={<span className="text-xs text-hive-muted">{team.weight.toFixed(1)}x</span>}
                >
                  <Leaf label={`${team.name.charAt(0).toUpperCase() + team.name.slice(1)} Manager`} sublabel="Synthesizes agent signals" />
                  {ta.map((agent) => (
                    <Leaf
                      key={agent.id}
                      label={agent.agent_class || agent.role}
                      sublabel={`${agent.model} / ${agent.provider}`}
                      status={agent.status}
                      right={
                        agent.total_signals > 0
                          ? <>{Math.round(agent.accuracy * 100)}% ({agent.total_signals})</>
                          : undefined
                      }
                    />
                  ))}
                  {ta.length === 0 && <Leaf label="No agents assigned" />}
                </Node>
              );
            })}
          </Node>

          <Node label="Portfolio Managers" subtitle="Segment allocation">
            <Leaf label="L1s segment" />
            <Leaf label="DeFi segment" />
            <Leaf label="L2s segment" />
            <Leaf label="Memes segment" />
            <Leaf label="AI segment" />
            <Leaf label="Infrastructure segment" />
          </Node>

          <Node label="Execution" subtitle="Trade lifecycle">
            <Leaf label="Paper Trader" sublabel="Executes orders" />
            <Leaf label="Trade Monitor" sublabel="SL / TP / trailing stops" />
            <Leaf label="Trade Ledger" sublabel="P&L tracking and calibration" />
          </Node>

          <Node label="Signal Aggregator" subtitle="Deterministic, no LLM">
            <Leaf label="Bayesian log-odds combination" />
            <Leaf label="Macro gate / Technical gate" />
            <Leaf label="Polarization detection" />
            <Leaf label="Close-call detection" />
          </Node>

          {unassigned.length > 0 && (
            <Node label={`Unassigned (${unassigned.length})`} subtitle="Awaiting Board assignment" badge="PENDING" badgeColor="bg-gray-500/20 text-gray-400" defaultOpen={true}>
              {unassigned.map((agent) => (
                <Leaf
                  key={agent.id}
                  label={agent.role}
                  sublabel={`${agent.model} / ${agent.provider}`}
                  status={agent.status}
                />
              ))}
            </Node>
          )}

        </Node>
      </div>
    </div>
  );
}
