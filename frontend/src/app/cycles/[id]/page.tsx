'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import {
  Activity, ArrowLeft, Play, Pause, SkipBack, SkipForward, FastForward,
  Search, Brain, Target, Shield, Users, Scale, CheckCircle, XCircle,
  DollarSign, LogOut, Star, Swords, BarChart3,
} from 'lucide-react';
import { humanizeEvent } from '@/lib/humanize-event';
import { API_BASE } from '@/lib/api';

interface PipelineEvent {
  id: string;
  event_type: string;
  timestamp: string;
  stage: string;
  actor: string;
  title: string;
  detail: Record<string, any> | null;
  elapsed_ms: number | null;
}

const ICON_MAP: Record<string, typeof Play> = {
  Play, Search, Brain, Target, Shield, Users, Scale, CheckCircle, XCircle,
  DollarSign, LogOut, Star, Swords, BarChart3, Activity, Pause,
};

const STAGES = ['intelligence', 'ceo', 'coin_selection', 'agent_analysis', 'aggregation', 'risk', 'execution', 'review', 'complete'];
const STAGE_DISPLAY = ['Market Data', 'CEO Strategy', 'Coin Selection', 'Team Analysis', 'Signal Aggregation', 'Risk Check', 'Execution', 'Review', 'Done'];

const SPEEDS = [1, 2, 5];

export default function CycleReplayPage() {
  const params = useParams();
  const cycleId = params.id as string;

  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [visibleCount, setVisibleCount] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/events?cycle_id=${cycleId}&limit=200`)
      .then(r => r.json())
      .then(data => {
        const arr = Array.isArray(data) ? data.reverse() : [];
        setEvents(arr);
        // Auto-play on load
        if (arr.length > 0) {
          setPlaying(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [cycleId]);

  const advance = useCallback(() => {
    setVisibleCount(prev => {
      if (prev >= events.length) {
        setPlaying(false);
        return prev;
      }
      return prev + 1;
    });
  }, [events.length]);

  useEffect(() => {
    if (playing && events.length > 0) {
      const delay = 1000 / speed;
      intervalRef.current = setInterval(advance, delay);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, advance, events.length]);

  const handlePlay = () => {
    if (visibleCount >= events.length) setVisibleCount(0);
    setPlaying(true);
  };
  const handlePause = () => setPlaying(false);
  const handleBack = () => { setPlaying(false); setVisibleCount(prev => Math.max(0, prev - 1)); };
  const handleForward = () => { setPlaying(false); advance(); };

  const currentStage = visibleCount > 0 ? events[visibleCount - 1]?.stage || '' : '';
  const stageIndex = STAGES.indexOf(currentStage);
  const progressPct = events.length > 0 ? (visibleCount / events.length) * 100 : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Activity size={24} className="animate-spin text-syn-accent" />
      </div>
    );
  }

  return (
    <div className="slide-up space-y-6">
      <a href="/activity" className="inline-flex items-center gap-1 text-xs text-syn-muted hover:text-syn-text transition-colors">
        <ArrowLeft size={12} /> Back to Activity
      </a>

      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Cycle #{cycleId} Replay</h1>
        <p className="text-xs sm:text-sm text-syn-muted mt-1">{events.length} steps — watch the AI analyze markets, debate, and trade</p>
      </div>

      {/* Controls */}
      <div className="bg-syn-surface border border-syn-border rounded-lg p-3 sm:p-4">
        <div className="flex items-center gap-2 sm:gap-4">
          <div className="flex items-center gap-1 sm:gap-2 shrink-0">
            <button onClick={handleBack} className="p-1.5 sm:p-2 rounded-lg hover:bg-white/[0.04] transition-colors">
              <SkipBack size={14} className="sm:w-4 sm:h-4" />
            </button>
            {playing ? (
              <button onClick={handlePause} className="p-1.5 sm:p-2 rounded-lg bg-syn-accent/10 text-syn-accent hover:bg-syn-accent/20 transition-colors">
                <Pause size={14} className="sm:w-4 sm:h-4" />
              </button>
            ) : (
              <button onClick={handlePlay} className="p-1.5 sm:p-2 rounded-lg bg-syn-accent/10 text-syn-accent hover:bg-syn-accent/20 transition-colors">
                <Play size={14} className="sm:w-4 sm:h-4" />
              </button>
            )}
            <button onClick={handleForward} className="p-1.5 sm:p-2 rounded-lg hover:bg-white/[0.04] transition-colors">
              <SkipForward size={14} className="sm:w-4 sm:h-4" />
            </button>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <FastForward size={12} className="text-syn-muted hidden sm:block" />
            {SPEEDS.map(s => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`text-[10px] font-bold px-1.5 sm:px-2 py-0.5 rounded ${speed === s ? 'bg-syn-accent/10 text-syn-accent' : 'text-syn-muted hover:text-syn-text'}`}
              >
                {s}x
              </button>
            ))}
          </div>

          <div className="flex-1 min-w-0">
            <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
              <div className="h-full bg-syn-accent rounded-full transition-all duration-300" style={{ width: `${progressPct}%` }} />
            </div>
          </div>

          <span className="text-[10px] sm:text-xs text-syn-muted tabular-nums shrink-0">{visibleCount}/{events.length}</span>
        </div>

        {/* Stage indicators with labels */}
        <div className="flex items-center gap-0.5 sm:gap-1 mt-3">
          {STAGES.map((stage, i) => (
            <div
              key={stage}
              className={`flex-1 h-1 rounded-full transition-colors ${i <= stageIndex ? 'bg-syn-accent' : 'bg-white/[0.04]'}`}
              title={STAGE_DISPLAY[i]}
            />
          ))}
        </div>
        <div className="hidden sm:flex justify-between mt-1">
          {STAGE_DISPLAY.filter((_, i) => i % 2 === 0 || i === STAGE_DISPLAY.length - 1).map(label => (
            <span key={label} className="text-[10px] text-syn-muted">{label}</span>
          ))}
        </div>
      </div>

      {/* Event list */}
      <div className="bg-syn-surface border border-syn-border rounded-lg p-3 sm:p-5">
        {events.length === 0 ? (
          <div className="text-center py-10">
            <p className="text-sm text-syn-muted">No events found for this cycle</p>
          </div>
        ) : visibleCount === 0 ? (
          <div className="text-center py-10">
            <div className="animate-spin w-5 h-5 border-2 border-syn-accent border-t-transparent rounded-full mx-auto" />
          </div>
        ) : (
          <div className="space-y-0 divide-y divide-white/[0.03]">
            {events.slice(0, visibleCount).map((event, i) => {
              const { icon: iconName, color, message } = humanizeEvent(event);
              const Icon = ICON_MAP[iconName] || Activity;
              const time = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
              const isLatest = i === visibleCount - 1;

              return (
                <div
                  key={event.id}
                  className={`flex items-start gap-2 sm:gap-3 py-2 sm:py-2.5 transition-all ${isLatest ? 'bg-white/[0.03] slide-up' : ''}`}
                >
                  <span className="text-[9px] sm:text-[10px] text-syn-muted/50 font-mono tabular-nums shrink-0 mt-0.5 w-[3.2rem] sm:w-16">{time}</span>
                  <Icon size={14} className={`${color} shrink-0 mt-0.5`} />
                  <span className="text-[11px] sm:text-xs text-syn-text/90 break-words min-w-0 flex-1">{message}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
