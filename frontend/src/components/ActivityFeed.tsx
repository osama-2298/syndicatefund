'use client';

import { useEffect, useState, useRef } from 'react';
import {
  Activity, ArrowRight, Play, Brain, Search, Target,
  Shield, Users, Scale, CheckCircle, XCircle, DollarSign,
  LogOut, Star, Swords, BarChart3,
} from 'lucide-react';
import { humanizeEvent } from '@/lib/humanize-event';
import { API_BASE } from '@/lib/api';

const ICON_MAP: Record<string, any> = {
  Play, Brain, Search, Target, Shield, Users, Scale,
  CheckCircle, XCircle, DollarSign, LogOut, Star, Swords,
  BarChart3, Activity,
};

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
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-syn-accent opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-syn-accent"></span>
        </span>
        <span className="text-xs text-syn-text-secondary">Loading activity...</span>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="py-6 text-center">
        <p className="text-xs text-syn-text-secondary">No activity yet. Events appear here when the pipeline runs — every 4 hours.</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-white/[0.03]">
      {events.map((event) => {
        const { icon: iconName, color, message } = humanizeEvent(event);
        const Icon = ICON_MAP[iconName] || Activity;
        const isNew = newIds.has(event.id);
        const time = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        return (
          <div
            key={event.id}
            className={`flex items-start gap-3 py-2.5 px-1 transition-all duration-300 ${isNew ? 'bg-white/[0.03] slide-up' : ''}`}
          >
            <span className="text-[10px] text-syn-text-secondary/50 font-mono tabular-nums shrink-0 mt-0.5 w-16">
              {time}
            </span>
            <Icon size={14} className={`${color} shrink-0 mt-0.5`} />
            <span className="text-xs text-syn-text/90 break-words flex-1">{message}</span>
          </div>
        );
      })}
      {compact && (
        <div className="pt-3 pb-1">
          <a href="/activity" className="text-xs text-syn-accent hover:text-violet-300 transition-colors flex items-center gap-1">
            View all activity <ArrowRight size={12} />
          </a>
        </div>
      )}
    </div>
  );
}
