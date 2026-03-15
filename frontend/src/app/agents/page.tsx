import { api, AgentSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    founding: 'bg-amber-500/20 text-amber-400',
    active: 'bg-hive-green/20 text-hive-green',
    assigned: 'bg-hive-blue/20 text-hive-blue',
    registered: 'bg-hive-border text-hive-muted',
    probation: 'bg-orange-500/20 text-orange-400',
    fired: 'bg-hive-red/20 text-hive-red',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${colors[status] || 'bg-hive-border text-hive-muted'}`}>
      {status.toUpperCase()}
    </span>
  );
}

function AccuracyBar({ accuracy, signals }: { accuracy: number; signals: number }) {
  if (signals < 5) return <span className="text-hive-muted text-sm">{'\u2014'}</span>;
  const pct = Math.round(accuracy * 100);
  const color = pct >= 60 ? 'bg-hive-green' : pct >= 40 ? 'bg-hive-accent' : 'bg-hive-red';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-hive-border rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm">{pct}%</span>
    </div>
  );
}

export default async function AgentsPage() {
  let agents: AgentSummary[] = [];
  try {
    agents = await api.getAgents();
  } catch (e) {
    // API not available
  }

  const founding = agents.filter(a => a.status === 'founding');
  const contributor = agents.filter(a => a.status !== 'founding');

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Agents</h1>
        <p className="text-hive-muted">
          {agents.length} total — {founding.length} founding, {contributor.length} contributor
        </p>
      </div>

      {/* Founding Agents */}
      <div className="bg-hive-card border border-hive-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-hive-border flex items-center justify-between">
          <h2 className="text-lg font-semibold">Founding Agents</h2>
          <span className="text-xs text-hive-accent bg-hive-accent/10 px-2 py-1 rounded">PERMANENT</span>
        </div>
        <table className="w-full">
          <thead>
            <tr className="text-sm text-hive-muted border-b border-hive-border">
              <th className="text-left px-5 py-3">Agent</th>
              <th className="text-left px-5 py-3">Team</th>
              <th className="text-left px-5 py-3">Model</th>
              <th className="text-left px-5 py-3">Status</th>
              <th className="text-right px-5 py-3">Signals</th>
              <th className="text-right px-5 py-3">Accuracy</th>
            </tr>
          </thead>
          <tbody>
            {founding.map((agent) => (
              <tr key={agent.id} className="border-b border-hive-border/50 hover:bg-hive-border/20">
                <td className="px-5 py-3">
                  <span className="font-medium">{agent.agent_class || agent.role}</span>
                </td>
                <td className="px-5 py-3 text-hive-muted">{agent.team_name ?? '\u2014'}</td>
                <td className="px-5 py-3 text-sm text-hive-muted">{agent.model}</td>
                <td className="px-5 py-3"><StatusBadge status={agent.status} /></td>
                <td className="px-5 py-3 text-right">{agent.total_signals}</td>
                <td className="px-5 py-3 text-right">
                  <AccuracyBar accuracy={agent.accuracy} signals={agent.total_signals} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Contributor Agents */}
      {contributor.length > 0 && (
        <div className="bg-hive-card border border-hive-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-hive-border">
            <h2 className="text-lg font-semibold">Contributor Agents</h2>
          </div>
          <table className="w-full">
            <thead>
              <tr className="text-sm text-hive-muted border-b border-hive-border">
                <th className="text-left px-5 py-3">Role</th>
                <th className="text-left px-5 py-3">Team</th>
                <th className="text-left px-5 py-3">Provider</th>
                <th className="text-left px-5 py-3">Status</th>
                <th className="text-right px-5 py-3">Signals</th>
                <th className="text-right px-5 py-3">Accuracy</th>
                <th className="text-right px-5 py-3">Quarantine</th>
              </tr>
            </thead>
            <tbody>
              {contributor.map((agent) => (
                <tr key={agent.id} className="border-b border-hive-border/50 hover:bg-hive-border/20">
                  <td className="px-5 py-3 font-medium">{agent.role}</td>
                  <td className="px-5 py-3 text-hive-muted">{agent.team_name ?? 'Unassigned'}</td>
                  <td className="px-5 py-3 text-sm text-hive-muted">{agent.provider}</td>
                  <td className="px-5 py-3"><StatusBadge status={agent.status} /></td>
                  <td className="px-5 py-3 text-right">{agent.total_signals}</td>
                  <td className="px-5 py-3 text-right">
                    <AccuracyBar accuracy={agent.accuracy} signals={agent.total_signals} />
                  </td>
                  <td className="px-5 py-3 text-right text-hive-muted">
                    {agent.quarantine_signals_remaining > 0 ? `${agent.quarantine_signals_remaining} left` : '\u2014'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
