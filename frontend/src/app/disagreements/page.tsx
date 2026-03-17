'use client';

import { useEffect, useState } from 'react';
import { Swords, Activity } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PipelineEvent {
  id: string;
  event_type: string;
  timestamp: string;
  actor: string;
  title: string;
  detail: {
    symbol?: string;
    polarization?: number;
    bullish_teams?: Array<{ team: string; score: number }>;
    bearish_teams?: Array<{ team: string; score: number }>;
    resolution?: string;
    resolution_confidence?: number;
  } | null;
}

export default function DisagreementsPage() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/events?event_type=disagreement&limit=50`)
      .then(r => r.json())
      .then(data => setEvents(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={24} className="animate-spin text-hive-accent" />
      </div>
    );
  }

  return (
    <div className="slide-up space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Disagreement Theater</h1>
        <p className="text-sm text-hive-muted mt-1">
          When AI teams clash — every polarized debate between bullish and bearish analysis.
        </p>
      </div>

      {events.length === 0 ? (
        <div className="glass-card p-10 text-center">
          <Swords size={32} className="mx-auto text-white/10 mb-3" />
          <p className="text-sm text-hive-muted">No disagreements recorded yet</p>
          <p className="text-xs text-hive-muted/50 mt-1">Disagreements appear when team signals are polarized (&gt;50%)</p>
        </div>
      ) : (
        <div className="space-y-4">
          {events.map((event) => {
            if (!event.detail) return null;
            const { symbol, polarization, bullish_teams, bearish_teams, resolution, resolution_confidence } = event.detail;
            const base = symbol?.replace('USDT', '') || '???';
            const time = new Date(event.timestamp).toLocaleString();

            return (
              <div key={event.id} className="glass-card overflow-hidden">
                <div className="px-5 py-3 border-b border-white/[0.06] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Swords size={12} className="text-red-400" />
                    <span className="text-sm font-bold">{base}</span>
                    <span className="text-xs text-red-400 font-medium">{((polarization || 0) * 100).toFixed(0)}% polarized</span>
                  </div>
                  <span className="text-[10px] text-hive-muted">{time}</span>
                </div>

                <div className="p-5">
                  <div className="grid grid-cols-2 gap-4">
                    {/* Bullish */}
                    <div className="rounded-lg bg-emerald-500/[0.04] border border-emerald-500/10 p-3">
                      <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest mb-2">Bullish</div>
                      {(bullish_teams || []).length === 0 ? (
                        <p className="text-xs text-hive-muted">No bull teams</p>
                      ) : (
                        <div className="space-y-1.5">
                          {bullish_teams!.map((t, i) => (
                            <div key={i} className="flex items-center gap-2">
                              <span className="text-xs capitalize flex-1">{t.team}</span>
                              <div className="w-16 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.min(100, Math.abs(t.score) * 100)}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Bearish */}
                    <div className="rounded-lg bg-red-500/[0.04] border border-red-500/10 p-3">
                      <div className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-2">Bearish</div>
                      {(bearish_teams || []).length === 0 ? (
                        <p className="text-xs text-hive-muted">No bear teams</p>
                      ) : (
                        <div className="space-y-1.5">
                          {bearish_teams!.map((t, i) => (
                            <div key={i} className="flex items-center gap-2">
                              <span className="text-xs capitalize flex-1">{t.team}</span>
                              <div className="w-16 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                                <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.min(100, Math.abs(t.score) * 100)}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {resolution && (
                    <div className="mt-3 pt-3 border-t border-white/[0.03] text-center">
                      <span className="text-[10px] text-hive-muted">Resolution: </span>
                      <span className={`text-xs font-bold ${resolution === 'BUY' ? 'text-emerald-400' : resolution === 'SELL' || resolution === 'SHORT' ? 'text-red-400' : 'text-hive-text'}`}>
                        {resolution}
                      </span>
                      {resolution_confidence != null && (
                        <span className="text-[10px] text-hive-muted ml-1">({(resolution_confidence * 100).toFixed(0)}% confidence)</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
