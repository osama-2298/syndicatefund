'use client';

import { useEffect, useState } from 'react';
import { Shield, Loader2, Users } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

const teamGradients: Record<string, string> = {
  technical: 'from-blue-500 to-cyan-500',
  sentiment: 'from-purple-500 to-pink-500',
  fundamental: 'from-yellow-500 to-amber-500',
  macro: 'from-cyan-500 to-teal-500',
  'on-chain': 'from-emerald-500 to-green-500',
  onchain: 'from-emerald-500 to-green-500',
};

function getGradient(name: string): string {
  const key = name.toLowerCase().replace(/[\s_]+/g, '-');
  return teamGradients[key] || 'from-amber-500 to-orange-500';
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/teams`)
      .then((r) => r.json())
      .then((data) => {
        setTeams(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  return (
    <div className="slide-up space-y-8">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-white/[0.04]">
          <Shield size={20} className="text-amber-400/60" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Teams</h1>
          <p className="text-sm text-white/40 mt-1">
            {loading ? 'Loading teams...' : `${teams.length} analysis teams`}
          </p>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="glass-card flex items-center justify-center py-20">
          <Loader2 size={24} className="text-white/20 animate-spin" />
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="glass-card flex flex-col items-center justify-center py-20">
          <Shield size={40} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">Could not load teams</p>
          <p className="text-xs text-white/20 mt-1">Make sure the API server is running</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && teams.length === 0 && (
        <div className="glass-card flex flex-col items-center justify-center py-20">
          <Shield size={40} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">No teams found</p>
          <p className="text-xs text-white/20 mt-1">Run the seed script to create system teams</p>
        </div>
      )}

      {/* Team Cards Grid */}
      {!loading && !error && teams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {teams.map((team) => {
            const gradient = getGradient(team.name);
            return (
              <div key={team.id} className="glass-card overflow-hidden group hover:bg-white/[0.05] transition-all duration-300">
                {/* Gradient top border */}
                <div className={`h-[2px] bg-gradient-to-r ${gradient}`} />

                <div className="p-5 space-y-4">
                  {/* Team name + badge */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="text-sm font-bold text-white/90 capitalize">{team.name}</h3>
                      <p className="text-xs text-white/30 mt-1 line-clamp-2 leading-relaxed">{team.discipline}</p>
                    </div>
                    <span className={`flex-shrink-0 text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
                      team.is_system
                        ? 'text-amber-400 bg-amber-400/10 ring-amber-400/30'
                        : 'text-blue-400 bg-blue-400/10 ring-blue-400/30'
                    }`}>
                      {team.is_system ? 'SYSTEM' : 'PROVISIONAL'}
                    </span>
                  </div>

                  {/* Stats row */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-1">Agents</p>
                      <div className="flex items-baseline gap-1">
                        <Users size={12} className="text-white/20" />
                        <span className="text-lg font-bold tabular-nums text-white/90">{team.active_agent_count}</span>
                        <span className="text-xs text-white/20">/ {team.agent_count}</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-1">Weight</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              team.weight >= 1.2 ? 'bg-emerald-400' : team.weight <= 0.5 ? 'bg-red-400' : 'bg-amber-400'
                            }`}
                            style={{ width: `${Math.min(team.weight * 50, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium tabular-nums text-white/60">{team.weight.toFixed(1)}x</span>
                      </div>
                    </div>
                  </div>

                  {/* Data key pills */}
                  <div className="flex flex-wrap gap-1">
                    {team.data_keys.slice(0, 5).map((key) => (
                      <span
                        key={key}
                        className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-white/[0.04] text-white/30 ring-1 ring-inset ring-white/[0.06]"
                      >
                        {key}
                      </span>
                    ))}
                    {team.data_keys.length > 5 && (
                      <span className="text-[10px] text-white/20 self-center ml-0.5">
                        +{team.data_keys.length - 5} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
