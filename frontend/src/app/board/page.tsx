'use client';

import { useEffect, useState } from 'react';
import { Activity, Gavel, Skull, AlertTriangle, UserPlus, Users, ChevronDown, ChevronRight } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface BoardDecision {
  id: string;
  decision_type: string;
  agent_id: string | null;
  team_id: string | null;
  reasoning: string | null;
  decided_by: string;
  created_at: string;
}

interface BoardSession {
  session_id: string;
  decisions: BoardDecision[];
  created_at: string;
}

const DECISION_STYLES: Record<string, { icon: typeof Skull; color: string; label: string; bg: string }> = {
  agent_fire: { icon: Skull, color: 'text-red-400', label: 'FIRED', bg: 'bg-red-500/10 ring-red-500/20' },
  agent_probation: { icon: AlertTriangle, color: 'text-amber-400', label: 'PROBATION', bg: 'bg-amber-500/10 ring-amber-500/20' },
  agent_assigned: { icon: UserPlus, color: 'text-blue-400', label: 'ASSIGNED', bg: 'bg-blue-500/10 ring-blue-500/20' },
  team_created: { icon: Users, color: 'text-emerald-400', label: 'NEW TEAM', bg: 'bg-emerald-500/10 ring-emerald-500/20' },
};

export default function BoardPage() {
  const [sessions, setSessions] = useState<BoardSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/board/sessions?limit=20`)
      .then(r => r.json())
      .then(data => {
        const arr = Array.isArray(data) ? data : [];
        setSessions(arr);
        // Auto-expand first session
        if (arr.length > 0) setExpanded(new Set([arr[0].session_id]));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const toggleSession = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

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
        <h1 className="text-2xl font-bold tracking-tight">Board Room</h1>
        <p className="text-sm text-hive-muted mt-1">
          Governance decisions — agent firings, promotions, team restructuring.
        </p>
      </div>

      {sessions.length === 0 ? (
        <div className="glass-card p-10 text-center">
          <Gavel size={32} className="mx-auto text-white/10 mb-3" />
          <p className="text-sm text-hive-muted">No board sessions recorded yet</p>
          <p className="text-xs text-hive-muted/50 mt-1">Board sessions occur after cycles to evaluate agent performance</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => {
            const isOpen = expanded.has(session.session_id);
            const time = new Date(session.created_at).toLocaleString();
            const fires = session.decisions.filter(d => d.decision_type === 'agent_fire').length;
            const probations = session.decisions.filter(d => d.decision_type === 'agent_probation').length;

            return (
              <div key={session.session_id} className="glass-card overflow-hidden">
                <button
                  onClick={() => toggleSession(session.session_id)}
                  className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {isOpen ? <ChevronDown size={14} className="text-hive-muted" /> : <ChevronRight size={14} className="text-hive-muted" />}
                    <span className="text-sm font-semibold">Board Session</span>
                    <span className="text-[10px] text-hive-muted">{time}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-hive-muted">{session.decisions.length} decisions</span>
                    {fires > 0 && (
                      <span className="text-[10px] font-bold text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded ring-1 ring-inset ring-red-500/20">
                        {fires} fired
                      </span>
                    )}
                    {probations > 0 && (
                      <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded ring-1 ring-inset ring-amber-500/20">
                        {probations} probation
                      </span>
                    )}
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-white/[0.06] divide-y divide-white/[0.03]">
                    {session.decisions.map((decision) => {
                      const style = DECISION_STYLES[decision.decision_type] || {
                        icon: Gavel, color: 'text-hive-muted', label: decision.decision_type.toUpperCase(), bg: 'bg-white/[0.04] ring-white/[0.06]',
                      };
                      const Icon = style.icon;

                      return (
                        <div key={decision.id} className="px-5 py-3 flex items-start gap-3">
                          <Icon size={16} className={`${style.color} mt-0.5 shrink-0`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ring-1 ring-inset ${style.bg}`}>
                                {style.label}
                              </span>
                              <span className="text-[10px] text-hive-muted">by {decision.decided_by}</span>
                            </div>
                            {decision.reasoning && (
                              <p className="text-xs text-hive-text/70">{decision.reasoning}</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
