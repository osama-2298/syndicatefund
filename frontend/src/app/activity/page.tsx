'use client';

import { useEffect, useState } from 'react';
import { Activity, Clock } from 'lucide-react';
import CycleCard, { type CycleData, type PipelineEvent } from '@/components/CycleCard';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ActivityPage() {
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [eventsByCycle, setEventsByCycle] = useState<Record<number, PipelineEvent[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/cycles?limit=25`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/events?limit=200`).then(r => r.json()).catch(() => []),
    ]).then(([cyclesData, eventsData]) => {
      let c: CycleData[] = Array.isArray(cyclesData) ? cyclesData : [];
      const e = Array.isArray(eventsData) ? eventsData : [];

      const grouped: Record<number, PipelineEvent[]> = {};
      const ungrouped: PipelineEvent[] = [];

      for (const event of e) {
        const cid = event.cycle_id;
        if (cid != null) {
          if (!grouped[cid]) grouped[cid] = [];
          grouped[cid].push(event);
        } else {
          ungrouped.push(event);
        }
      }

      if (ungrouped.length > 0 && c.length > 0) {
        const firstCycleId = c[0].id;
        if (!grouped[firstCycleId]) grouped[firstCycleId] = [];
        grouped[firstCycleId].push(...ungrouped);
      } else if (ungrouped.length > 0 && c.length === 0) {
        grouped[-1] = ungrouped;
        c = [{ id: -1, started_at: ungrouped[0]?.timestamp || '', completed_at: null, regime: null,
               coins_analyzed: 0, signals_produced: 0, orders_executed: 0, duration_secs: null }];
      }

      setCycles(c);
      for (const cid of Object.keys(grouped)) {
        grouped[Number(cid)] = grouped[Number(cid)].reverse();
      }
      setEventsByCycle(grouped);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={24} className="animate-spin text-hive-accent" />
      </div>
    );
  }

  const cyclesWithEvents = cycles.filter(c => (eventsByCycle[c.id] || []).length > 0);
  const totalSignals = cycles.reduce((s, c) => s + c.signals_produced, 0);
  const totalTrades = cycles.reduce((s, c) => s + c.orders_executed, 0);

  return (
    <div className="slide-up space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Activity</h1>
        <p className="text-sm text-hive-muted mt-1">
          Every decision the AI makes, organized by cycle. The latest cycle is expanded by default.
        </p>
      </div>

      {/* Summary stats strip */}
      {cyclesWithEvents.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Total Cycles</p>
            <p className="text-lg font-bold font-mono tabular-nums text-white/90">{cycles.length}</p>
          </div>
          <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Signals</p>
            <p className="text-lg font-bold font-mono tabular-nums text-white/90">{totalSignals.toLocaleString()}</p>
          </div>
          <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Trades</p>
            <p className="text-lg font-bold font-mono tabular-nums text-white/90">{totalTrades}</p>
          </div>
        </div>
      )}

      {cyclesWithEvents.length === 0 ? (
        <div className="glass-card p-10 text-center">
          <Clock size={32} className="mx-auto text-white/10 mb-3" />
          <p className="text-sm text-hive-muted">No cycle activity recorded yet.</p>
          <p className="text-xs text-hive-muted/50 mt-1">The pipeline runs every 4 hours. Activity will appear here after the next cycle completes.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {cyclesWithEvents.map((cycle, i) => (
            <CycleCard
              key={cycle.id}
              cycle={cycle}
              events={eventsByCycle[cycle.id] || []}
              defaultOpen={i === 0}
            />
          ))}
        </div>
      )}
    </div>
  );
}
