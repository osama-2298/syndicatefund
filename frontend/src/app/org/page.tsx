import { api, AgentSummary, TeamSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    founding: 'bg-amber-400',
    active: 'bg-hive-green',
    assigned: 'bg-hive-blue',
    registered: 'bg-gray-400',
    probation: 'bg-orange-400',
    fired: 'bg-hive-red',
  };
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status] || 'bg-gray-400'}`} />;
}

export default async function OrgPage() {
  let teams: TeamSummary[] = [];
  let agents: AgentSummary[] = [];
  try {
    [teams, agents] = await Promise.all([api.getTeams(), api.getAgents()]);
  } catch (e) {}

  // Group agents by team
  const agentsByTeam: Record<string, AgentSummary[]> = {};
  const unassigned: AgentSummary[] = [];
  for (const agent of agents) {
    if (agent.team_name) {
      if (!agentsByTeam[agent.team_name]) agentsByTeam[agent.team_name] = [];
      agentsByTeam[agent.team_name].push(agent);
    } else {
      unassigned.push(agent);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Organization</h1>
        <p className="text-hive-muted">
          {teams.length} teams · {agents.length} agents · Board of Directors manages structure
        </p>
      </div>

      {/* Executive Layer */}
      <div className="flex justify-center">
        <div className="bg-hive-card border border-hive-accent/30 rounded-xl p-4 text-center">
          <p className="text-xs text-hive-accent mb-1">EXECUTIVE</p>
          <p className="font-bold">Board of Directors</p>
          <div className="flex gap-4 mt-2 text-xs text-hive-muted">
            <span>CSO</span>
            <span>CTO</span>
            <span>CPO</span>
          </div>
        </div>
      </div>

      {/* Connector line */}
      <div className="flex justify-center">
        <div className="w-px h-8 bg-hive-border" />
      </div>

      {/* CEO / COO / CRO */}
      <div className="flex justify-center gap-4">
        {['CEO — Regime & Strategy', 'COO — Coin Selection', 'CRO — Risk Rules'].map((role) => (
          <div key={role} className="bg-hive-card border border-hive-border rounded-lg px-4 py-2 text-center text-sm">
            <p className="font-medium">{role.split(' — ')[0]}</p>
            <p className="text-xs text-hive-muted">{role.split(' — ')[1]}</p>
          </div>
        ))}
      </div>

      {/* Connector */}
      <div className="flex justify-center">
        <div className="w-px h-8 bg-hive-border" />
      </div>

      {/* Teams Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map((team) => {
          const teamAgents = agentsByTeam[team.name] || [];
          return (
            <div key={team.id} className="bg-hive-card border border-hive-border rounded-xl overflow-hidden">
              {/* Team Header */}
              <div className="px-4 py-3 border-b border-hive-border flex items-center justify-between">
                <div>
                  <h3 className="font-bold capitalize">{team.name}</h3>
                  <p className="text-xs text-hive-muted">{team.discipline.slice(0, 60)}...</p>
                </div>
                <div className="text-right">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    team.is_system ? 'bg-amber-500/20 text-amber-400' : 'bg-hive-blue/20 text-hive-blue'
                  }`}>
                    {team.is_system ? 'SYSTEM' : 'DYNAMIC'}
                  </span>
                  <p className="text-xs text-hive-muted mt-1">{team.weight.toFixed(1)}x weight</p>
                </div>
              </div>

              {/* Manager */}
              <div className="px-4 py-2 border-b border-hive-border/50 bg-hive-border/10">
                <p className="text-xs text-hive-muted">Manager</p>
                <p className="text-sm font-medium capitalize">{team.name} Manager</p>
              </div>

              {/* Agents */}
              <div className="divide-y divide-hive-border/30">
                {teamAgents.length === 0 ? (
                  <div className="px-4 py-3 text-sm text-hive-muted">No agents assigned</div>
                ) : (
                  teamAgents.map((agent) => (
                    <div key={agent.id} className="px-4 py-2.5 flex items-center justify-between hover:bg-hive-border/10">
                      <div className="flex items-center gap-2">
                        <StatusDot status={agent.status} />
                        <div>
                          <p className="text-sm font-medium">{agent.agent_class || agent.role}</p>
                          <p className="text-xs text-hive-muted">{agent.model} · {agent.provider}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          agent.status === 'founding' ? 'bg-amber-500/20 text-amber-400' :
                          agent.status === 'active' ? 'bg-hive-green/20 text-hive-green' :
                          'bg-hive-border text-hive-muted'
                        }`}>
                          {agent.status}
                        </span>
                        {agent.total_signals > 0 && (
                          <p className="text-xs text-hive-muted mt-0.5">
                            {Math.round(agent.accuracy * 100)}% · {agent.total_signals} signals
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Unassigned Agents */}
      {unassigned.length > 0 && (
        <div className="bg-hive-card border border-hive-border rounded-xl p-4">
          <h3 className="font-bold mb-3">Unassigned Agents ({unassigned.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {unassigned.map((agent) => (
              <div key={agent.id} className="flex items-center gap-2 p-2 rounded bg-hive-border/20">
                <StatusDot status={agent.status} />
                <span className="text-sm">{agent.role}</span>
                <span className="text-xs text-hive-muted ml-auto">{agent.provider} · {agent.model}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
