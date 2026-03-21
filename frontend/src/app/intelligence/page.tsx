'use client';

import { useEffect, useState } from 'react';
import { Shield, Zap, AlertTriangle, Radio, Activity, Eye } from 'lucide-react';
import { API_BASE } from '@/lib/api';
import { SEVERITY_COLORS, DRAWDOWN_COLORS } from '@/lib/constants';
import type { FastLoopEvent, PortfolioRisk } from '@/lib/types';

export default function IntelligencePage() {
  const [events, setEvents] = useState<FastLoopEvent[]>([]);
  const [risk, setRisk] = useState<PortfolioRisk | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [filter, setFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/intelligence/events?limit=100`).then(r => r.json()).catch(() => ({ events: [] })),
      fetch(`${API_BASE}/api/v1/portfolio/risk`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/v1/intelligence/status`).then(r => r.json()).catch(() => null),
    ]).then(([evtData, riskData, statusData]) => {
      setEvents(evtData?.events ?? []);
      setRisk(riskData);
      setStatus(statusData);
      setLoading(false);
    });
  }, []);

  const filteredEvents = filter === 'all'
    ? events
    : events.filter(e => e.severity === filter);

  const severityCounts = events.reduce((acc, e) => {
    acc[e.severity] = (acc[e.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const fmtTime = (iso: string) => {
    try { return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }); }
    catch { return ''; }
  };
  const fmtDate = (iso: string) => {
    try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); }
    catch { return ''; }
  };

  if (loading) return (
    <div className="min-h-screen bg-syn-bg flex items-center justify-center">
      <div className="animate-pulse text-syn-muted">Loading intelligence feed...</div>
    </div>
  );

  return (
    <main className="min-h-screen bg-syn-bg text-syn-text py-20 px-4">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Radio size={20} className="text-cyan-400" />
              <h1 className="text-2xl font-bold">Intelligence Network</h1>
            </div>
            <p className="text-sm text-syn-text-secondary">
              15-minute fast loop monitoring news, prices, and portfolio risk between analysis cycles.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-syn-muted">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Fast loop {status?.fast_loop_enabled ? 'active' : 'inactive'} ({status?.interval_minutes ?? 15}min)
          </div>
        </div>

        {/* Risk Dashboard */}
        {risk && (
          <div className="bg-syn-surface border border-syn-border rounded-xl p-5">
            <h2 className="text-xs font-bold uppercase tracking-widest text-syn-muted mb-4">Portfolio Risk Status</h2>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              {/* Drawdown Level */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Drawdown Level</p>
                <div className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${
                  DRAWDOWN_COLORS[risk.drawdown_level]?.bg ?? 'bg-syn-surface'
                } ${DRAWDOWN_COLORS[risk.drawdown_level]?.color ?? ''}`}>
                  {DRAWDOWN_COLORS[risk.drawdown_level]?.label ?? risk.drawdown_level}
                </div>
                <p className="text-[10px] text-syn-muted mt-1">{risk.drawdown_pct.toFixed(2)}% from peak</p>
              </div>

              {/* Heat */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Portfolio Heat</p>
                <p className={`text-xl font-mono font-bold ${
                  risk.heat_exceeded ? 'text-red-400' : risk.portfolio_heat > 5 ? 'text-amber-400' : 'text-emerald-400'
                }`}>{risk.portfolio_heat.toFixed(1)}%</p>
                <p className="text-[10px] text-syn-muted">of 7% limit</p>
              </div>

              {/* Correlation */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Avg Correlation</p>
                <p className={`text-xl font-mono font-bold ${
                  risk.avg_correlation > 0.7 ? 'text-red-400' : risk.avg_correlation > 0.5 ? 'text-amber-400' : 'text-emerald-400'
                }`}>{risk.avg_correlation.toFixed(2)}</p>
                <p className="text-[10px] text-syn-muted">{risk.correlation_warning ? 'Warning!' : 'Normal'}</p>
              </div>

              {/* Exposure */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Gross Exposure</p>
                <p className="text-xl font-mono font-bold text-syn-text">{risk.gross_exposure.toFixed(0)}%</p>
                <p className="text-[10px] text-syn-muted">Net: {risk.net_exposure.toFixed(0)}%</p>
              </div>

              {/* Trading Status */}
              <div className="text-center">
                <p className="text-[10px] text-syn-text-tertiary mb-1">Trading</p>
                <p className={`text-xl font-bold ${risk.trading_allowed ? 'text-emerald-400' : 'text-red-500'}`}>
                  {risk.trading_allowed ? 'ACTIVE' : 'HALTED'}
                </p>
                <p className="text-[10px] text-syn-muted">Size: {(risk.size_multiplier * 100).toFixed(0)}%</p>
              </div>
            </div>

            {risk.actions.length > 0 && (
              <div className="mt-3 pt-3 border-t border-syn-border">
                {risk.actions.map((a, i) => (
                  <p key={i} className="text-xs text-orange-400 font-mono flex items-center gap-1.5 mb-1">
                    <AlertTriangle size={12} /> {a}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Event Stats + Filter */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`text-xs px-3 py-1.5 rounded-full border transition ${
              filter === 'all' ? 'bg-syn-accent/20 border-syn-accent text-syn-accent' : 'border-syn-border text-syn-muted hover:text-syn-text'
            }`}
          >All ({events.length})</button>
          {(['critical', 'high', 'medium', 'low'] as const).map(sev => (
            <button
              key={sev}
              onClick={() => setFilter(sev)}
              className={`text-xs px-3 py-1.5 rounded-full border transition ${
                filter === sev ? `${SEVERITY_COLORS[sev]} border-current` : 'border-syn-border text-syn-muted hover:text-syn-text'
              }`}
            >{sev} ({severityCounts[sev] ?? 0})</button>
          ))}
        </div>

        {/* Event Feed */}
        <div className="space-y-2">
          {filteredEvents.length === 0 ? (
            <div className="bg-syn-surface border border-syn-border rounded-xl p-8 text-center">
              <Eye size={24} className="mx-auto text-syn-muted mb-2" />
              <p className="text-sm text-syn-muted">No intelligence events yet. The fast loop will populate this feed.</p>
            </div>
          ) : (
            filteredEvents.map((evt, i) => (
              <div
                key={i}
                className={`bg-syn-surface border border-syn-border rounded-lg p-3 flex items-start gap-3 ${
                  evt.acted_upon ? 'border-l-2 border-l-orange-400' : ''
                }`}
              >
                <div className={`mt-0.5 shrink-0 ${SEVERITY_COLORS[evt.severity] ?? 'text-syn-muted'}`}>
                  {evt.severity === 'critical' ? <AlertTriangle size={16} /> :
                    evt.severity === 'high' ? <Zap size={16} /> :
                      evt.event_type === 'risk_action' ? <Shield size={16} /> :
                        <Activity size={16} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${SEVERITY_COLORS[evt.severity] ?? ''}`}>
                      {evt.severity}
                    </span>
                    <span className="text-[10px] text-syn-muted font-mono">{evt.event_type.replace(/_/g, ' ')}</span>
                    <span className="text-[10px] text-syn-text-tertiary">{evt.source}</span>
                    {evt.acted_upon && (
                      <span className="text-[10px] font-bold text-orange-400">ACTION TAKEN</span>
                    )}
                  </div>
                  <p className="text-sm text-syn-text mt-1 break-words">{evt.title}</p>
                  {evt.symbols.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {evt.symbols.map(s => (
                        <span key={s} className="text-[10px] font-mono bg-syn-bg px-1.5 py-0.5 rounded text-syn-muted">
                          {s.replace('USDT', '')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[10px] text-syn-text-tertiary">{fmtTime(evt.timestamp)}</p>
                  <p className="text-[10px] text-syn-muted">{fmtDate(evt.timestamp)}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </main>
  );
}
