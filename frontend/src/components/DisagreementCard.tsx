'use client';

import { useEffect, useState } from 'react';
import { Swords, ArrowRight } from 'lucide-react';
import { API_BASE } from '@/lib/api';

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

export default function DisagreementCard() {
  const [event, setEvent] = useState<PipelineEvent | null>(null);

  useEffect(() => {
    const fetchDisagreement = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/events?event_type=disagreement&limit=1`);
        if (!res.ok) return;
        const data: PipelineEvent[] = await res.json();
        if (data.length > 0) setEvent(data[0]);
      } catch {}
    };
    fetchDisagreement();
    const interval = setInterval(fetchDisagreement, 15000);
    return () => clearInterval(interval);
  }, []);

  if (!event || !event.detail) {
    return (
      <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-syn-border flex items-center gap-2">
          <Swords size={14} className="text-red-400" />
          <h2 className="text-sm font-semibold">Latest Disagreement</h2>
        </div>
        <div className="px-5 py-6 text-center">
          <p className="text-xs text-syn-text-secondary">No team clashes yet. Disagreements appear when agents are split on a trade.</p>
        </div>
      </div>
    );
  }

  const { symbol, polarization, bullish_teams, bearish_teams, resolution, resolution_confidence } = event.detail;
  const base = symbol?.replace('USDT', '') || '???';

  return (
    <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
      <div className="px-5 py-4 border-b border-syn-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Swords size={14} className="text-red-400" />
          <h2 className="text-sm font-semibold">Latest Disagreement</h2>
        </div>
        <a href="/disagreements" className="text-xs text-syn-accent hover:text-violet-300 transition-colors flex items-center gap-1">
          History <ArrowRight size={12} />
        </a>
      </div>

      <div className="p-5">
        {/* Symbol + polarization */}
        <div className="text-center mb-4">
          <span className="text-lg font-bold">{base}</span>
          <span className="ml-2 text-xs text-red-400 font-medium">{((polarization || 0) * 100).toFixed(0)}% polarized</span>
        </div>

        {/* Bull vs Bear columns */}
        <div className="grid grid-cols-2 gap-4">
          {/* Bullish */}
          <div className="rounded-lg bg-emerald-500/[0.04] border border-emerald-500/10 p-3">
            <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest mb-2">Bullish</div>
            {(bullish_teams || []).length === 0 ? (
              <p className="text-xs text-syn-text-secondary">No bull teams</p>
            ) : (
              <div className="space-y-1.5">
                {bullish_teams!.map((t, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-xs capitalize flex-1">{t.team}</span>
                    <div className="w-12 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
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
              <p className="text-xs text-syn-text-secondary">No bear teams</p>
            ) : (
              <div className="space-y-1.5">
                {bearish_teams!.map((t, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-xs capitalize flex-1">{t.team}</span>
                    <div className="w-12 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                      <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.min(100, Math.abs(t.score) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Resolution */}
        {resolution && (
          <div className="mt-3 text-center">
            <span className="text-[10px] text-syn-text-secondary">Resolution: </span>
            <span className={`text-xs font-bold ${resolution === 'BUY' ? 'text-emerald-400' : resolution === 'SELL' || resolution === 'SHORT' ? 'text-red-400' : 'text-syn-text'}`}>
              {resolution}
            </span>
            {resolution_confidence != null && (
              <span className="text-[10px] text-syn-text-secondary ml-1">({(resolution_confidence * 100).toFixed(0)}% conf)</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
