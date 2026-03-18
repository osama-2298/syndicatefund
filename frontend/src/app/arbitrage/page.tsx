'use client';

import { useEffect, useState } from 'react';
import {
  ArrowUpDown, RefreshCw, TrendingUp, TrendingDown, Activity,
  DollarSign, Zap, Clock, ChevronDown, ChevronUp,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';

interface RateComparison {
  symbol: string;
  rates: Record<string, number>;
  highest: { exchange: string; rate_pct: number };
  lowest: { exchange: string; rate_pct: number };
  spread_pct: number;
  annualized_spread_pct: number;
  opportunity: string;
  strategy?: string;
}

interface FundingScan {
  status: string;
  timestamp?: string;
  symbols_scanned?: number;
  actionable_opportunities?: number;
  exchange_stats?: Record<string, { avg_rate_pct: number; symbols_reporting: number }>;
  opportunities?: RateComparison[];
  all_rates?: RateComparison[];
}

interface ArbStatus {
  enabled: boolean;
  paper_mode: boolean;
  strategies: Record<string, { enabled: boolean }>;
  portfolio: {
    cash: number;
    total_value: number;
    open_positions: number;
    total_realized_pnl: number;
    total_funding_collected: number;
    total_fees_paid: number;
    drawdown_pct: number;
  };
}

interface ArbStats {
  total_positions: number;
  open_positions: number;
  closed_positions: number;
  win_rate: number;
  total_pnl_usd: number;
  net_return_pct: number;
  total_opportunities_detected: number;
}

const EXCHANGE_COLORS: Record<string, string> = {
  binance: 'text-yellow-400',
  okx: 'text-white',
  bybit: 'text-orange-400',
  bitget: 'text-cyan-400',
};

const EXCHANGE_BG: Record<string, string> = {
  binance: 'bg-yellow-500/10 ring-yellow-500/20',
  okx: 'bg-white/10 ring-white/20',
  bybit: 'bg-orange-500/10 ring-orange-500/20',
  bitget: 'bg-cyan-500/10 ring-cyan-500/20',
};

function formatRate(rate: number): string {
  const sign = rate >= 0 ? '+' : '';
  return `${sign}${rate.toFixed(4)}%`;
}

function RateCell({ rate, isHighest, isLowest }: { rate: number; isHighest: boolean; isLowest: boolean }) {
  let colorClass = 'text-syn-text-secondary';
  if (isHighest) colorClass = 'text-red-400 font-semibold';
  if (isLowest) colorClass = 'text-emerald-400 font-semibold';

  return (
    <span className={`font-mono text-sm ${colorClass}`}>
      {formatRate(rate)}
    </span>
  );
}

function OpportunityBadge({ opportunity }: { opportunity: string }) {
  if (opportunity.startsWith('STRONG')) {
    return <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">STRONG</span>;
  }
  if (opportunity.startsWith('MODERATE')) {
    return <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20">MODERATE</span>;
  }
  if (opportunity.startsWith('WEAK')) {
    return <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-syn-surface text-syn-muted ring-1 ring-syn-border">WEAK</span>;
  }
  return <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-syn-surface text-syn-muted ring-1 ring-syn-border">-</span>;
}

export default function ArbitragePage() {
  const [scan, setScan] = useState<FundingScan | null>(null);
  const [status, setStatus] = useState<ArbStatus | null>(null);
  const [stats, setStats] = useState<ArbStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'spread' | 'symbol'>('spread');

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      fetch(`${API_BASE}/api/v1/arbitrage/funding-rates`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`${API_BASE}/api/v1/arbitrage/status`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`${API_BASE}/api/v1/arbitrage/stats`).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([scanData, statusData, statsData]) => {
      if (scanData) setScan(scanData);
      if (statusData) setStatus(statusData);
      if (statsData) setStats(statsData);
      setLoading(false);
    });
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60_000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/arbitrage/funding-rates/scan`, { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        setScan(data);
      }
    } catch (e) {
      console.error('Scan failed:', e);
    } finally {
      setScanning(false);
    }
  };

  const allRates = scan?.all_rates || [];
  const sortedRates = [...allRates].sort((a, b) => {
    if (sortBy === 'spread') return b.spread_pct - a.spread_pct;
    return a.symbol.localeCompare(b.symbol);
  });
  const exchanges = ['binance', 'okx', 'bybit', 'bitget'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Funding Rate Arbitrage</h1>
          <p className="text-sm text-syn-text-secondary mt-1">
            Cross-exchange funding rate comparison — 4 exchanges, real-time
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center gap-2 text-sm bg-syn-accent text-white px-4 py-2 rounded-lg font-medium hover:bg-syn-accent-hover transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={scanning ? 'animate-spin' : ''} />
          {scanning ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity size={14} className="text-syn-muted" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Symbols</span>
          </div>
          <div className="text-2xl font-bold font-mono">{scan?.symbols_scanned ?? '-'}</div>
        </div>

        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={14} className="text-emerald-400" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Opportunities</span>
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">{scan?.actionable_opportunities ?? '-'}</div>
        </div>

        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={14} className="text-syn-muted" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Portfolio</span>
          </div>
          <div className="text-2xl font-bold font-mono">
            ${(status?.portfolio?.total_value ?? 50000).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>

        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={14} className="text-syn-muted" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Total Detected</span>
          </div>
          <div className="text-2xl font-bold font-mono">{stats?.total_opportunities_detected ?? 0}</div>
        </div>
      </div>

      {/* Exchange Average Rates */}
      {scan?.exchange_stats && Object.keys(scan.exchange_stats).length > 0 && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-3">Exchange Average Funding Rates</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {exchanges.map(ex => {
              const stat = scan.exchange_stats?.[ex];
              if (!stat) return null;
              const rate = stat.avg_rate_pct;
              return (
                <div key={ex} className={`rounded-lg p-3 ring-1 ${EXCHANGE_BG[ex]}`}>
                  <div className={`text-xs font-bold uppercase ${EXCHANGE_COLORS[ex]}`}>{ex}</div>
                  <div className={`text-lg font-mono font-bold mt-1 ${rate >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatRate(rate)}
                  </div>
                  <div className="text-[10px] text-syn-muted">{stat.symbols_reporting} symbols</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Funding Rates Table */}
      <div className="bg-syn-surface border border-syn-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-syn-border flex items-center justify-between">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">
            Cross-Exchange Rates
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSortBy(sortBy === 'spread' ? 'symbol' : 'spread')}
              className="flex items-center gap-1 text-[10px] text-syn-muted hover:text-syn-text transition-colors"
            >
              <ArrowUpDown size={10} />
              {sortBy === 'spread' ? 'By Spread' : 'By Symbol'}
            </button>
            {scan?.timestamp && (
              <span className="text-[10px] text-syn-muted flex items-center gap-1">
                <Clock size={10} />
                {new Date(scan.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        {loading && !scan ? (
          <div className="p-8 text-center text-syn-muted">Loading funding rates...</div>
        ) : sortedRates.length === 0 ? (
          <div className="p-8 text-center text-syn-muted">
            No funding rate data yet. Click "Scan Now" to fetch live rates.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted">
                  <th className="text-left px-4 py-2">Symbol</th>
                  {exchanges.map(ex => (
                    <th key={ex} className={`text-right px-3 py-2 ${EXCHANGE_COLORS[ex]}`}>{ex}</th>
                  ))}
                  <th className="text-right px-3 py-2">Spread</th>
                  <th className="text-right px-3 py-2">Ann. %</th>
                  <th className="text-center px-3 py-2">Signal</th>
                </tr>
              </thead>
              <tbody>
                {sortedRates.map((row) => {
                  const isExpanded = expandedRow === row.symbol;
                  return (
                    <tr key={row.symbol} className="group">
                      <td colSpan={8} className="p-0">
                        <div
                          className="flex items-center cursor-pointer hover:bg-syn-bg/50 transition-colors"
                          onClick={() => setExpandedRow(isExpanded ? null : row.symbol)}
                        >
                          <div className="px-4 py-3 w-20 sm:w-24">
                            <span className="text-sm font-bold">{row.symbol}</span>
                          </div>
                          {exchanges.map(ex => (
                            <div key={ex} className="px-3 py-3 text-right flex-1">
                              {row.rates[ex] !== undefined ? (
                                <RateCell
                                  rate={row.rates[ex]}
                                  isHighest={ex === row.highest.exchange}
                                  isLowest={ex === row.lowest.exchange}
                                />
                              ) : (
                                <span className="text-xs text-syn-muted">-</span>
                              )}
                            </div>
                          ))}
                          <div className="px-3 py-3 text-right flex-1">
                            <span className={`font-mono text-sm font-semibold ${row.spread_pct > 0.02 ? 'text-emerald-400' : 'text-syn-text-secondary'}`}>
                              {row.spread_pct.toFixed(4)}%
                            </span>
                          </div>
                          <div className="px-3 py-3 text-right flex-1">
                            <span className={`font-mono text-sm ${row.annualized_spread_pct > 10 ? 'text-emerald-400' : 'text-syn-text-secondary'}`}>
                              {row.annualized_spread_pct.toFixed(1)}%
                            </span>
                          </div>
                          <div className="px-3 py-3 text-center flex-1 flex items-center justify-center gap-1">
                            <OpportunityBadge opportunity={row.opportunity} />
                            {isExpanded ? <ChevronUp size={12} className="text-syn-muted" /> : <ChevronDown size={12} className="text-syn-muted" />}
                          </div>
                        </div>

                        {/* Expanded strategy detail */}
                        {isExpanded && row.strategy && (
                          <div className="px-4 pb-3 pt-0">
                            <div className="bg-syn-bg rounded-lg p-3 text-xs text-syn-text-secondary border border-syn-border">
                              <div className="flex items-center gap-2 mb-1">
                                <Zap size={12} className="text-amber-400" />
                                <span className="font-semibold text-syn-text">Strategy</span>
                              </div>
                              {row.strategy}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Engine Status */}
      {status && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-4">
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-3">Engine Status</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {Object.entries(status.strategies).map(([name, s]) => (
              <div key={name} className="flex items-center justify-between p-3 bg-syn-bg rounded-lg border border-syn-border">
                <span className="text-sm font-medium capitalize">{name.replace(/_/g, ' ')}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${s.enabled ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20' : 'bg-syn-surface text-syn-muted ring-1 ring-syn-border'}`}>
                  {s.enabled ? 'ACTIVE' : 'DISABLED'}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-4 text-xs text-syn-muted">
            <span>Mode: {status.paper_mode ? 'Paper Trading' : 'Live'}</span>
            <span>Open Positions: {status.portfolio.open_positions}</span>
            <span>Realized PnL: ${status.portfolio.total_realized_pnl.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
