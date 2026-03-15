import { api, Portfolio, CycleSummary, AgentSummary, TeamSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default async function Dashboard() {
  let portfolio: Portfolio | null = null;
  let cycles: CycleSummary[] = [];
  let currentCycle: any = null;
  let trades: any = null;
  let agents: AgentSummary[] = [];
  let teams: TeamSummary[] = [];

  try {
    [portfolio, cycles, currentCycle, trades, agents, teams] = await Promise.all([
      api.getPortfolio(),
      api.getCycles(5),
      api.getCurrentCycle(),
      fetch(`${API_BASE}/api/v1/portfolio/trades`, { next: { revalidate: 30 } }).then(r => r.json()).catch(() => null),
      api.getAgents(),
      api.getTeams(),
    ]);
  } catch (e) {}

  const positions = portfolio?.positions ?? [];
  const cash = portfolio?.cash ?? 100000;
  const invested = positions.reduce((sum, p) => sum + p.quantity * (p.current_price || p.entry_price), 0);
  const totalValue = cash + invested;
  const returnPct = ((totalValue - 100000) / 100000) * 100;
  const regime = currentCycle?.regime ?? cycles?.[0]?.regime ?? null;
  const closedTrades = trades?.trades ?? [];

  const activeAgents = agents.filter(a => ['founding', 'active', 'assigned'].includes(a.status));
  const totalSignals = agents.reduce((sum, a) => sum + a.total_signals, 0);
  const avgAccuracy = agents.filter(a => a.total_signals >= 5).reduce((sum, a, _, arr) => sum + a.accuracy / arr.length, 0);
  const lastCycle = cycles?.[0];

  return (
    <div className="space-y-6">
      {/* Header with system status */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-1">Dashboard</h1>
          <p className="text-hive-muted">Multi-agent crypto analysis platform</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-hive-card border border-hive-border rounded-lg px-3 py-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-hive-green opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-hive-green"></span>
            </span>
            <span className="text-sm text-hive-text">System Active</span>
          </div>
          {lastCycle && (
            <div className="bg-hive-card border border-hive-border rounded-lg px-3 py-2 text-sm text-hive-muted">
              Last cycle: {new Date(lastCycle.started_at).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {/* Primary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="bg-hive-card border border-hive-border rounded-xl p-4">
          <p className="text-xs text-hive-muted mb-1">Portfolio Value</p>
          <p className={`text-xl font-bold ${returnPct > 0 ? 'text-hive-green' : returnPct < 0 ? 'text-hive-red' : 'text-hive-text'}`}>
            ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-hive-muted mt-1">Paper trading</p>
        </div>

        <div className="bg-hive-card border border-hive-border rounded-xl p-4">
          <p className="text-xs text-hive-muted mb-1">Total Return</p>
          <p className={`text-xl font-bold ${returnPct > 0 ? 'text-hive-green' : returnPct < 0 ? 'text-hive-red' : 'text-hive-text'}`}>
            {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%
          </p>
          <p className="text-xs text-hive-muted mt-1">{returnPct >= 0 ? '+' : ''}${(totalValue - 100000).toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
        </div>

        <div className="bg-hive-card border border-hive-border rounded-xl p-4">
          <p className="text-xs text-hive-muted mb-1">Invested</p>
          <p className="text-xl font-bold text-hive-text">${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
          <p className="text-xs text-hive-muted mt-1">${cash.toLocaleString(undefined, { maximumFractionDigits: 0 })} cash</p>
        </div>

        <div className="bg-hive-card border border-hive-border rounded-xl p-4">
          <p className="text-xs text-hive-muted mb-1">Active Agents</p>
          <p className="text-xl font-bold text-hive-text">{activeAgents.length}</p>
          <p className="text-xs text-hive-muted mt-1">{teams.length} teams</p>
        </div>

        <div className="bg-hive-card border border-hive-border rounded-xl p-4">
          <p className="text-xs text-hive-muted mb-1">Total Signals</p>
          <p className="text-xl font-bold text-hive-text">{totalSignals.toLocaleString()}</p>
          <p className="text-xs text-hive-muted mt-1">{avgAccuracy > 0 ? `${(avgAccuracy * 100).toFixed(0)}% accuracy` : 'Calibrating...'}</p>
        </div>

        <div className="bg-hive-card border border-hive-border rounded-xl p-4">
          <p className="text-xs text-hive-muted mb-1">Market Regime</p>
          <p className={`text-xl font-bold ${
            regime === 'bull' ? 'text-hive-green' : regime === 'bear' || regime === 'crisis' ? 'text-hive-red' : 'text-hive-text'
          }`}>
            {regime ? regime.toUpperCase() : 'N/A'}
          </p>
          <p className="text-xs text-hive-muted mt-1">{positions.length} open position{positions.length !== 1 ? 's' : ''}</p>
        </div>
      </div>

      {/* Teams Overview - compact horizontal bar */}
      <div className="bg-hive-card border border-hive-border rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-hive-muted uppercase tracking-wide">Team Status</h2>
          <a href="/org" className="text-xs text-hive-accent hover:underline">View org chart</a>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {teams.map((team) => (
            <div key={team.id} className="flex items-center gap-2 p-2 rounded-lg bg-hive-bg">
              <span className="relative flex h-2 w-2 flex-shrink-0">
                <span className={`relative inline-flex rounded-full h-2 w-2 ${team.active_agent_count > 0 ? 'bg-hive-green' : 'bg-gray-500'}`}></span>
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium capitalize truncate">{team.name}</p>
                <p className="text-xs text-hive-muted">{team.active_agent_count} agents · {team.weight.toFixed(1)}x</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Open Positions */}
      <div className="bg-hive-card border border-hive-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-hive-border flex items-center justify-between">
          <h2 className="text-lg font-semibold">Open Positions</h2>
          {positions.length > 0 && (
            <span className="text-sm text-hive-muted">
              {positions.length} position{positions.length !== 1 ? 's' : ''} — ${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })} invested
            </span>
          )}
        </div>
        {positions.length === 0 ? (
          <div className="px-5 py-8 text-center text-hive-muted">
            No open positions. Waiting for next cycle to generate trades.
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-sm text-hive-muted border-b border-hive-border">
                <th className="text-left px-5 py-3">Symbol</th>
                <th className="text-left px-5 py-3">Side</th>
                <th className="text-right px-5 py-3">Size</th>
                <th className="text-right px-5 py-3">Entry</th>
                <th className="text-right px-5 py-3">Current</th>
                <th className="text-right px-5 py-3">P&L</th>
                <th className="text-right px-5 py-3">P&L %</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, i) => {
                const size = pos.quantity * (pos.current_price || pos.entry_price);
                const pnlPct = pos.entry_price > 0
                  ? ((pos.current_price - pos.entry_price) / pos.entry_price * 100) * (pos.side === 'BUY' ? 1 : -1)
                  : 0;
                const pnlUsd = pos.side === 'BUY'
                  ? (pos.current_price - pos.entry_price) * pos.quantity
                  : (pos.entry_price - pos.current_price) * pos.quantity;
                return (
                  <tr key={i} className="border-b border-hive-border/50 hover:bg-hive-border/20">
                    <td className="px-5 py-3 font-medium">{pos.symbol.replace('USDT', '')}</td>
                    <td className="px-5 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded ${pos.side === 'BUY' ? 'bg-hive-green/20 text-hive-green' : 'bg-hive-red/20 text-hive-red'}`}>
                        {pos.side}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">${size.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td className="px-5 py-3 text-right">${pos.entry_price.toLocaleString()}</td>
                    <td className="px-5 py-3 text-right">${pos.current_price.toLocaleString()}</td>
                    <td className={`px-5 py-3 text-right font-medium ${pnlUsd >= 0 ? 'text-hive-green' : 'text-hive-red'}`}>
                      {pnlUsd >= 0 ? '+' : ''}${pnlUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </td>
                    <td className={`px-5 py-3 text-right ${pnlPct >= 0 ? 'text-hive-green' : 'text-hive-red'}`}>
                      {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Closed Trades */}
      <div className="bg-hive-card border border-hive-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-hive-border flex items-center justify-between">
          <h2 className="text-lg font-semibold">Closed Trades</h2>
          {closedTrades.length > 0 && (
            <span className="text-sm text-hive-muted">{closedTrades.length} trades</span>
          )}
        </div>
        {closedTrades.length === 0 ? (
          <div className="px-5 py-8 text-center text-hive-muted">
            No closed trades yet. Positions close when stop-loss, take-profit, or time-stop triggers.
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-sm text-hive-muted border-b border-hive-border">
                <th className="text-left px-5 py-3">Symbol</th>
                <th className="text-left px-5 py-3">Side</th>
                <th className="text-right px-5 py-3">Entry</th>
                <th className="text-right px-5 py-3">Exit</th>
                <th className="text-right px-5 py-3">P&L</th>
                <th className="text-right px-5 py-3">P&L %</th>
                <th className="text-left px-5 py-3">Reason</th>
                <th className="text-right px-5 py-3">Duration</th>
              </tr>
            </thead>
            <tbody>
              {closedTrades.slice(0, 20).map((trade: any, i: number) => {
                const pnl = trade.pnl_usd ?? 0;
                const pnlPct = trade.pnl_pct ?? 0;
                return (
                  <tr key={i} className="border-b border-hive-border/50 hover:bg-hive-border/20">
                    <td className="px-5 py-3 font-medium">{(trade.symbol || '').replace('USDT', '')}</td>
                    <td className="px-5 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded ${trade.side === 'BUY' ? 'bg-hive-green/20 text-hive-green' : 'bg-hive-red/20 text-hive-red'}`}>
                        {trade.side}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">${(trade.entry_price ?? 0).toLocaleString()}</td>
                    <td className="px-5 py-3 text-right">${(trade.exit_price ?? 0).toLocaleString()}</td>
                    <td className={`px-5 py-3 text-right font-medium ${pnl >= 0 ? 'text-hive-green' : 'text-hive-red'}`}>
                      {pnl >= 0 ? '+' : ''}${pnl.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </td>
                    <td className={`px-5 py-3 text-right ${pnlPct >= 0 ? 'text-hive-green' : 'text-hive-red'}`}>
                      {pnlPct >= 0 ? '+' : ''}{(pnlPct * 100).toFixed(1)}%
                    </td>
                    <td className="px-5 py-3 text-sm text-hive-muted">{trade.exit_reason ?? ''}</td>
                    <td className="px-5 py-3 text-right text-hive-muted text-sm">
                      {trade.holding_hours ? `${Math.round(trade.holding_hours)}h` : '\u2014'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Recent Cycles */}
      <div className="bg-hive-card border border-hive-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-hive-border flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Cycles</h2>
          <a href="/cycles" className="text-xs text-hive-accent hover:underline">View all</a>
        </div>
        {cycles.length === 0 ? (
          <div className="px-5 py-8 text-center text-hive-muted">
            No cycles recorded yet. The pipeline runs every 4 hours.
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-sm text-hive-muted border-b border-hive-border">
                <th className="text-left px-5 py-3">#</th>
                <th className="text-left px-5 py-3">Time</th>
                <th className="text-left px-5 py-3">Regime</th>
                <th className="text-right px-5 py-3">Coins</th>
                <th className="text-right px-5 py-3">Signals</th>
                <th className="text-right px-5 py-3">Orders</th>
                <th className="text-right px-5 py-3">Duration</th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((cycle) => (
                <tr key={cycle.id} className="border-b border-hive-border/50 hover:bg-hive-border/20">
                  <td className="px-5 py-3 text-hive-muted">{cycle.id}</td>
                  <td className="px-5 py-3 text-sm">{new Date(cycle.started_at).toLocaleString()}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      cycle.regime === 'bull' ? 'bg-hive-green/20 text-hive-green' :
                      cycle.regime === 'bear' ? 'bg-hive-red/20 text-hive-red' :
                      cycle.regime === 'crisis' ? 'bg-red-900/30 text-red-400' :
                      'bg-hive-border text-hive-muted'
                    }`}>
                      {(cycle.regime ?? 'N/A').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">{cycle.coins_analyzed}</td>
                  <td className="px-5 py-3 text-right">{cycle.signals_produced}</td>
                  <td className="px-5 py-3 text-right">{cycle.orders_executed}</td>
                  <td className="px-5 py-3 text-right text-hive-muted">
                    {cycle.duration_secs ? `${cycle.duration_secs.toFixed(0)}s` : '\u2014'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
