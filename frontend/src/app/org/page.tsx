'use client';

import { useEffect, useState } from 'react';
import { Network, ChevronRight } from 'lucide-react';

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
    active: 'bg-emerald-400',
    assigned: 'bg-blue-400',
    registered: 'bg-gray-400',
    probation: 'bg-orange-400',
    fired: 'bg-red-400',
  };
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status] || 'bg-gray-400'} flex-shrink-0`} />;
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
        className={`w-full flex items-center gap-2 py-2 px-2.5 rounded-lg transition-colors text-left group
          ${hasChildren ? 'hover:bg-white/[0.04] cursor-pointer' : 'cursor-default'}`}
      >
        <span className="w-4 flex-shrink-0 flex items-center justify-center">
          {hasChildren ? (
            <ChevronRight
              size={14}
              className={`text-white/20 group-hover:text-white/40 transition-all duration-150 ${open ? 'rotate-90' : ''}`}
            />
          ) : (
            <span className="w-1.5 h-1.5 rounded-full bg-white/[0.08]" />
          )}
        </span>

        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className="text-sm font-medium">{label}</span>
          {badge && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${badgeColor || 'bg-white/[0.04] text-white/30 ring-white/[0.08]'}`}>
              {badge}
            </span>
          )}
          {subtitle && <span className="text-xs text-white/30 truncate hidden md:inline">{subtitle}</span>}
        </div>

        {right && <div className="flex-shrink-0">{right}</div>}
      </button>

      {open && hasChildren && (
        <div className="ml-4 pl-4 border-l border-white/[0.06]">
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
    <div className="flex items-center gap-2 py-2 px-2.5 rounded-lg hover:bg-white/[0.03] transition-colors">
      <span className="w-4 flex-shrink-0 flex items-center justify-center">
        {status ? <StatusDot status={status} /> : <span className="w-1.5 h-1.5 rounded-full bg-white/[0.08]" />}
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-sm">{label}</span>
        {sublabel && <span className="text-xs text-white/30 ml-2">{sublabel}</span>}
      </div>
      {right && <div className="flex-shrink-0 text-xs text-white/30">{right}</div>}
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

  const agentNames: Record<string, string> = {
    'TechnicalTrendAgent': 'Lena Karlsson',
    'TechnicalSignalAgent': 'David Osei',
    'TechnicalTimingAgent': 'Mika Tanaka',
    'SocialSentimentAgent': 'Priya Sharma',
    'MarketSentimentAgent': 'Alexei Volkov',
    'SmartMoneySentimentAgent': 'Sofia Reyes',
    'ValuationAgent': 'Henrik Larsen',
    'CyclePositionAgent': 'Amara Obi',
    'CryptoMacroAgent': 'Lucas Weber',
    'ExternalMacroAgent': 'Fatima Al-Rashid',
    'NetworkHealthAgent': 'Jin Park',
    'CapitalFlowAgent': 'Camille Dubois',
  };
  const managerNames: Record<string, string> = {
    'technical': 'Oscar Brennan',
    'sentiment': 'Yara Haddad',
    'fundamental': 'Isaac Thornton',
    'macro': 'Zara Kimathi',
    'onchain': 'Nikolai Petrov',
  };
  const getName = (agent: Agent) => {
    if (agent.agent_class && agentNames[agent.agent_class]) {
      return `${agentNames[agent.agent_class]} — ${agent.agent_class.replace(/([A-Z])/g, ' $1').trim()}`;
    }
    return agent.role;
  };

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
          <div className="w-5 h-5 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
          <p className="text-sm text-white/30">Loading organization...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto slide-up">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2.5 mb-3">
          <Network size={18} className="text-amber-400/60" />
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Org Chart</p>
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Organization</h1>
        <p className="text-sm text-white/40 mt-1">
          {teams.length} teams, {agents.length} agents. Click to expand.
        </p>
      </div>

      {/* Tree */}
      <div className="glass-card p-4">
        <Node label="Marcus Blackwell — CEO" subtitle="Strategic leadership" badge="EXECUTIVE" badgeColor="bg-amber-400/10 text-amber-400 ring-amber-400/20" defaultOpen={true}>

          <Node label="Elena Vasquez — COO" subtitle="Coin selection">
            <Leaf label="Selects which coins to analyze each cycle based on volume, momentum, and CEO strategy" />
          </Node>

          <Node label="Tobias Richter — CRO" subtitle="Risk management">
            <Leaf label="Sets position limits, drawdown thresholds, and confidence minimums per cycle" />
            <Node label="James Hartley — Risk Manager" subtitle="Enforces CRO rules on all trades">
              <Leaf label="Position sizing (quarter-Kelly)" />
              <Leaf label="Drawdown halt" />
              <Leaf label="Confidence gates" />
            </Node>
          </Node>

          <Node label="Board of Directors" subtitle="Organizational governance" badge="META" badgeColor="bg-purple-400/10 text-purple-400 ring-purple-400/20">
            <Leaf label="Victor Okafor — CSO" sublabel="Team creation and dissolution" />
            <Leaf label="Nadia Chen — CTO" sublabel="Agent assignment and prompt writing" />
            <Leaf label="Raphael Moreno — CPO" sublabel="Probation and firing pipeline" />
          </Node>

          <Node label="Analysis Division" subtitle={`${teams.length} teams, ${agents.filter(a => a.team_name).length} assigned agents`} defaultOpen={true}>
            {teams.map((team) => {
              const ta = agentsByTeam[team.name] || [];
              return (
                <Node
                  key={team.id}
                  label={`${team.name.charAt(0).toUpperCase() + team.name.slice(1)} Team`}
                  badge={team.is_system ? 'SYSTEM' : 'DYNAMIC'}
                  badgeColor={team.is_system ? 'bg-amber-400/10 text-amber-400 ring-amber-400/20' : 'bg-blue-400/10 text-blue-400 ring-blue-400/20'}
                  right={<span className="text-xs text-white/30">{team.weight.toFixed(1)}x</span>}
                >
                  <Leaf label={`${managerNames[team.name] || 'Manager'} — ${team.name.charAt(0).toUpperCase() + team.name.slice(1)} Manager`} sublabel="Synthesizes agent signals" />
                  {ta.map((agent) => (
                    <Leaf
                      key={agent.id}
                      label={getName(agent)}
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

          <Node label="Diana Frost — Head of Portfolio" subtitle="Segment allocation">
            <Leaf label="L1s segment" />
            <Leaf label="DeFi segment" />
            <Leaf label="L2s segment" />
            <Leaf label="Memes segment" />
            <Leaf label="AI segment" />
            <Leaf label="Infrastructure segment" />
          </Node>

          <Node label="Kai Nakamura — Head of Execution" subtitle="Trade lifecycle">
            <Leaf label="Paper Trader" sublabel="Executes orders" />
            <Leaf label="Trade Monitor" sublabel="SL / TP / trailing stops" />
            <Leaf label="Trade Ledger" sublabel="P&L tracking and calibration" />
          </Node>

          <Node label="Soren Lindqvist — Signal Aggregator" subtitle="Deterministic, no LLM">
            <Leaf label="Bayesian log-odds combination" />
            <Leaf label="Macro gate / Technical gate" />
            <Leaf label="Polarization detection" />
            <Leaf label="Close-call detection" />
          </Node>

          {unassigned.length > 0 && (
            <Node label={`Unassigned (${unassigned.length})`} subtitle="Awaiting Board assignment" badge="PENDING" badgeColor="bg-gray-400/10 text-gray-400 ring-gray-400/20" defaultOpen={true}>
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
