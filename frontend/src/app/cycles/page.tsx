'use client';

import { useEffect, useState } from 'react';
import { Activity, Loader2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

const regimeColors: Record<string, string> = {
  bull: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/30',
  bear: 'text-red-400 bg-red-400/10 ring-red-400/30',
  crisis: 'text-red-300 bg-red-900/20 ring-red-900/40',
  ranging: 'text-amber-400 bg-amber-400/10 ring-amber-400/30',
};

function RegimeBadge({ regime }: { regime: string | null }) {
  if (!regime) return <span className="text-white/20 text-sm">{'\u2014'}</span>;
  const color = regimeColors[regime] || 'text-gray-400 bg-gray-400/10 ring-gray-400/30';
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${color}`}>
      {regime.toUpperCase()}
    </span>
  );
}

function StatusCell({ cycle }: { cycle: CycleSummary }) {
  const isRunning = !cycle.completed_at;
  const hasError = !!cycle.error;

  if (isRunning) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-blue-400 bg-blue-400/10 ring-blue-400/30">
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-400" />
        </span>
        RUNNING
      </span>
    );
  }

  if (hasError) {
    return (
      <span
        className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-red-400 bg-red-400/10 ring-red-400/30 cursor-help"
        title={cycle.error ?? ''}
      >
        ERROR
      </span>
    );
  }

  return (
    <span className="text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset text-emerald-400 bg-emerald-400/10 ring-emerald-400/30">
      DONE
    </span>
  );
}

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

  return (
    <div className="slide-up space-y-8">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-white/[0.04]">
          <Activity size={20} className="text-amber-400/60" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cycle History</h1>
          <p className="text-sm text-white/40 mt-1">
            {loading
              ? 'Loading cycles...'
              : `${cycles.length} cycles \u2014 pipeline runs every 4 hours aligned to UTC`}
          </p>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="glass-card flex items-center justify-center py-20">
          <Loader2 size={24} className="text-white/20 animate-spin" />
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="glass-card flex flex-col items-center justify-center py-20">
          <Activity size={40} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">Could not load cycles</p>
          <p className="text-xs text-white/20 mt-1">Make sure the API server is running</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && cycles.length === 0 && (
        <div className="glass-card flex flex-col items-center justify-center py-20">
          <Activity size={40} className="text-white/10 mb-3" />
          <p className="text-sm text-white/40">No cycles recorded yet</p>
          <p className="text-xs text-white/20 mt-1">
            Start the server with <code className="font-mono bg-white/[0.06] px-1.5 py-0.5 rounded text-[11px]">python -m hivemind.main --serve</code>
          </p>
        </div>
      )}

      {/* Cycles Table */}
      {!loading && !error && cycles.length > 0 && (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Cycle</th>
                  <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Started</th>
                  <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Regime</th>
                  <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Coins</th>
                  <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Signals</th>
                  <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Orders</th>
                  <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Portfolio</th>
                  <th className="text-right px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Duration</th>
                  <th className="text-left px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Status</th>
                </tr>
              </thead>
              <tbody>
                {cycles.map((cycle) => (
                  <tr key={cycle.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3 text-sm font-medium text-white/40 tabular-nums">#{cycle.id}</td>
                    <td className="px-5 py-3 text-sm text-white/60">
                      {new Date(cycle.started_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3">
                      <RegimeBadge regime={cycle.regime} />
                    </td>
                    <td className="px-5 py-3 text-right text-sm tabular-nums text-white/60">{cycle.coins_analyzed}</td>
                    <td className="px-5 py-3 text-right text-sm tabular-nums text-white/60">{cycle.signals_produced}</td>
                    <td className="px-5 py-3 text-right text-sm tabular-nums text-white/60">{cycle.orders_executed}</td>
                    <td className="px-5 py-3 text-right text-sm tabular-nums text-white/60">
                      {cycle.portfolio_value
                        ? `$${cycle.portfolio_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                        : '\u2014'}
                    </td>
                    <td className="px-5 py-3 text-right text-sm tabular-nums text-white/30">
                      {cycle.duration_secs ? `${Math.round(cycle.duration_secs)}s` : '\u2014'}
                    </td>
                    <td className="px-5 py-3">
                      <StatusCell cycle={cycle} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
