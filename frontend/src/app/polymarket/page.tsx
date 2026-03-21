'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Cloud, TrendingUp, Activity, DollarSign, Target, Clock,
  RefreshCw, AlertTriangle, CheckCircle, XCircle,
  Zap, Ban, Thermometer, Sun,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';

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
  condition_id: string;
  placed_at: string;
  resolved: boolean;
  outcome: boolean | null;
  pnl: number;
}

interface LiveOrder {
  order_id: string;
  city: string;
  date: string;
  bin_label: string;
  price: number;
  size: number;
  quantity_usd: number;
  edge: number;
  status: string;
  created_at: string;
}

interface OpenOrdersData {
  orders: LiveOrder[];
  count: number;
  committed_capital: number;
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

/* ── Helpers ── */

function fmtUsd(n: number | undefined | null): string {
  const v = n ?? 0;
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtPnl(n: number | undefined | null): string {
  const v = n ?? 0;
  return `${v >= 0 ? '+' : ''}$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'never';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function cityIcon(city: string) {
  const hot = ['miami', 'phoenix', 'las vegas', 'dubai', 'rio'];
  const lower = city.toLowerCase();
  if (hot.some(c => lower.includes(c))) return <Sun size={14} className="text-amber-400" />;
  return <Thermometer size={14} className="text-syn-text-secondary" />;
}

/* ── Page ── */

export default function PolymarketPage() {
  const [status, setStatus] = useState<OracleStatus | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<TradesData | null>(null);
  const [openOrders, setOpenOrders] = useState<OpenOrdersData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [killLoading, setKillLoading] = useState(false);

  const isLive = openOrders?.mode === 'live';

  const fetchData = useCallback(async () => {
    try {
      const [s, p, t, o] = await Promise.all([
        fetch(`${API_BASE}/api/v1/polymarket/status`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/portfolio`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/trades`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE}/api/v1/polymarket/open-orders`).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      if (s) setStatus(s);
      if (p) setPortfolio(p);
      if (t) setTrades(t);
      if (o) setOpenOrders(o);
      setError(null);
    } catch {
      setError('Cannot reach API');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 15000);
    return () => clearInterval(iv);
  }, [fetchData]);

  const handleKillSwitch = async () => {
    if (!confirm('Cancel all orders and stop trading?')) return;
    setKillLoading(true);
    try {
      const token = prompt('Admin token:');
      if (!token) return;
      await fetch(`${API_BASE}/api/v1/polymarket/kill-switch`, {
        method: 'POST',
        headers: { Authorization: token, 'Content-Type': 'application/json' },
      });
      fetchData();
    } finally {
      setKillLoading(false);
    }
  };

  // Combine all positions & trades into one timeline
  const openPositions = portfolio?.positions?.filter(p => !p.resolved) ?? [];
  const resolvedTrades = trades?.resolved ?? [];
  const pendingOrders = openOrders?.orders ?? [];
  const totalBets = portfolio?.total_bets ?? 0;
  const wins = portfolio?.wins ?? 0;
  const losses = portfolio?.losses ?? 0;
  const pnl = portfolio?.total_pnl ?? 0;
  const balance = portfolio?.bankroll ?? 0;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCw size={28} className="text-syn-accent animate-spin" />
        <p className="text-syn-text-secondary text-sm">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cloud size={24} className="text-syn-accent" />
          <h1 className="text-xl font-bold text-white">Weather Oracle</h1>
          {isLive ? (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-300 bg-amber-400/15 border border-amber-400/30 px-2 py-0.5 rounded-full">
              <Zap size={10} /> LIVE
            </span>
          ) : (
            <span className="text-xs text-syn-text-tertiary bg-syn-bg border border-syn-border px-2 py-0.5 rounded-full">Paper</span>
          )}
          <span className={`w-2 h-2 rounded-full ${status?.running ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
          <span className="text-xs text-syn-text-tertiary">
            {status?.running ? `Scanned ${timeAgo(status.last_scan)}` : 'Offline'}
          </span>
        </div>
        {isLive && (
          <button onClick={handleKillSwitch} disabled={killLoading}
            className="flex items-center gap-1 px-3 py-1.5 text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg hover:bg-red-500/20 disabled:opacity-50">
            <Ban size={12} /> {killLoading ? 'Stopping...' : 'Emergency Stop'}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 flex items-center gap-2 text-red-300 text-sm">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* ── Balance + Stats ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <p className="text-xs text-syn-text-tertiary mb-1">Balance</p>
          <p className="text-2xl font-bold text-white font-mono">{fmtUsd(balance)}</p>
        </div>
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <p className="text-xs text-syn-text-tertiary mb-1">P&L</p>
          <p className={`text-2xl font-bold font-mono ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {fmtPnl(pnl)}
          </p>
        </div>
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <p className="text-xs text-syn-text-tertiary mb-1">Win Rate</p>
          <p className="text-2xl font-bold text-white font-mono">
            {totalBets > 0 ? `${((wins / totalBets) * 100).toFixed(0)}%` : '--'}
          </p>
          <p className="text-xs text-syn-text-tertiary">{wins}W {losses}L</p>
        </div>
        <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
          <p className="text-xs text-syn-text-tertiary mb-1">Bets / Markets</p>
          <p className="text-2xl font-bold text-white font-mono">{totalBets}</p>
          <p className="text-xs text-syn-text-tertiary">{status?.markets_tracked ?? 0} markets tracked</p>
        </div>
      </div>

      {/* ── Pending Orders ── */}
      {pendingOrders.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Activity size={14} className="text-amber-400" />
            Pending Orders ({pendingOrders.length})
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl divide-y divide-syn-border/50">
            {pendingOrders.map((o) => (
              <div key={o.order_id} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {cityIcon(o.city)}
                  <span className="text-white text-sm font-medium">{o.city}</span>
                  <span className="text-xs text-syn-text-tertiary">{o.date}</span>
                  <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{o.bin_label}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="font-mono text-white">{fmtUsd(o.quantity_usd)}</span>
                  <span className="font-mono text-syn-text-secondary">{(o.price * 100).toFixed(0)}c</span>
                  <span className="text-amber-400 animate-pulse font-medium">Pending</span>
                  <span className="text-syn-text-tertiary">{timeAgo(o.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Open Positions ── */}
      {openPositions.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Target size={14} className="text-syn-accent" />
            Open Positions ({openPositions.length})
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl divide-y divide-syn-border/50">
            {openPositions.map((pos, i) => (
              <div key={`${pos.condition_id}-${i}`} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {cityIcon(pos.city)}
                  <span className="text-white text-sm font-medium">{pos.city}</span>
                  <span className="text-xs text-syn-text-tertiary">{pos.date}</span>
                  <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{pos.bin_label}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="font-mono text-white">{fmtUsd(pos.quantity)}</span>
                  <span className="font-mono text-syn-text-secondary">@ {(pos.entry_price * 100).toFixed(0)}c</span>
                  <span className="text-syn-accent font-mono">+{((pos.edge_at_entry ?? pos.edge) * 100).toFixed(1)}% edge</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Empty State ── */}
      {openPositions.length === 0 && pendingOrders.length === 0 && (
        <div className="bg-syn-surface border border-syn-border rounded-xl px-6 py-12 text-center">
          <Cloud size={32} className="text-syn-text-tertiary mx-auto mb-3" />
          <p className="text-syn-text-secondary text-sm">No active trades</p>
          <p className="text-syn-text-tertiary text-xs mt-1">
            The oracle scans every 5 minutes for weather markets with edge. Trades appear here automatically.
          </p>
        </div>
      )}

      {/* ── Trade History ── */}
      {resolvedTrades.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Clock size={14} className="text-syn-text-secondary" />
            Trade History
          </h2>
          <div className="bg-syn-surface border border-syn-border rounded-xl divide-y divide-syn-border/50">
            {resolvedTrades.slice(0, 20).map((t, i) => (
              <div key={`t-${i}`} className={`px-4 py-3 flex items-center justify-between ${
                t.outcome === true ? 'bg-emerald-500/5' : t.outcome === false ? 'bg-red-500/5' : ''
              }`}>
                <div className="flex items-center gap-3">
                  {t.outcome === true ? <CheckCircle size={14} className="text-emerald-400" /> :
                   t.outcome === false ? <XCircle size={14} className="text-red-400" /> :
                   <Clock size={14} className="text-syn-text-tertiary" />}
                  <span className="text-white text-sm">{t.city}</span>
                  <span className="text-xs text-syn-text-tertiary">{t.date}</span>
                  <span className="bg-syn-bg px-2 py-0.5 rounded text-xs font-mono text-syn-text-secondary">{t.bin_label}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="font-mono text-syn-text-secondary">{fmtUsd(t.quantity)}</span>
                  <span className={`font-mono font-medium ${(t.pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {fmtPnl(t.pnl)}
                  </span>
                  <span className="text-syn-text-tertiary">{timeAgo(t.placed_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
