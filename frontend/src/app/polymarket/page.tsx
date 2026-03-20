'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  Cloud, Sun, Thermometer, TrendingUp, TrendingDown,
  Activity, DollarSign, Target, BarChart3, Clock,
  RefreshCw, AlertTriangle, CheckCircle, XCircle,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';

// Lazy-load Recharts (no SSR)
const BarChart = dynamic(() => import('recharts').then(m => m.BarChart), { ssr: false });
const Bar = dynamic(() => import('recharts').then(m => m.Bar), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(m => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(m => m.YAxis), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(m => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import('recharts').then(m => m.ResponsiveContainer), { ssr: false });
const Cell = dynamic(() => import('recharts').then(m => m.Cell), { ssr: false });

/* ── Types ── */

interface OracleStatus {
  running: boolean;
  last_scan: string | null;
  markets_tracked: number;
  open_positions: number;
  portfolio_value: number;
  total_pnl: number;
  uptime_seconds: number;
}

interface Portfolio {
  bankroll: number;
  cash: number;
  positions: Position[];
  total_pnl: number;
  total_bets: number;
  wins: number;
  losses: number;
}

interface Position {
  city: string;
  date: string;
  bin_label: string;
  entry_price: number;
  quantity: number;
  model_prob: number;
  edge: number;
  condition_id: string;
  placed_at: string;
}

interface MarketInfo {
  city: string;
  date: string;
  condition_id: string;
  bins: { label: string; price: number }[];
  total_volume: number;
  edges_count?: number;
}

interface TradeRecord {
  city: string;
  date: string;
  bin_label: string;
  entry_price: number;
  outcome: boolean | null;
  pnl: number;
  resolved_at: string | null;
  actual_high: number | null;
  placed_at: string;
}

interface TradesData {
  open: TradeRecord[];
  resolved: TradeRecord[];
  stats: {
    total: number;
    wins: number;
    losses: number;
    pending: number;
    total_pnl: number;
  };
}

interface EdgeOpportunity {
  city: string;
  date: string;
  bin_label: string;
  model_prob: number;
  market_price: number;
  edge: number;
  suggested_size: number;
  condition_id: string;
}

/* ── Helpers ── */

function fmtUsd(n: number): string {
  if (Math.abs(n) >= 1000) return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function fmtPct(n: number): string {
  return `${n >= 0 ? '+' : ''}${(n * 100).toFixed(1)}%`;
}

function fmtEdge(n: number): string {
  return `${n >= 0 ? '+' : ''}${(n * 100).toFixed(1)}%`;
}

function timeAgo(iso: string | null): string {
  if (!iso) return '--';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 0) return 'just now';
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function daysUntil(dateStr: string): string {
  const target = new Date(dateStr + 'T00:00:00Z');
  const now = new Date();
  const diff = (target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  if (diff < 0) return 'Resolved';
  if (diff < 1) return 'Today';
  if (diff < 2) return 'Tomorrow';
  return `${Math.ceil(diff)}d`;
}

function formatUptime(seconds: number): string {
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

function cityWeatherIcon(city: string) {
  // Simple heuristic for weather icon based on city
  const hot = ['miami', 'phoenix', 'las vegas', 'dubai', 'rio'];
  const cold = ['anchorage', 'minneapolis', 'helsinki', 'moscow'];
  const lower = city.toLowerCase();
  if (hot.some(c => lower.includes(c))) return <Sun size={16} className="text-amber-400" />;
  if (cold.some(c => lower.includes(c))) return <Cloud size={16} className="text-blue-300" />;
  return <Thermometer size={16} className="text-syn-text-secondary" />;
}

/* ── Page Component ── */

export default function PolymarketPage() {
  const [status, setStatus] = useState<OracleStatus | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [markets, setMarkets] = useState<MarketInfo[]>([]);
  const [trades, setTrades] = useState<TradesData | null>(null);
  const [opportunities, setOpportunities] = useState<EdgeOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      const [statusRes, portfolioRes, marketsRes, tradesRes, oppsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/polymarket/status`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/portfolio`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/markets`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/trades`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/opportunities`).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);

      if (statusRes) setStatus(statusRes);
      if (portfolioRes) setPortfolio(portfolioRes);
      if (marketsRes) setMarkets(Array.isArray(marketsRes) ? marketsRes : []);
      if (tradesRes) setTrades(tradesRes);
      if (oppsRes) setOpportunities(Array.isArray(oppsRes) ? oppsRes : []);

      setError(null);
    } catch (err) {
      setError('Failed to connect to Weather Oracle API');
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const winRate = portfolio
    ? portfolio.total_bets > 0
      ? ((portfolio.wins / portfolio.total_bets) * 100).toFixed(1)
      : '0.0'
    : '--';

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCw size={32} className="text-syn-accent animate-spin" />
        <p className="text-syn-text-secondary text-sm">Loading Weather Oracle...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Cloud size={28} className="text-syn-accent" />
          <div>
            <h1 className="text-2xl font-bold text-white">Weather Oracle</h1>
            <p className="text-sm text-syn-text-secondary">
              Polymarket weather prediction markets
            </p>
          </div>
          <div className="flex items-center gap-2 ml-4">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                status?.running ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
              }`}
            />
            <span className="text-xs text-syn-text-secondary">
              {status?.running ? 'Running' : 'Offline'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-syn-text-tertiary">
          {status?.uptime_seconds != null && (
            <span>Uptime: {formatUptime(status.uptime_seconds)}</span>
          )}
          <span>Last scan: {timeAgo(status?.last_scan ?? null)}</span>
          <span>Refreshed: {lastRefresh.toLocaleTimeString()}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex items-center gap-2 text-red-300 text-sm">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* ── Stats Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Portfolio Value */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <div className="flex items-center gap-2 text-syn-text-secondary text-xs mb-2">
            <DollarSign size={14} />
            Portfolio Value
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {status ? fmtUsd(status.portfolio_value) : '--'}
          </div>
          <div className="text-xs text-syn-text-tertiary mt-1">
            {portfolio ? `${fmtUsd(portfolio.cash)} cash` : ''}
          </div>
        </div>

        {/* Total P&L */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <div className="flex items-center gap-2 text-syn-text-secondary text-xs mb-2">
            <TrendingUp size={14} />
            Total P&L
          </div>
          <div className={`text-2xl font-bold font-mono ${
            (status?.total_pnl ?? 0) >= 0 ? 'text-syn-accent' : 'text-red-400'
          }`}>
            {status ? `${(status.total_pnl ?? 0) >= 0 ? '+' : ''}${fmtUsd(status.total_pnl)}` : '--'}
          </div>
          <div className="text-xs text-syn-text-tertiary mt-1">
            {portfolio ? `${portfolio.total_bets} total bets` : ''}
          </div>
        </div>

        {/* Win Rate */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <div className="flex items-center gap-2 text-syn-text-secondary text-xs mb-2">
            <Target size={14} />
            Win Rate
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {winRate}%
          </div>
          <div className="text-xs text-syn-text-tertiary mt-1">
            {portfolio ? `${portfolio.wins}W / ${portfolio.losses}L` : ''}
          </div>
        </div>

        {/* Active Markets */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <div className="flex items-center gap-2 text-syn-text-secondary text-xs mb-2">
            <BarChart3 size={14} />
            Active Markets
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {status?.markets_tracked ?? '--'}
          </div>
          <div className="text-xs text-syn-text-tertiary mt-1">
            {status ? `${status.open_positions} open positions` : ''}
          </div>
        </div>
      </div>

      {/* ── Open Positions ── */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity size={18} className="text-syn-accent" />
          Open Positions
        </h2>
        <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
          {portfolio && portfolio.positions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-syn-border text-syn-text-secondary text-xs">
                    <th className="text-left px-4 py-3 font-medium">City</th>
                    <th className="text-left px-4 py-3 font-medium">Date</th>
                    <th className="text-left px-4 py-3 font-medium">Bin</th>
                    <th className="text-right px-4 py-3 font-medium">Entry</th>
                    <th className="text-right px-4 py-3 font-medium">Amount</th>
                    <th className="text-right px-4 py-3 font-medium">Model Prob</th>
                    <th className="text-right px-4 py-3 font-medium">Edge</th>
                    <th className="text-center px-4 py-3 font-medium">Resolves</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.positions.map((pos, i) => (
                    <tr
                      key={`${pos.condition_id}-${i}`}
                      className="border-b border-syn-border/50 hover:bg-syn-bg/30 transition-colors"
                    >
                      <td className="px-4 py-3 flex items-center gap-2">
                        {cityWeatherIcon(pos.city)}
                        <span className="text-white font-medium">{pos.city}</span>
                      </td>
                      <td className="px-4 py-3 text-syn-text-secondary">{pos.date}</td>
                      <td className="px-4 py-3">
                        <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">
                          {pos.bin_label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">
                        {pos.entry_price.toFixed(2)}c
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-white">
                        {fmtUsd(pos.quantity)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">
                        {(pos.model_prob * 100).toFixed(1)}%
                      </td>
                      <td className={`px-4 py-3 text-right font-mono ${
                        pos.edge >= 0 ? 'text-syn-accent' : 'text-red-400'
                      }`}>
                        {fmtEdge(pos.edge)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-syn-text-tertiary bg-syn-bg px-2 py-0.5 rounded">
                          {daysUntil(pos.date)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-syn-text-tertiary text-sm">
              No open positions
            </div>
          )}
        </div>
      </section>

      {/* ── Recent Trades ── */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Clock size={18} className="text-syn-accent" />
          Recent Trades
        </h2>
        <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
          {trades && trades.resolved.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-syn-border text-syn-text-secondary text-xs">
                    <th className="text-left px-4 py-3 font-medium">City</th>
                    <th className="text-left px-4 py-3 font-medium">Date</th>
                    <th className="text-left px-4 py-3 font-medium">Bin</th>
                    <th className="text-right px-4 py-3 font-medium">Entry</th>
                    <th className="text-center px-4 py-3 font-medium">Result</th>
                    <th className="text-right px-4 py-3 font-medium">P&L</th>
                    <th className="text-right px-4 py-3 font-medium">Actual High</th>
                    <th className="text-right px-4 py-3 font-medium">Resolved</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.resolved.slice(0, 20).map((trade, i) => (
                    <tr
                      key={`trade-${i}`}
                      className={`border-b border-syn-border/50 transition-colors ${
                        trade.outcome === true
                          ? 'bg-emerald-500/5 hover:bg-emerald-500/10'
                          : trade.outcome === false
                          ? 'bg-red-500/5 hover:bg-red-500/10'
                          : 'hover:bg-syn-bg/30'
                      }`}
                    >
                      <td className="px-4 py-3 flex items-center gap-2">
                        {cityWeatherIcon(trade.city)}
                        <span className="text-white font-medium">{trade.city}</span>
                      </td>
                      <td className="px-4 py-3 text-syn-text-secondary">{trade.date}</td>
                      <td className="px-4 py-3">
                        <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">
                          {trade.bin_label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">
                        {trade.entry_price.toFixed(2)}c
                      </td>
                      <td className="px-4 py-3 text-center">
                        {trade.outcome === true ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-syn-accent">
                            <CheckCircle size={14} /> Won
                          </span>
                        ) : trade.outcome === false ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-red-400">
                            <XCircle size={14} /> Lost
                          </span>
                        ) : (
                          <span className="text-xs text-syn-text-tertiary">Pending</span>
                        )}
                      </td>
                      <td className={`px-4 py-3 text-right font-mono ${
                        (trade.pnl ?? 0) >= 0 ? 'text-syn-accent' : 'text-red-400'
                      }`}>
                        {trade.pnl != null ? `${trade.pnl >= 0 ? '+' : ''}${fmtUsd(trade.pnl)}` : '--'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">
                        {trade.actual_high != null ? `${trade.actual_high.toFixed(0)}F` : '--'}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-syn-text-tertiary">
                        {timeAgo(trade.resolved_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-syn-text-tertiary text-sm">
              No resolved trades yet
            </div>
          )}
        </div>
      </section>

      {/* ── Edge Opportunities + Market Overview (side by side on desktop) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Edge Opportunities */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-syn-accent" />
            Edge Opportunities
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
            {opportunities.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-syn-border text-syn-text-secondary text-xs">
                      <th className="text-left px-4 py-3 font-medium">City</th>
                      <th className="text-left px-4 py-3 font-medium">Date</th>
                      <th className="text-left px-4 py-3 font-medium">Bin</th>
                      <th className="text-right px-4 py-3 font-medium">Model</th>
                      <th className="text-right px-4 py-3 font-medium">Market</th>
                      <th className="text-right px-4 py-3 font-medium">Edge</th>
                      <th className="text-right px-4 py-3 font-medium">Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunities.map((opp, i) => (
                      <tr
                        key={`opp-${i}`}
                        className="border-b border-syn-border/50 hover:bg-syn-bg/30 transition-colors"
                      >
                        <td className="px-4 py-3 flex items-center gap-2">
                          {cityWeatherIcon(opp.city)}
                          <span className="text-white text-xs font-medium">{opp.city}</span>
                        </td>
                        <td className="px-4 py-3 text-syn-text-secondary text-xs">{opp.date}</td>
                        <td className="px-4 py-3">
                          <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">
                            {opp.bin_label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-syn-text-secondary">
                          {(opp.model_prob * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-syn-text-secondary">
                          {(opp.market_price * 100).toFixed(1)}c
                        </td>
                        <td className={`px-4 py-3 text-right font-mono text-xs font-medium ${
                          opp.edge >= 0 ? 'text-syn-accent' : 'text-red-400'
                        }`}>
                          {fmtEdge(opp.edge)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-white">
                          {fmtUsd(opp.suggested_size)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-6 py-12 text-center text-syn-text-tertiary text-sm">
                No edge opportunities above threshold
              </div>
            )}
          </div>
        </section>

        {/* Market Overview */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Cloud size={18} className="text-syn-accent" />
            Tracked Markets
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
            {markets.length > 0 ? (
              <div className="divide-y divide-syn-border/50">
                {markets.map((market, i) => (
                  <div
                    key={`market-${i}`}
                    className="px-4 py-3 flex items-center justify-between hover:bg-syn-bg/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {cityWeatherIcon(market.city)}
                      <div>
                        <span className="text-white text-sm font-medium">{market.city}</span>
                        <span className="text-syn-text-tertiary text-xs ml-2">{market.date}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-syn-text-secondary">
                        {market.bins?.length ?? 0} bins
                      </span>
                      {market.edges_count != null && market.edges_count > 0 && (
                        <span className="text-syn-accent font-medium">
                          {market.edges_count} edge{market.edges_count !== 1 ? 's' : ''}
                        </span>
                      )}
                      {market.total_volume != null && market.total_volume > 0 && (
                        <span className="text-syn-text-tertiary font-mono">
                          Vol: {fmtUsd(market.total_volume)}
                        </span>
                      )}
                      <span className="text-syn-text-tertiary bg-syn-bg px-2 py-0.5 rounded">
                        {daysUntil(market.date)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="px-6 py-12 text-center text-syn-text-tertiary text-sm">
                No markets currently tracked
              </div>
            )}
          </div>
        </section>
      </div>

      {/* ── P&L Distribution (if we have resolved trades) ── */}
      {trades && trades.resolved.length > 3 && (
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 size={18} className="text-syn-accent" />
            Trade P&L Distribution
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl p-6">
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trades.resolved.slice(0, 30).map((t, i) => ({
                  name: `${t.city.slice(0, 3)} ${t.date.slice(5)}`,
                  pnl: t.pnl ?? 0,
                }))}>
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#6b7280', fontSize: 10 }}
                    axisLine={{ stroke: '#374151' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#6b7280', fontSize: 10 }}
                    axisLine={{ stroke: '#374151' }}
                    tickLine={false}
                    tickFormatter={(v: number) => `$${v}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1a2e',
                      border: '1px solid #2d2d44',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                    formatter={(value) => [`$${Number(value ?? 0).toFixed(2)}`, 'P&L']}
                  />
                  <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                    {trades.resolved.slice(0, 30).map((t, i) => (
                      <Cell
                        key={`cell-${i}`}
                        fill={(t.pnl ?? 0) >= 0 ? '#34d399' : '#f87171'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
