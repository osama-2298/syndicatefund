'use client';

import { useEffect, useState } from 'react';
import { Loader2, Shield, Users, Weight, Radio, BarChart3 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* ------------------------------------------------------------------ */
/*  DESIGN CONSTANTS                                                   */
/* ------------------------------------------------------------------ */

const TEAM_COLORS: Record<string, string> = {
  technical: 'from-blue-500 to-cyan-500',
  sentiment: 'from-purple-500 to-pink-500',
  fundamental: 'from-yellow-500 to-amber-500',
  macro: 'from-cyan-500 to-teal-500',
  onchain: 'from-emerald-500 to-green-500',
  'on-chain': 'from-emerald-500 to-green-500',
};

const AGENT_COLORS: Record<string, string> = {
  TechnicalTrendAgent: 'from-blue-500 to-cyan-500',
  TechnicalSignalAgent: 'from-blue-400 to-indigo-500',
  TechnicalTimingAgent: 'from-sky-500 to-blue-500',
  SocialSentimentAgent: 'from-purple-500 to-pink-500',
  MarketSentimentAgent: 'from-violet-500 to-purple-600',
  SmartMoneySentimentAgent: 'from-fuchsia-500 to-purple-500',
  ValuationAgent: 'from-yellow-500 to-amber-500',
  CyclePositionAgent: 'from-amber-500 to-orange-500',
  CryptoMacroAgent: 'from-cyan-500 to-teal-500',
  ExternalMacroAgent: 'from-teal-500 to-emerald-500',
  NetworkHealthAgent: 'from-emerald-500 to-green-500',
  CapitalFlowAgent: 'from-green-500 to-lime-500',
};

/* ------------------------------------------------------------------ */
/*  TYPES                                                              */
/* ------------------------------------------------------------------ */

interface TeamSummary {
  id: string;
  name: string;
  discipline: string;
  status: string;
  weight: number;
  activation_mode: string;
  min_agents: number;
  is_system: boolean;
  created_by: string;
  created_at: string;
  agent_count: number;
  active_agent_count: number;
  data_keys: string[];
}

interface AgentSummary {
  id: string;
  team_id: string | null;
  team_name: string | null;
  role: string;
  agent_class: string | null;
  status: string;
  total_signals: number;
  accuracy: number;
}

/* ------------------------------------------------------------------ */
/*  HELPERS                                                            */
/* ------------------------------------------------------------------ */

function getGradient(name: string): string {
  const key = name.toLowerCase().replace(/[\s_]+/g, '-');
  return TEAM_COLORS[key] || 'from-amber-500 to-orange-500';
}

function getAgentGradient(agentClass: string | null, teamName: string | null): string {
  if (agentClass && AGENT_COLORS[agentClass]) return AGENT_COLORS[agentClass];
  if (teamName) {
    const key = teamName.toLowerCase().replace(/[\s_]+/g, '-');
    if (TEAM_COLORS[key]) return TEAM_COLORS[key];
  }
  return 'from-amber-500 to-orange-500';
}

function getAgentInitial(agent: AgentSummary): string {
  const name = agent.agent_class || agent.role;
  const caps = name.replace(/Agent$/, '').match(/[A-Z]/g);
  if (caps && caps.length >= 2) return caps.slice(0, 2).join('');
  return name.slice(0, 2).toUpperCase();
}

/* ------------------------------------------------------------------ */
/*  SUB-COMPONENTS                                                     */
/* ------------------------------------------------------------------ */

function StatCell({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) {
  return (
    <div>
      <div className="flex items-center gap-1 mb-1">
        <Icon size={10} className="text-white/15" />
        <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-white/25">{label}</p>
      </div>
      <p className="text-base font-bold font-mono tabular-nums text-white/90">{value}</p>
    </div>
  );
}

function TeamCard({ team, agents }: { team: TeamSummary; agents: AgentSummary[] }) {
  const gradient = getGradient(team.name);
  const teamAgents = agents.filter(a => a.team_id === team.id);
  const agentsWithSignals = teamAgents.filter(a => a.total_signals >= 5);
  const avgAccuracy = agentsWithSignals.length > 0
    ? agentsWithSignals.reduce((s, a) => s + a.accuracy, 0) / agentsWithSignals.length
    : 0;
  const totalSignals = teamAgents.reduce((s, a) => s + a.total_signals, 0);

  return (
    <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl overflow-hidden flex flex-col">
      {/* Top gradient border */}
      <div className={`h-[3px] bg-gradient-to-r ${gradient}`} />

      <div className="p-5 flex flex-col flex-1">
        {/* Team name + badge */}
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="text-lg font-bold text-white/90 capitalize tracking-tight">{team.name}</h3>
          <span className={`flex-shrink-0 text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
            team.is_system
              ? 'text-amber-400 bg-amber-400/10 ring-amber-400/30'
              : 'text-blue-400 bg-blue-400/10 ring-blue-400/30'
          }`}>
            {team.is_system ? 'SYSTEM' : 'DYNAMIC'}
          </span>
        </div>

        <p className="text-xs text-white/25 leading-relaxed line-clamp-2 mb-4">{team.discipline}</p>

        {/* Divider */}
        <div className="h-px bg-white/[0.06] mb-4" />

        {/* Stats 2x2 grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 mb-4">
          <StatCell label="Agents" value={`${team.active_agent_count}/${team.agent_count}`} icon={Users} />
          <StatCell label="Weight" value={`${team.weight.toFixed(1)}x`} icon={Weight} />
          <StatCell label="Signals" value={totalSignals.toLocaleString()} icon={Radio} />
          <StatCell
            label="Accuracy"
            value={agentsWithSignals.length > 0 ? `${Math.round(avgAccuracy * 100)}%` : '\u2014'}
            icon={BarChart3}
          />
        </div>

        {/* Agent dots */}
        <div className="mt-auto pt-3 border-t border-white/[0.04]">
          <div className="flex items-center gap-2 flex-wrap">
            {teamAgents.map((agent) => {
              const agGradient = getAgentGradient(agent.agent_class, team.name);
              const initial = getAgentInitial(agent);
              return (
                <div
                  key={agent.id}
                  className={`w-7 h-7 rounded-full bg-gradient-to-br ${agGradient} flex items-center justify-center`}
                  title={agent.agent_class || agent.role}
                >
                  <span className="text-[8px] font-bold text-white/80">{initial}</span>
                </div>
              );
            })}
            {teamAgents.length === 0 && (
              <span className="text-[10px] text-white/15 italic">No agents assigned</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DataCoverageMatrix({ teams }: { teams: TeamSummary[] }) {
  // Collect all unique data keys
  const allKeys = Array.from(new Set(teams.flatMap(t => t.data_keys))).sort();
  if (allKeys.length === 0) return null;

  return (
    <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.06]">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Data Coverage Matrix</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-white/30 sticky left-0 bg-[#0d0d15] z-10">
                Data Key
              </th>
              {teams.map((team) => {
                const gradient = getGradient(team.name);
                return (
                  <th key={team.id} className="px-3 py-2.5 text-center">
                    <span className={`inline-block text-[9px] font-bold uppercase tracking-wider bg-gradient-to-r ${gradient} bg-clip-text text-transparent`}>
                      {team.name}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {allKeys.map((key, idx) => (
              <tr key={key} className={`border-b border-white/[0.03] ${idx % 2 === 0 ? '' : 'bg-white/[0.01]'}`}>
                <td className="px-4 py-1.5 text-[11px] font-mono text-white/40 sticky left-0 bg-[#0d0d15] z-10">
                  {key}
                </td>
                {teams.map((team) => {
                  const has = team.data_keys.includes(key);
                  const gradient = getGradient(team.name);
                  return (
                    <td key={team.id} className="px-3 py-1.5 text-center">
                      {has ? (
                        <span className={`inline-block w-3 h-3 rounded-sm bg-gradient-to-br ${gradient} opacity-70`} />
                      ) : (
                        <span className="inline-block w-3 h-3 rounded-sm bg-white/[0.03]" />
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN PAGE                                                          */
/* ------------------------------------------------------------------ */

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/teams`).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/agents`).then(r => r.json()),
    ])
      .then(([teamsData, agentsData]) => {
        setTeams(teamsData);
        setAgents(agentsData);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Team Overview</h1>
        <p className="text-sm text-white/30 mt-1">
          {loading
            ? 'Loading teams...'
            : `${teams.length} analysis teams \u2014 ${teams.filter(t => t.is_system).length} system, ${teams.filter(t => !t.is_system).length} dynamic`}
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex items-center justify-center py-24">
          <Loader2 size={24} className="text-white/20 animate-spin" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex flex-col items-center justify-center py-24">
          <Shield size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">Could not load teams</p>
          <p className="text-xs text-white/20 mt-1">Ensure the API server is running on {API_BASE}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && teams.length === 0 && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex flex-col items-center justify-center py-24">
          <Shield size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">No teams found</p>
          <p className="text-xs text-white/20 mt-1">Run the seed script to create system teams</p>
        </div>
      )}

      {/* Main Content */}
      {!loading && !error && teams.length > 0 && (
        <>
          {/* Team Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {teams.map((team) => (
              <TeamCard key={team.id} team={team} agents={agents} />
            ))}
          </div>

          {/* Data Coverage Matrix */}
          <DataCoverageMatrix teams={teams} />
        </>
      )}
    </div>
  );
}
