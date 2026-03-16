'use client';

import { useEffect, useState, useRef } from 'react';
import {
  Activity, ArrowRight, Play, Brain, Search, Target,
  Shield, Users, Scale, CheckCircle, XCircle, DollarSign,
  LogOut, Star, Swords, BarChart3,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PipelineEvent {
  id: string;
  cycle_id: number | null;
  event_type: string;
  timestamp: string;
  stage: string;
  actor: string;
  title: string;
  detail: Record<string, any> | null;
  elapsed_ms: number | null;
}

// Transform raw events into clear, human-readable messages
function humanize(event: PipelineEvent): { icon: typeof Play; color: string; message: string } {
  const d = event.detail || {};

  switch (event.event_type) {
    case 'cycle_start':
      return { icon: Play, color: 'text-white/60', message: 'New analysis cycle started' };

    case 'cycle_end':
      return {
        icon: CheckCircle, color: 'text-emerald-400',
        message: `Cycle complete — analyzed ${d.coins_analyzed || '?'} coins, produced ${d.signals_produced || '?'} signals, executed ${d.orders_executed || 0} trades`,
      };

    case 'intel_gathered':
      return {
        icon: Search, color: 'text-blue-400',
        message: `Market intel collected from ${d.sources?.length || '?'} sources${d.fear_greed ? ` — Fear & Greed: ${d.fear_greed}/100` : ''}`,
      };

    case 'ceo_directive': {
      if (d.emergency_halt) return { icon: Shield, color: 'text-red-400', message: `CEO halted all trading — ${d.halt_reason || 'emergency'}` };
      const regime = (d.regime || '').toUpperCase();
      return {
        icon: Brain, color: 'text-amber-400',
        message: `CEO reads the market as ${regime}${d.risk_multiplier ? ` — risk level ${d.risk_multiplier}x` : ''}`,
      };
    }

    case 'coo_selection': {
      if (event.actor === 'Hot Coin Detector') {
        const sym = (d.symbol || '').replace('USDT', '');
        return { icon: Star, color: 'text-fuchsia-400', message: `Trending coin added: ${sym} — ${d.reason || 'high momentum'}` };
      }
      const coins = (d.coins || []).map((c: string) => c.replace('USDT', '')).join(', ');
      return { icon: Target, color: 'text-amber-400', message: `${d.coins?.length || '?'} coins selected for analysis: ${coins}` };
    }

    case 'cro_rules':
      return {
        icon: Shield, color: 'text-orange-400',
        message: `Risk limits set — max ${d.max_position_pct || '?'}% per trade, min ${Math.round((d.min_signal_confidence || 0) * 100)}% confidence required`,
      };

    case 'team_signal': {
      const team = d.team || 'Unknown';
      const action = d.action || '?';
      const sym = (d.symbol || '').replace('USDT', '');
      const conf = Math.round((d.confidence || 0) * 100);
      const verb = action === 'BUY' ? 'is bullish on' : action === 'SELL' || action === 'SHORT' ? 'is bearish on' : 'says hold';
      return { icon: Users, color: 'text-blue-400', message: `${team} team ${verb} ${sym} (${conf}% confidence)` };
    }

    case 'disagreement': {
      const sym = (d.symbol || '').replace('USDT', '');
      const pol = Math.round((d.polarization || 0) * 100);
      const nBull = (d.bullish_teams || []).length;
      const nBear = (d.bearish_teams || []).length;
      return {
        icon: Swords, color: 'text-red-400',
        message: `Teams split on ${sym} — ${nBull} bullish vs ${nBear} bearish (${pol}% disagreement)`,
      };
    }

    case 'aggregation_result': {
      const sym = (d.symbol || '').replace('USDT', '');
      const action = d.action || '?';
      const conf = Math.round((d.confidence || 0) * 100);
      if (action === 'HOLD' || conf === 0) {
        return { icon: Scale, color: 'text-violet-400', message: `${sym} — no clear signal, teams are undecided` };
      }
      const direction = action === 'BUY' ? 'Buy' : action === 'SELL' || action === 'SHORT' ? 'Sell' : action;
      return { icon: Scale, color: 'text-violet-400', message: `Final signal for ${sym}: ${direction} (${conf}% confidence)` };
    }

    case 'risk_check':
      return {
        icon: Shield, color: 'text-orange-400',
        message: `${d.passed || 0} of ${d.total_signals || '?'} signals passed risk checks`,
      };

    case 'pm_review':
      return {
        icon: BarChart3, color: 'text-cyan-400',
        message: `Portfolio manager approved ${d.orders_after || 0} trades${d.orders_before !== d.orders_after ? ` (blocked ${(d.orders_before || 0) - (d.orders_after || 0)} for portfolio balance)` : ''}`,
      };

    case 'verdict': {
      const sym = (d.symbol || '').replace('USDT', '');
      if (d.blocked) {
        const reason = d.reason || 'risk rules';
        return { icon: XCircle, color: 'text-white/40', message: `${sym} blocked — ${reason}` };
      }
      return { icon: CheckCircle, color: 'text-emerald-400', message: `${sym} approved for trading — ${d.action}` };
    }

    case 'trade_executed': {
      const sym = (d.symbol || '').replace('USDT', '');
      const side = d.side === 'BUY' ? 'Bought' : 'Sold';
      return {
        icon: DollarSign, color: 'text-emerald-400',
        message: `${side} ${sym} at $${(d.price || 0).toLocaleString()}`,
      };
    }

    case 'trade_closed': {
      const sym = (d.symbol || '').replace('USDT', '');
      const pnl = d.pnl_pct || 0;
      const pnlStr = pnl > 0 ? `+${(pnl * 100).toFixed(1)}% profit` : `${(pnl * 100).toFixed(1)}% loss`;
      return {
        icon: LogOut, color: pnl > 0 ? 'text-emerald-400' : 'text-red-400',
        message: `Closed ${sym} — ${pnlStr} ($${(d.pnl_usd || 0) >= 0 ? '+' : ''}${(d.pnl_usd || 0).toFixed(0)})`,
      };
    }

    case 'ceo_review':
      return { icon: Brain, color: 'text-amber-400', message: 'CEO reviewed cycle performance and adjusted team weights' };

    default:
      return { icon: Activity, color: 'text-white/40', message: event.title };
  }
}

export default function ActivityFeed({
  maxItems = 15,
  compact = false,
}: {
  maxItems?: number;
  compact?: boolean;
}) {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const prevIdsRef = useRef<Set<string>>(new Set());
  const [newIds, setNewIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/events/live`);
        if (!res.ok) return;
        const data: PipelineEvent[] = await res.json();
        const sliced = data.slice(0, maxItems);

        const currentIdsList = sliced.map(e => e.id);
        const currentIds = new Set(currentIdsList);
        const freshIds = new Set<string>();
        currentIdsList.forEach(id => {
          if (!prevIdsRef.current.has(id)) {
            freshIds.add(id);
          }
        });
        prevIdsRef.current = currentIds;
        if (freshIds.size > 0) {
          setNewIds(freshIds);
          setTimeout(() => setNewIds(new Set()), 600);
        }

        setEvents(sliced);
      } catch {
        try {
          const res = await fetch(`${API_BASE}/data/latest_events.json`);
          if (res.ok) {
            const data = await res.json();
            setEvents((data.events || []).slice(0, maxItems));
          }
        } catch {}
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
    const interval = setInterval(fetchEvents, 5000);
    return () => clearInterval(interval);
  }, [maxItems]);

  if (loading && events.length === 0) {
    return (
      <div className="flex items-center gap-3 py-6 justify-center">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-hive-accent opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-hive-accent"></span>
        </span>
        <span className="text-xs text-hive-muted">Loading activity...</span>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="py-6 text-center">
        <p className="text-xs text-hive-muted">No activity yet. Events appear here when the pipeline runs — every 4 hours.</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-white/[0.03]">
      {events.map((event) => {
        const { icon: Icon, color, message } = humanize(event);
        const isNew = newIds.has(event.id);
        const time = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        return (
          <div
            key={event.id}
            className={`flex items-start gap-3 py-2.5 px-1 transition-all duration-300 ${isNew ? 'bg-white/[0.03] slide-up' : ''}`}
          >
            <span className="text-[10px] text-hive-muted/50 font-mono tabular-nums shrink-0 mt-0.5 w-16">
              {time}
            </span>
            <Icon size={14} className={`${color} shrink-0 mt-0.5`} />
            <span className="text-xs text-hive-text/90 break-words flex-1">{message}</span>
          </div>
        );
      })}
      {compact && (
        <div className="pt-3 pb-1">
          <a href="/activity" className="text-xs text-hive-accent hover:text-amber-300 transition-colors flex items-center gap-1">
            View all activity <ArrowRight size={12} />
          </a>
        </div>
      )}
    </div>
  );
}
