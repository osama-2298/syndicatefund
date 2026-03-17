'use client';

import type { AgentComm } from '@/lib/types';
import { AGENT_NAMES, AGENT_COLORS, TEAM_COLORS, COMM_TYPE_CONFIG, EXECUTIVE_NAMES, getAgentInitial } from '@/lib/constants';
import { formatRelative } from '@/lib/format';

function getCommGradient(comm: AgentComm): string {
  const cls = comm.agent_class || '';
  if (AGENT_COLORS[cls]) return AGENT_COLORS[cls];
  const exec = EXECUTIVE_NAMES[cls];
  if (exec) return exec.gradient;
  // Manager — resolve from team
  if (cls.startsWith('manager_')) {
    const team = cls.replace('manager_', '');
    return TEAM_COLORS[team] || 'from-violet-500 to-purple-500';
  }
  // Agent from team (contributor agents)
  if (comm.team && TEAM_COLORS[comm.team]) return TEAM_COLORS[comm.team];
  return 'from-violet-500 to-purple-500';
}

function getInitials(comm: AgentComm): string {
  const cls = comm.agent_class || '';
  // Executives
  if (['CEO', 'COO', 'CRO'].includes(cls)) return cls;
  if (cls === 'Aggregator') return 'AG';
  if (cls === 'Execution') return 'EX';
  // Agents
  if (AGENT_NAMES[cls]) return getAgentInitial(cls, cls);
  // Managers
  if (cls.startsWith('manager_')) {
    const team = cls.replace('manager_', '');
    return team.slice(0, 2).toUpperCase();
  }
  return comm.agent_name.slice(0, 2).toUpperCase();
}

function getTitle(comm: AgentComm): string {
  const cls = comm.agent_class || '';
  const exec = EXECUTIVE_NAMES[cls];
  if (exec) return exec.title;
  if (comm.metadata?.title) return comm.metadata.title;
  if (cls.startsWith('manager_')) {
    const team = cls.replace('manager_', '');
    return `${team.charAt(0).toUpperCase() + team.slice(1)} Team Manager`;
  }
  return comm.comm_type.replace(/_/g, ' ');
}

export default function CommCard({ comm }: { comm: AgentComm }) {
  const gradient = getCommGradient(comm);
  const initials = getInitials(comm);
  const title = getTitle(comm);
  const typeConfig = COMM_TYPE_CONFIG[comm.comm_type] || { label: comm.comm_type.toUpperCase(), color: 'text-syn-muted bg-syn-surface ring-syn-border' };
  const confidence = comm.metadata?.confidence;

  return (
    <div className="bg-syn-surface border border-syn-border rounded-xl p-4 sm:p-5 hover:border-syn-border-hover transition-colors">
      {/* Header */}
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center flex-shrink-0`}>
          <span className="text-xs font-bold text-white">{initials}</span>
        </div>

        <div className="flex-1 min-w-0">
          {/* Name + title row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-syn-text">{comm.agent_name}</span>
            <span className="text-xs text-syn-text-tertiary">{title}</span>
          </div>

          {/* Badges row */}
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {/* Comm type badge */}
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 ${typeConfig.color}`}>
              {typeConfig.label}
            </span>

            {/* Direction pill */}
            {comm.direction && !['coo_selection', 'cro_rules'].includes(comm.comm_type) && (
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 ${
                ['BULLISH', 'BUY', 'LONG', 'bull'].includes(comm.direction)
                  ? 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20'
                  : ['BEARISH', 'SELL', 'SHORT', 'bear'].includes(comm.direction)
                  ? 'text-red-400 bg-red-400/10 ring-red-400/20'
                  : 'text-syn-muted bg-syn-surface ring-syn-border'
              }`}>
                {comm.direction}
              </span>
            )}

            {/* Conviction */}
            {comm.conviction !== null && comm.conviction !== undefined && (
              <span className="text-[10px] text-syn-text-tertiary font-mono">{comm.conviction}/10</span>
            )}

            {/* Symbol */}
            {comm.symbol && (
              <span className="text-[10px] text-syn-text-secondary font-mono">{comm.symbol.replace('USDT', '')}</span>
            )}

            {/* Timestamp */}
            {comm.created_at && (
              <span className="text-[10px] text-syn-text-tertiary ml-auto">{formatRelative(comm.created_at)}</span>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <p className="text-sm text-syn-text-secondary mt-3 leading-relaxed whitespace-pre-line">{comm.content}</p>

      {/* Metadata pills */}
      {(confidence !== undefined || comm.metadata?.price) && (
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {confidence !== undefined && (
            <div className="flex items-center gap-1.5">
              <div className="w-16 h-1.5 bg-syn-bg rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-syn-accent to-violet-400 rounded-full"
                  style={{ width: `${Math.round(confidence * 100)}%` }}
                />
              </div>
              <span className="text-[10px] text-syn-text-tertiary font-mono">{Math.round(confidence * 100)}%</span>
            </div>
          )}
          {comm.metadata?.price ? (
            <span className="text-[10px] text-syn-text-tertiary font-mono">${Number(comm.metadata.price).toLocaleString()}</span>
          ) : null}
        </div>
      )}
    </div>
  );
}
