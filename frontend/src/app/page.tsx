import StatCard from '@/components/StatCard';
import { api, Portfolio, CycleSummary } from '@/lib/api';

export const dynamic = 'force-dynamic';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default async function Dashboard() {
  let portfolio: Portfolio | null = null;
  let cycles: CycleSummary[] = [];
  let currentCycle: any = null;
  let trades: any = null;

  try {
    [portfolio, cycles, currentCycle, trades] = await Promise.all([
      api.getPortfolio(),
      api.getCycles(5),
      api.getCurrentCycle(),
      fetch(`${API_BASE}/api/v1/portfolio/trades`, { next: { revalidate: 30 } }).then(r => r.json()).catch(() => null),
    ]);
  } catch (e) {}

  const positions = portfolio?.positions ?? [];
  const cash = portfolio?.cash ?? 100000;
  const invested = positions.reduce((sum, p) => sum + p.quantity * (p.current_price || p.entry_price), 0);
  const totalValue = cash + invested;
  const returnPct = ((totalValue - 100000) / 100000) * 100;
  const regime = currentCycle?.regime ?? 'N/A';
  const closedTrades = trades?.trades ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Dashboard</h1>
        <p className="text-hive-muted">Multi-agent crypto analysis platform</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Portfolio Value"
          value={`$${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          subtitle="Paper trading"
          trend={returnPct > 0 ? 'up' : returnPct < 0 ? 'down' : 'neutral'}
        />
        <StatCard
          title="Total Return"
          value={`${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%`}
          subtitle={`${returnPct >= 0 ? '+' : ''}$${(totalValue - 100000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          trend={returnPct > 0 ? 'up' : returnPct < 0 ? 'down' : 'neutral'}
        />
        <StatCard
          title="Invested"
          value={`$${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          subtitle={`$${cash.toLocaleString(undefined, { maximumFractionDigits: 0 })} cash`}
        />
        <StatCard
          title="Open Positions"
          value={`${positions.length}`}
          subtitle={positions.length > 0 ? positions.map(p => p.symbol.replace('USDT', '')).join(', ') : 'No positions'}
        />
        <StatCard
          title="Market Regime"
          value={regime.toUpperCase()}
          subtitle={currentCycle?.status === 'running' ? 'Cycle in progress' : 'Waiting for next cycle'}
          trend={regime === 'bull' ? 'up' : regime === 'bear' || regime === 'crisis' ? 'down' : 'neutral'}
        />
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
                      {trade.holding_hours ? `${Math.round(trade.holding_hours)}h` : '—'}
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
        <div className="px-5 py-4 border-b border-hive-border">
          <h2 className="text-lg font-semibold">Recent Cycles</h2>
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
