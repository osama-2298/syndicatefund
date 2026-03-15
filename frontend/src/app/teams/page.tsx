import { api, TeamSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function TeamsPage() {
  let teams: TeamSummary[] = [];
  try {
    teams = await api.getTeams();
  } catch (e) {}

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Teams</h1>
        <p className="text-hive-muted">{teams.length} analysis teams</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map((team) => (
          <div key={team.id} className="bg-hive-card border border-hive-border rounded-xl p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold capitalize">{team.name}</h3>
                <p className="text-sm text-hive-muted mt-1 line-clamp-2">{team.discipline}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded flex-shrink-0 ${
                team.is_system ? 'bg-amber-500/20 text-amber-400' : 'bg-hive-blue/20 text-hive-blue'
              }`}>
                {team.is_system ? 'SYSTEM' : 'PROVISIONAL'}
              </span>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-hive-muted">Agents</p>
                <p className="text-lg font-bold">{team.active_agent_count}<span className="text-sm text-hive-muted">/{team.agent_count}</span></p>
              </div>
              <div>
                <p className="text-xs text-hive-muted">Weight</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-1.5 bg-hive-border rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        team.weight >= 1.2 ? 'bg-hive-green' : team.weight <= 0.5 ? 'bg-hive-red' : 'bg-hive-accent'
                      }`}
                      style={{ width: `${Math.min(team.weight * 50, 100)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{team.weight.toFixed(1)}x</span>
                </div>
              </div>
            </div>

            {/* Data Keys */}
            <div className="flex flex-wrap gap-1">
              {team.data_keys.slice(0, 5).map((key) => (
                <span key={key} className="text-xs bg-hive-border text-hive-muted px-1.5 py-0.5 rounded">
                  {key}
                </span>
              ))}
              {team.data_keys.length > 5 && (
                <span className="text-xs text-hive-muted">+{team.data_keys.length - 5} more</span>
              )}
            </div>
          </div>
        ))}

        {teams.length === 0 && (
          <div className="col-span-full text-center py-12 text-hive-muted">
            No teams found. Run the seed script to create system teams.
          </div>
        )}
      </div>
    </div>
  );
}
