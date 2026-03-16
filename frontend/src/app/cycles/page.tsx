'use client';

import { useEffect, useState } from 'react';
import { Loader2, Activity, Clock, Radio, Coins, ShoppingCart, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* ------------------------------------------------------------------ */
/*  TYPES                                                              */
/* ------------------------------------------------------------------ */

interface CycleSummary {
  id: number;
  started_at: string;
  completed_at: string | null;
  duration_secs: number | null;
  regime: string | null;
  coins_analyzed: number;
  signals_produced: number;
  orders_executed: number;
  portfolio_value: number | null;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  DESIGN CONSTANTS                                                   */
/* ------------------------------------------------------------------ */

const regimeConfig: Record<string, { color: string; bg: string; ring: string }> = {
  bull: { color: 'text-emerald-400', bg: 'bg-emerald-400/10', ring: 'ring-emerald-400/30' },
  bear: { color: 'text-red-400', bg: 'bg-red-400/10', ring: 'ring-red-400/30' },
  crisis: { color: 'text-red-300', bg: 'bg-red-900/20', ring: 'ring-red-900/40' },
  ranging: { color: 'text-amber-400', bg: 'bg-amber-400/10', ring: 'ring-amber-400/30' },
};

/* ------------------------------------------------------------------ */
/*  SUB-COMPONENTS                                                     */
/* ------------------------------------------------------------------ */

function SummaryStrip({ cycles }: { cycles: CycleSummary[] }) {
  const completed = cycles.filter(c => c.completed_at && !c.error);
  const totalSignals = cycles.reduce((s, c) => s + c.signals_produced, 0);
  const totalOrders = cycles.reduce((s, c) => s + c.orders_executed, 0);
  const avgDuration = completed.length > 0
    ? completed.reduce((s, c) => s + (c.duration_secs || 0), 0) / completed.length
    : 0;

  const stats = [
    { label: 'Total Cycles', value: cycles.length.toString(), icon: Activity },
    { label: 'Avg Duration', value: avgDuration > 0 ? `${Math.round(avgDuration)}s` : '\u2014', icon: Clock },
    { label: 'Total Signals', value: totalSignals.toLocaleString(), icon: Radio },
    { label: 'Total Orders', value: totalOrders.toLocaleString(), icon: ShoppingCart },
    {
      label: 'Success Rate',
      value: cycles.length > 0 ? `${Math.round((completed.length / cycles.length) * 100)}%` : '\u2014',
      icon: Activity,
    },
  ];

  return (
    <div className="grid grid-cols-5 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-[#0d0d15] border border-white/[0.06] rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1.5">
            <stat.icon size={12} className="text-white/20" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">{stat.label}</p>
          </div>
          <p className="text-xl font-bold font-mono tabular-nums text-white/90">{stat.value}</p>
        </div>
      ))}
    </div>
  );
}

function RegimeBadge({ regime }: { regime: string | null }) {
  if (!regime) return <span className="text-white/15 text-xs font-mono">\u2014</span>;
  const config = regimeConfig[regime] || { color: 'text-gray-400', bg: 'bg-gray-400/10', ring: 'ring-gray-400/30' };
  return (
    <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ring-1 ring-inset ${config.color} ${config.bg} ${config.ring}`}>
      {regime.toUpperCase()}
    </span>
  );
}

function StatusIndicator({ cycle }: { cycle: CycleSummary }) {
  const isRunning = !cycle.completed_at;
  const hasError = !!cycle.error;

  if (isRunning) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-400" />
        </span>
        <span className="text-[10px] font-bold text-blue-400">RUNNING</span>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="flex h-2 w-2 rounded-full bg-red-400" />
        <span className="text-[10px] font-bold text-red-400">ERROR</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <span className="flex h-2 w-2 rounded-full bg-emerald-400" />
      <span className="text-[10px] font-bold text-emerald-400">DONE</span>
    </div>
  );
}

function DurationBar({ duration, maxDuration }: { duration: number | null; maxDuration: number }) {
  if (!duration || maxDuration === 0) return <span className="text-white/15 text-xs font-mono">\u2014</span>;
  const pct = Math.min((duration / maxDuration) * 100, 100);
  const color = duration > maxDuration * 0.8 ? 'bg-red-400/70' : duration > maxDuration * 0.5 ? 'bg-amber-400/70' : 'bg-emerald-400/70';
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono tabular-nums text-white/40 w-10 text-right">{Math.round(duration)}s</span>
    </div>
  );
}

function CycleRow({ cycle, maxDuration }: { cycle: CycleSummary; maxDuration: number }) {
  const [expanded, setExpanded] = useState(false);
  const hasError = !!cycle.error;

  return (
    <>
      <div
        className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/[0.03] transition-colors cursor-pointer border-b border-white/[0.03]"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Cycle number circle */}
        <div className="w-9 h-9 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center flex-shrink-0">
          <span className="text-xs font-bold font-mono tabular-nums text-white/60">{cycle.id}</span>
        </div>

        {/* Regime badge */}
        <div className="w-24 flex-shrink-0">
          <RegimeBadge regime={cycle.regime} />
        </div>

        {/* Timestamp */}
        <div className="w-40 flex-shrink-0">
          <p className="text-xs font-mono text-white/50">
            {new Date(cycle.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </p>
          <p className="text-[10px] font-mono text-white/25">
            {new Date(cycle.started_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </p>
        </div>

        {/* Stats: coins | signals | orders */}
        <div className="flex items-center gap-5 flex-shrink-0">
          <div className="flex items-center gap-1.5" title="Coins analyzed">
            <Coins size={11} className="text-white/20" />
            <span className="text-xs font-mono tabular-nums text-white/50">{cycle.coins_analyzed}</span>
          </div>
          <div className="flex items-center gap-1.5" title="Signals produced">
            <Radio size={11} className="text-white/20" />
            <span className="text-xs font-mono tabular-nums text-white/50">{cycle.signals_produced}</span>
          </div>
          <div className="flex items-center gap-1.5" title="Orders executed">
            <ShoppingCart size={11} className="text-white/20" />
            <span className="text-xs font-mono tabular-nums text-white/50">{cycle.orders_executed}</span>
          </div>
        </div>

        {/* Duration bar */}
        <div className="flex-1 min-w-0">
          <DurationBar duration={cycle.duration_secs} maxDuration={maxDuration} />
        </div>

        {/* Status */}
        <div className="w-24 flex-shrink-0 flex justify-end">
          <StatusIndicator cycle={cycle} />
        </div>

        {/* Expand icon */}
        <div className="flex-shrink-0 text-white/15">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-5 py-4 bg-white/[0.01] border-b border-white/[0.06]">
          <div className="ml-[52px] grid grid-cols-4 gap-6">
            <div>
              <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-amber-400/60 mb-1">Started</p>
              <p className="text-xs font-mono text-white/60">{new Date(cycle.started_at).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-amber-400/60 mb-1">Completed</p>
              <p className="text-xs font-mono text-white/60">
                {cycle.completed_at ? new Date(cycle.completed_at).toLocaleString() : 'In progress...'}
              </p>
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-amber-400/60 mb-1">Duration</p>
              <p className="text-xs font-mono text-white/60">
                {cycle.duration_secs ? `${cycle.duration_secs.toFixed(1)} seconds` : '\u2014'}
              </p>
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-amber-400/60 mb-1">Portfolio Value</p>
              <p className="text-xs font-mono text-white/60">
                {cycle.portfolio_value
                  ? `$${cycle.portfolio_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : '\u2014'}
              </p>
            </div>
          </div>

          {hasError && (
            <div className="ml-[52px] mt-3 flex items-start gap-2 p-3 rounded-lg bg-red-900/10 border border-red-900/20">
              <AlertTriangle size={14} className="text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs font-mono text-red-400/80 break-all">{cycle.error}</p>
            </div>
          )}
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN PAGE                                                          */
/* ------------------------------------------------------------------ */

export default function CyclesPage() {
  const [cycles, setCycles] = useState<CycleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/cycles?limit=50`)
      .then((r) => r.json())
      .then((data) => {
        setCycles(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  const maxDuration = Math.max(...cycles.map(c => c.duration_secs || 0), 1);

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Cycle History</h1>
        <p className="text-sm text-white/30 mt-1">
          {loading
            ? 'Loading cycles...'
            : `${cycles.length} cycles \u2014 pipeline runs every 4 hours aligned to UTC`}
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex items-center justify-center py-24">
          <Loader2 size={24} className="text-white/20 animate-spin" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex flex-col items-center justify-center py-24">
          <Activity size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">Could not load cycles</p>
          <p className="text-xs text-white/20 mt-1">Ensure the API server is running on {API_BASE}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && cycles.length === 0 && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl flex flex-col items-center justify-center py-24">
          <Activity size={36} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">No cycles recorded yet</p>
          <p className="text-xs text-white/20 mt-1">
            Start the server with <code className="font-mono bg-white/[0.06] px-1.5 py-0.5 rounded text-[11px]">python -m hivemind.main --serve</code>
          </p>
        </div>
      )}

      {/* Main Content */}
      {!loading && !error && cycles.length > 0 && (
        <>
          {/* Summary Strip */}
          <SummaryStrip cycles={cycles} />

          {/* Timeline header */}
          <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl overflow-hidden">
            {/* Column headers */}
            <div className="flex items-center gap-4 px-5 py-2.5 border-b border-white/[0.06]">
              <div className="w-9 flex-shrink-0" />
              <div className="w-24 flex-shrink-0">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25">Regime</span>
              </div>
              <div className="w-40 flex-shrink-0">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25">Timestamp</span>
              </div>
              <div className="flex items-center gap-5 flex-shrink-0">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25 w-10">Coin</span>
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25 w-10">Sig</span>
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25 w-10">Ord</span>
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25">Duration</span>
              </div>
              <div className="w-24 flex-shrink-0 text-right">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-white/25">Status</span>
              </div>
              <div className="w-[14px] flex-shrink-0" />
            </div>

            {/* Cycle rows */}
            {cycles.map((cycle) => (
              <CycleRow key={cycle.id} cycle={cycle} maxDuration={maxDuration} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
