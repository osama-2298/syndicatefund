'use client';

import { useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  Cloud, Sun, Thermometer, TrendingUp,
  Activity, DollarSign, Target, BarChart3, Clock,
  RefreshCw, AlertTriangle, CheckCircle, XCircle,
  ShieldAlert, ShieldCheck, Wallet, ListOrdered,
  Zap, Ban, Play,
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
  total_value?: number;
  win_rate?: number;
}

interface Position {
  city: string;
  date: string;
  bin_label: string;
  entry_price: number;
  fill_price: number;
  quantity: number;
  model_prob: number;
  edge: number;
  edge_at_entry: number;
  forecast_mean: number;
  forecast_std: number;
  condition_id: string;
  placed_at: string;
  resolved: boolean;
  outcome: boolean | null;
  pnl: number;
}

interface LiveOrder {
  order_id: string;
  condition_id: string;
  city: string;
  date: string;
  bin_label: string;
  price: number;
  size: number;
  quantity_usd: number;
  model_prob: number;
  edge: number;
  status: string;
  fill_price: number;
  filled_size: number;
  created_at: string;
  updated_at: string;
  cancelled_at: string | null;
  error: string;
}

interface OpenOrdersData {
  orders: LiveOrder[];
  count: number;
  committed_capital: number;
  mode: string;
}

interface OrderHistoryData {
  orders: LiveOrder[];
  count: number;
  mode: string;
}

interface TradesData {
  open: Position[];
  resolved: Position[];
  stats: {
    total_bets: number;
    wins: number;
    losses: number;
    win_rate: number;
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
  quantity: number;
}

/* ── Helpers ── */

function fmtUsd(n: number | undefined | null): string {
  const v = n ?? 0;
  if (Math.abs(v) >= 1000) return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function fmtEdge(n: number | undefined | null): string {
  const v = n ?? 0;
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`;
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
  const hot = ['miami', 'phoenix', 'las vegas', 'dubai', 'rio'];
  const cold = ['anchorage', 'minneapolis', 'helsinki', 'moscow'];
  const lower = city.toLowerCase();
  if (hot.some(c => lower.includes(c))) return <Sun size={16} className="text-amber-400" />;
  if (cold.some(c => lower.includes(c))) return <Cloud size={16} className="text-blue-300" />;
  return <Thermometer size={16} className="text-syn-text-secondary" />;
}

function orderStatusBadge(status: string) {
  const s = status.toLowerCase();
  if (s === 'filled') return <span className="text-xs font-medium text-syn-accent bg-syn-accent/10 px-2 py-0.5 rounded">Filled</span>;
  if (s === 'pending') return <span className="text-xs font-medium text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded animate-pulse">Pending</span>;
  if (s === 'cancelled') return <span className="text-xs font-medium text-syn-text-tertiary bg-syn-bg px-2 py-0.5 rounded">Cancelled</span>;
  if (s === 'failed' || s === 'rejected') return <span className="text-xs font-medium text-red-400 bg-red-400/10 px-2 py-0.5 rounded">Failed</span>;
  if (s === 'partial') return <span className="text-xs font-medium text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded">Partial</span>;
  return <span className="text-xs text-syn-text-tertiary">{status}</span>;
}

/* ── Page Component ── */

export default function PolymarketPage() {
  const [status, setStatus] = useState<OracleStatus | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<TradesData | null>(null);
  const [opportunities, setOpportunities] = useState<EdgeOpportunity[]>([]);
  const [openOrders, setOpenOrders] = useState<OpenOrdersData | null>(null);
  const [orderHistory, setOrderHistory] = useState<OrderHistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [killSwitchLoading, setKillSwitchLoading] = useState(false);

  const isLive = openOrders?.mode === 'live';

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, portfolioRes, tradesRes, oppsRes, ordersRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/polymarket/status`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/portfolio`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/trades`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/opportunities`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/open-orders`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/order-history`).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);

      if (statusRes) setStatus(statusRes);
      if (portfolioRes) setPortfolio(portfolioRes);
      if (tradesRes) setTrades(tradesRes);
      if (oppsRes) setOpportunities(oppsRes?.opportunities ?? []);
      if (ordersRes) setOpenOrders(ordersRes);
      if (historyRes) setOrderHistory(historyRes);

      setError(null);
    } catch {
      setError('Failed to connect to Weather Oracle API');
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // refresh every 15s for live
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleKillSwitch = async () => {
    if (!confirm('EMERGENCY HALT: Cancel all open orders and stop trading?')) return;
    setKillSwitchLoading(true);
    try {
      const adminToken = prompt('Enter admin token:');
      if (!adminToken) return;
      const res = await fetch(`${API_BASE}/api/v1/polymarket/kill-switch`, {
        method: 'POST',
        headers: { Authorization: adminToken, 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      alert(`Kill switch activated: ${data.orders_cancelled} orders cancelled`);
      fetchData();
    } catch (e) {
      alert('Kill switch failed — check console');
    } finally {
      setKillSwitchLoading(false);
    }
  };

  const openPositions = portfolio?.positions?.filter(p => !p.resolved) ?? [];
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
          {/* Trading Mode Badge */}
          {isLive ? (
            <span className="ml-2 inline-flex items-center gap-1 text-xs font-bold text-amber-300 bg-amber-400/15 border border-amber-400/30 px-2.5 py-1 rounded-full">
              <Zap size={12} /> LIVE
            </span>
          ) : (
            <span className="ml-2 inline-flex items-center gap-1 text-xs font-medium text-syn-text-tertiary bg-syn-bg border border-syn-border px-2.5 py-1 rounded-full">
              Paper
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {isLive && (
            <button
              onClick={handleKillSwitch}
              disabled={killSwitchLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50"
            >
              <Ban size={14} />
              {killSwitchLoading ? 'Halting...' : 'Kill Switch'}
            </button>
          )}
          <div className="text-xs text-syn-text-tertiary">
            {status?.uptime_seconds != null && (
              <span className="mr-3">Uptime: {formatUptime(status.uptime_seconds)}</span>
            )}
            <span>Last scan: {timeAgo(status?.last_scan ?? null)}</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex items-center gap-2 text-red-300 text-sm">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* ── Stats Cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Wallet Balance */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-syn-text-secondary text-xs mb-1.5">
            <Wallet size={13} />
            Wallet
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {fmtUsd(portfolio?.bankroll ?? 0)}
          </div>
        </div>

        {/* Available */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-syn-text-secondary text-xs mb-1.5">
            <DollarSign size={13} />
            Available
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {fmtUsd(portfolio?.cash ?? 0)}
          </div>
        </div>

        {/* Committed */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-syn-text-secondary text-xs mb-1.5">
            <ListOrdered size={13} />
            Committed
          </div>
          <div className="text-xl font-bold text-amber-400 font-mono">
            {fmtUsd(openOrders?.committed_capital ?? 0)}
          </div>
        </div>

        {/* Total P&L */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-syn-text-secondary text-xs mb-1.5">
            <TrendingUp size={13} />
            P&L
          </div>
          <div className={`text-xl font-bold font-mono ${
            (portfolio?.total_pnl ?? 0) >= 0 ? 'text-syn-accent' : 'text-red-400'
          }`}>
            {portfolio ? `${(portfolio.total_pnl ?? 0) >= 0 ? '+' : ''}${fmtUsd(portfolio.total_pnl)}` : '--'}
          </div>
        </div>

        {/* Win Rate */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-syn-text-secondary text-xs mb-1.5">
            <Target size={13} />
            Win Rate
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {winRate}%
          </div>
          <div className="text-xs text-syn-text-tertiary">
            {portfolio ? `${portfolio.wins}W / ${portfolio.losses}L` : ''}
          </div>
        </div>

        {/* Markets */}
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-syn-text-secondary text-xs mb-1.5">
            <BarChart3 size={13} />
            Markets
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {status?.markets_tracked ?? '--'}
          </div>
          <div className="text-xs text-syn-text-tertiary">
            {status ? `${status.open_positions} positions` : ''}
          </div>
        </div>
      </div>

      {/* ── Open Orders (Live Trading) ── */}
      {isLive && (
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <ListOrdered size={18} className="text-amber-400" />
            Open Orders
            {openOrders && openOrders.count > 0 && (
              <span className="text-xs font-normal text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full ml-2">
                {openOrders.count} pending
              </span>
            )}
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
            {openOrders && openOrders.orders.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-syn-border text-syn-text-secondary text-xs">
                      <th className="text-left px-4 py-3 font-medium">City</th>
                      <th className="text-left px-4 py-3 font-medium">Date</th>
                      <th className="text-left px-4 py-3 font-medium">Bin</th>
                      <th className="text-right px-4 py-3 font-medium">Price</th>
                      <th className="text-right px-4 py-3 font-medium">Size</th>
                      <th className="text-right px-4 py-3 font-medium">Amount</th>
                      <th className="text-right px-4 py-3 font-medium">Edge</th>
                      <th className="text-center px-4 py-3 font-medium">Status</th>
                      <th className="text-right px-4 py-3 font-medium">Age</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openOrders.orders.map((order, i) => (
                      <tr key={order.order_id} className="border-b border-syn-border/50 hover:bg-syn-bg/30 transition-colors">
                        <td className="px-4 py-3 flex items-center gap-2">
                          {cityWeatherIcon(order.city)}
                          <span className="text-white font-medium">{order.city}</span>
                        </td>
                        <td className="px-4 py-3 text-syn-text-secondary">{order.date}</td>
                        <td className="px-4 py-3">
                          <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{order.bin_label}</span>
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">{(order.price * 100).toFixed(1)}c</td>
                        <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">{order.size}</td>
                        <td className="px-4 py-3 text-right font-mono text-white">{fmtUsd(order.quantity_usd)}</td>
                        <td className={`px-4 py-3 text-right font-mono ${order.edge >= 0 ? 'text-syn-accent' : 'text-red-400'}`}>
                          {fmtEdge(order.edge)}
                        </td>
                        <td className="px-4 py-3 text-center">{orderStatusBadge(order.status)}</td>
                        <td className="px-4 py-3 text-right text-xs text-syn-text-tertiary">{timeAgo(order.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-6 py-8 text-center text-syn-text-tertiary text-sm">
                No open orders — waiting for weather markets with edge
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Open Positions ── */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity size={18} className="text-syn-accent" />
          Open Positions
          {openPositions.length > 0 && (
            <span className="text-xs font-normal text-syn-accent bg-syn-accent/10 px-2 py-0.5 rounded-full ml-2">
              {openPositions.length}
            </span>
          )}
        </h2>
        <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
          {openPositions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-syn-border text-syn-text-secondary text-xs">
                    <th className="text-left px-4 py-3 font-medium">City</th>
                    <th className="text-left px-4 py-3 font-medium">Date</th>
                    <th className="text-left px-4 py-3 font-medium">Bin</th>
                    <th className="text-right px-4 py-3 font-medium">Entry</th>
                    <th className="text-right px-4 py-3 font-medium">Fill</th>
                    <th className="text-right px-4 py-3 font-medium">Amount</th>
                    <th className="text-right px-4 py-3 font-medium">Model</th>
                    <th className="text-right px-4 py-3 font-medium">Edge</th>
                    <th className="text-center px-4 py-3 font-medium">Resolves</th>
                  </tr>
                </thead>
                <tbody>
                  {openPositions.map((pos, i) => (
                    <tr key={`${pos.condition_id}-${i}`} className="border-b border-syn-border/50 hover:bg-syn-bg/30 transition-colors">
                      <td className="px-4 py-3 flex items-center gap-2">
                        {cityWeatherIcon(pos.city)}
                        <span className="text-white font-medium">{pos.city}</span>
                      </td>
                      <td className="px-4 py-3 text-syn-text-secondary">{pos.date}</td>
                      <td className="px-4 py-3">
                        <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{pos.bin_label}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">{(pos.entry_price * 100).toFixed(1)}c</td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">
                        {pos.fill_price > 0 ? `${(pos.fill_price * 100).toFixed(1)}c` : '--'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-white">{fmtUsd(pos.quantity)}</td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">{(pos.model_prob * 100).toFixed(1)}%</td>
                      <td className={`px-4 py-3 text-right font-mono ${
                        (pos.edge_at_entry ?? pos.edge ?? 0) >= 0 ? 'text-syn-accent' : 'text-red-400'
                      }`}>
                        {fmtEdge(pos.edge_at_entry ?? pos.edge ?? 0)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-syn-text-tertiary bg-syn-bg px-2 py-0.5 rounded">{daysUntil(pos.date)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-8 text-center text-syn-text-tertiary text-sm">
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
                    <th className="text-right px-4 py-3 font-medium">Amount</th>
                    <th className="text-center px-4 py-3 font-medium">Result</th>
                    <th className="text-right px-4 py-3 font-medium">P&L</th>
                    <th className="text-right px-4 py-3 font-medium">Placed</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.resolved.slice(0, 20).map((trade, i) => (
                    <tr
                      key={`trade-${i}`}
                      className={`border-b border-syn-border/50 transition-colors ${
                        trade.outcome === true ? 'bg-emerald-500/5 hover:bg-emerald-500/10' :
                        trade.outcome === false ? 'bg-red-500/5 hover:bg-red-500/10' : 'hover:bg-syn-bg/30'
                      }`}
                    >
                      <td className="px-4 py-3 flex items-center gap-2">
                        {cityWeatherIcon(trade.city)}
                        <span className="text-white font-medium">{trade.city}</span>
                      </td>
                      <td className="px-4 py-3 text-syn-text-secondary">{trade.date}</td>
                      <td className="px-4 py-3">
                        <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{trade.bin_label}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-syn-text-secondary">{(trade.entry_price * 100).toFixed(1)}c</td>
                      <td className="px-4 py-3 text-right font-mono text-white">{fmtUsd(trade.quantity)}</td>
                      <td className="px-4 py-3 text-center">
                        {trade.outcome === true ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-syn-accent"><CheckCircle size={14} /> Won</span>
                        ) : trade.outcome === false ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-red-400"><XCircle size={14} /> Lost</span>
                        ) : (
                          <span className="text-xs text-syn-text-tertiary">Pending</span>
                        )}
                      </td>
                      <td className={`px-4 py-3 text-right font-mono ${(trade.pnl ?? 0) >= 0 ? 'text-syn-accent' : 'text-red-400'}`}>
                        {trade.pnl != null ? `${trade.pnl >= 0 ? '+' : ''}${fmtUsd(trade.pnl)}` : '--'}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-syn-text-tertiary">{timeAgo(trade.placed_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-8 text-center text-syn-text-tertiary text-sm">
              No resolved trades yet
            </div>
          )}
        </div>
      </section>

      {/* ── Order History (Live Trading) ── */}
      {isLive && orderHistory && orderHistory.orders.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Clock size={18} className="text-syn-text-secondary" />
            Order History
            <span className="text-xs font-normal text-syn-text-tertiary ml-2">{orderHistory.count} total</span>
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-syn-border text-syn-text-secondary text-xs">
                    <th className="text-left px-4 py-3 font-medium">City</th>
                    <th className="text-left px-4 py-3 font-medium">Bin</th>
                    <th className="text-right px-4 py-3 font-medium">Price</th>
                    <th className="text-right px-4 py-3 font-medium">Fill</th>
                    <th className="text-right px-4 py-3 font-medium">Amount</th>
                    <th className="text-center px-4 py-3 font-medium">Status</th>
                    <th className="text-right px-4 py-3 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {orderHistory.orders.slice(0, 30).map((order, i) => (
                    <tr key={`hist-${i}`} className="border-b border-syn-border/50 hover:bg-syn-bg/30 transition-colors">
                      <td className="px-4 py-3 flex items-center gap-2">
                        {cityWeatherIcon(order.city)}
                        <span className="text-white text-xs">{order.city}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{order.bin_label}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-syn-text-secondary">{(order.price * 100).toFixed(1)}c</td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-syn-text-secondary">
                        {order.fill_price > 0 ? `${(order.fill_price * 100).toFixed(1)}c` : '--'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-white">{fmtUsd(order.quantity_usd)}</td>
                      <td className="px-4 py-3 text-center">{orderStatusBadge(order.status)}</td>
                      <td className="px-4 py-3 text-right text-xs text-syn-text-tertiary">{timeAgo(order.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* ── Edge Opportunities ── */}
      {opportunities.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-syn-accent" />
            Edge Opportunities
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
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
                    <tr key={`opp-${i}`} className="border-b border-syn-border/50 hover:bg-syn-bg/30 transition-colors">
                      <td className="px-4 py-3 flex items-center gap-2">
                        {cityWeatherIcon(opp.city)}
                        <span className="text-white text-xs font-medium">{opp.city}</span>
                      </td>
                      <td className="px-4 py-3 text-syn-text-secondary text-xs">{opp.date}</td>
                      <td className="px-4 py-3">
                        <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{opp.bin_label}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-syn-text-secondary">{(opp.model_prob * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-syn-text-secondary">{(opp.market_price * 100).toFixed(1)}c</td>
                      <td className={`px-4 py-3 text-right font-mono text-xs font-medium ${opp.edge >= 0 ? 'text-syn-accent' : 'text-red-400'}`}>
                        {fmtEdge(opp.edge)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-white">{fmtUsd(opp.quantity)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* ── P&L Distribution ── */}
      {trades && trades.resolved.length > 3 && (
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 size={18} className="text-syn-accent" />
            Trade P&L Distribution
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl p-6">
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trades.resolved.slice(0, 30).map((t) => ({
                  name: `${t.city.slice(0, 3)} ${t.date.slice(5)}`,
                  pnl: t.pnl ?? 0,
                }))}>
                  <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={{ stroke: '#374151' }} tickLine={false} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={{ stroke: '#374151' }} tickLine={false} tickFormatter={(v: number) => `$${v}`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #2d2d44', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(value) => [`$${Number(value ?? 0).toFixed(2)}`, 'P&L']}
                  />
                  <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                    {trades.resolved.slice(0, 30).map((t, i) => (
                      <Cell key={`cell-${i}`} fill={(t.pnl ?? 0) >= 0 ? '#34d399' : '#f87171'} />
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
