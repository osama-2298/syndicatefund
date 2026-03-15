import { api, CycleSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function CyclesPage() {
  let cycles: CycleSummary[] = [];
  try {
    cycles = await api.getCycles(50);
  } catch (e) {}

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Cycle History</h1>
        <p className="text-hive-muted">Pipeline runs every 4 hours aligned to UTC boundaries</p>
      </div>

      <div className="bg-hive-card border border-hive-border rounded-xl overflow-hidden">
        {cycles.length === 0 ? (
          <div className="px-5 py-12 text-center text-hive-muted">
            No cycles recorded yet. Start the server with <code className="bg-hive-border px-2 py-0.5 rounded text-sm">python -m hivemind.main --serve</code>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-sm text-hive-muted border-b border-hive-border">
                <th className="text-left px-5 py-3">Cycle</th>
                <th className="text-left px-5 py-3">Started</th>
                <th className="text-left px-5 py-3">Regime</th>
                <th className="text-right px-5 py-3">Coins</th>
                <th className="text-right px-5 py-3">Signals</th>
                <th className="text-right px-5 py-3">Orders</th>
                <th className="text-right px-5 py-3">Portfolio</th>
                <th className="text-right px-5 py-3">Duration</th>
                <th className="text-left px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((cycle) => {
                const isRunning = !cycle.completed_at;
                const hasError = !!cycle.error;
                return (
                  <tr key={cycle.id} className="border-b border-hive-border/50 hover:bg-hive-border/20">
                    <td className="px-5 py-3 font-medium text-hive-muted">#{cycle.id}</td>
                    <td className="px-5 py-3 text-sm">
                      {new Date(cycle.started_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        cycle.regime === 'bull' ? 'bg-hive-green/20 text-hive-green' :
                        cycle.regime === 'bear' ? 'bg-hive-red/20 text-hive-red' :
                        cycle.regime === 'crisis' ? 'bg-red-900/30 text-red-400' :
                        'bg-hive-border text-hive-muted'
                      }`}>
                        {(cycle.regime ?? '—').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">{cycle.coins_analyzed}</td>
                    <td className="px-5 py-3 text-right">{cycle.signals_produced}</td>
                    <td className="px-5 py-3 text-right">{cycle.orders_executed}</td>
                    <td className="px-5 py-3 text-right">
                      {cycle.portfolio_value ? `$${cycle.portfolio_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—'}
                    </td>
                    <td className="px-5 py-3 text-right text-hive-muted">
                      {cycle.duration_secs ? `${Math.round(cycle.duration_secs)}s` : '—'}
                    </td>
                    <td className="px-5 py-3">
                      {isRunning ? (
                        <span className="text-xs bg-hive-blue/20 text-hive-blue px-2 py-0.5 rounded animate-pulse">RUNNING</span>
                      ) : hasError ? (
                        <span className="text-xs bg-hive-red/20 text-hive-red px-2 py-0.5 rounded" title={cycle.error ?? ''}>ERROR</span>
                      ) : (
                        <span className="text-xs bg-hive-green/20 text-hive-green px-2 py-0.5 rounded">DONE</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
