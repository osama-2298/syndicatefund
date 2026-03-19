'use client';

import type { AgentComm } from '@/lib/types';
import Avatar from 'boring-avatars';
import { AGENT_COLORS, TEAM_COLORS, COMM_TYPE_CONFIG, EXECUTIVE_NAMES, getAgentInitial, getPersona, DEFAULT_AVATAR_COLORS } from '@/lib/constants';
import { formatRelative } from '@/lib/format';

/* ------------------------------------------------------------------ */
/*  HELPERS                                                            */
/* ------------------------------------------------------------------ */

function getGradient(comm: AgentComm): string {
  const cls = comm.agent_class || '';
  if (AGENT_COLORS[cls]) return AGENT_COLORS[cls];
  const exec = EXECUTIVE_NAMES[cls];
  if (exec) return exec.gradient;
  if (cls.startsWith('manager_')) {
    const team = cls.replace('manager_', '');
    return TEAM_COLORS[team] || 'from-violet-500 to-purple-500';
  }
  if (comm.team && TEAM_COLORS[comm.team]) return TEAM_COLORS[comm.team];
  return 'from-violet-500 to-purple-500';
}

function getInitials(comm: AgentComm): string {
  const cls = comm.agent_class || '';
  if (['CEO', 'COO', 'CRO'].includes(cls)) return cls;
  if (cls === 'Aggregator') return 'AG';
  if (cls === 'Execution') return 'EX';
  if (AGENT_COLORS[cls]) return getAgentInitial(cls, cls);
  if (cls.startsWith('manager_')) {
    const team = cls.replace('manager_', '');
    return team.slice(0, 2).toUpperCase();
  }
  return (comm.agent_name || '??').slice(0, 2).toUpperCase();
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

function isBullish(dir: string | null): boolean {
  if (!dir) return false;
  const d = dir.toUpperCase();
  return ['BULLISH', 'BUY', 'LONG', 'BULL'].includes(d);
}

function isBearish(dir: string | null): boolean {
  if (!dir) return false;
  const d = dir.toUpperCase();
  return ['BEARISH', 'SELL', 'SHORT', 'BEAR'].includes(d);
}

/* ------------------------------------------------------------------ */
/*  EXECUTIVE CARD — CEO Directive / COO Selection / CRO Rules        */
/* ------------------------------------------------------------------ */

function ExecutiveCard({ comm }: { comm: AgentComm }) {
  const gradient = getGradient(comm);
  const title = getTitle(comm);
  const typeConfig = COMM_TYPE_CONFIG[comm.comm_type];
  const meta = comm.metadata || {};
  const persona = getPersona(comm.agent_name);

  return (
    <div className="group relative bg-syn-surface border border-syn-border rounded-xl overflow-hidden hover:border-syn-border-hover transition-all duration-300">
      {/* Top accent bar */}
      <div className={`h-0.5 bg-gradient-to-r ${gradient}`} />

      <div className="p-4 sm:p-5">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 shadow-lg ring-1 ring-white/[0.06]">
            <Avatar name={comm.agent_name} variant="beam" size={40} colors={persona.colors} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-white">{comm.agent_name}</span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 ${typeConfig?.color || 'text-syn-muted bg-syn-surface ring-syn-border'}`}>
                {typeConfig?.label || comm.comm_type}
              </span>
            </div>
            <span className="text-[11px] text-syn-text-tertiary">{title}</span>
          </div>
          {comm.created_at && (
            <span className="text-[10px] text-syn-text-tertiary whitespace-nowrap">{formatRelative(comm.created_at)}</span>
          )}
        </div>

        {/* Content */}
        <p className="text-sm text-syn-text-secondary mt-3 leading-relaxed">{comm.content}</p>

        {/* Metadata pills for executives */}
        {comm.comm_type === 'ceo_directive' && (
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {meta.regime && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                meta.regime.toLowerCase().includes('bull') ? 'text-emerald-400 bg-emerald-400/10' :
                meta.regime.toLowerCase().includes('bear') ? 'text-red-400 bg-red-400/10' :
                meta.regime.toLowerCase().includes('crisis') ? 'text-red-300 bg-red-900/20' :
                'text-amber-400 bg-amber-400/10'
              }`}>
                {String(meta.regime).toUpperCase()}
              </span>
            )}
            {meta.risk_multiplier != null && (
              <span className="text-[10px] font-mono text-syn-text-tertiary bg-syn-bg px-2 py-0.5 rounded-full">
                Risk {meta.risk_multiplier}x
              </span>
            )}
          </div>
        )}
        {comm.comm_type === 'coo_selection' && meta.selected_coins && (
          <div className="flex items-center gap-1.5 mt-3 flex-wrap">
            {(meta.selected_coins as string[]).map((c: string) => (
              <span key={c} className="text-[10px] font-mono font-semibold text-cyan-400 bg-cyan-400/10 px-2 py-0.5 rounded-full">
                {c.replace('USDT', '')}
              </span>
            ))}
          </div>
        )}
        {comm.comm_type === 'cro_rules' && (
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {meta.max_position_pct != null && (
              <span className="text-[10px] font-mono text-red-400/80 bg-red-400/5 px-2 py-0.5 rounded-full">
                Max pos {(meta.max_position_pct * 100).toFixed(0)}%
              </span>
            )}
            {meta.max_open_positions != null && (
              <span className="text-[10px] font-mono text-red-400/80 bg-red-400/5 px-2 py-0.5 rounded-full">
                Max {meta.max_open_positions} open
              </span>
            )}
            {meta.min_signal_confidence != null && (
              <span className="text-[10px] font-mono text-red-400/80 bg-red-400/5 px-2 py-0.5 rounded-full">
                Min conf {(meta.min_signal_confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  SIGNAL CARD — Agent signals + Manager synthesis                    */
/* ------------------------------------------------------------------ */

function SignalCard({ comm }: { comm: AgentComm }) {
  const typeConfig = COMM_TYPE_CONFIG[comm.comm_type];
  const confidence = comm.metadata?.confidence;
  const isManager = comm.comm_type === 'manager_synthesis';
  const persona = getPersona(comm.agent_name);

  return (
    <div className={`group bg-syn-surface border rounded-lg overflow-hidden hover:border-syn-border-hover transition-all duration-200 ${
      isManager ? 'border-syn-border' : 'border-syn-border/60'
    }`}>
      <div className={`px-3.5 py-3 ${isManager ? 'sm:px-4 sm:py-3.5' : ''}`}>
        {/* Compact header */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md overflow-hidden flex-shrink-0 ring-1 ring-white/[0.04]">
            <Avatar name={comm.agent_name} variant="beam" size={28} colors={persona.colors} />
          </div>

          <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
            <span className={`font-semibold text-syn-text ${isManager ? 'text-sm' : 'text-[13px]'}`}>{comm.agent_name}</span>
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 ${typeConfig?.color || ''}`}>
              {typeConfig?.label || 'SIGNAL'}
            </span>
          </div>

          {/* Direction + conviction cluster */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {comm.direction && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                isBullish(comm.direction) ? 'text-emerald-400 bg-emerald-400/10' :
                isBearish(comm.direction) ? 'text-red-400 bg-red-400/10' :
                'text-syn-text-tertiary bg-syn-bg'
              }`}>
                {comm.direction}
              </span>
            )}
            {comm.conviction != null && (
              <div className="flex items-center gap-1">
                <div className="flex gap-px">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-1 h-3 rounded-full transition-colors ${
                        i < comm.conviction!
                          ? isBullish(comm.direction) ? 'bg-emerald-400' : isBearish(comm.direction) ? 'bg-red-400' : 'bg-syn-accent'
                          : 'bg-syn-border'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-[10px] font-mono text-syn-text-tertiary">{comm.conviction}</span>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <p className="text-[13px] text-syn-text-secondary mt-2 leading-relaxed whitespace-pre-line line-clamp-4">{comm.content}</p>

        {/* Confidence bar */}
        {confidence != null && (
          <div className="flex items-center gap-2 mt-2">
            <div className="flex-1 h-1 bg-syn-bg rounded-full overflow-hidden max-w-[120px]">
              <div
                className={`h-full rounded-full ${
                  isBullish(comm.direction) ? 'bg-emerald-400/70' : isBearish(comm.direction) ? 'bg-red-400/70' : 'bg-syn-accent/70'
                }`}
                style={{ width: `${Math.round(confidence * 100)}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-syn-text-tertiary">{Math.round(confidence * 100)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  AGGREGATION CARD                                                   */
/* ------------------------------------------------------------------ */

function AggregationCard({ comm }: { comm: AgentComm }) {
  const meta = comm.metadata || {};
  const confidence = meta.confidence;
  const consensus = meta.consensus;
  const teamScores = meta.team_scores || {};
  const quality = meta.decision_quality;
  const symbol = comm.symbol?.replace('USDT', '') || '?';

  return (
    <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden hover:border-syn-border-hover transition-all duration-200">
      <div className="px-3.5 py-3 sm:px-4">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md overflow-hidden flex-shrink-0 ring-1 ring-white/[0.04]">
              <Avatar name="Soren Lindqvist" variant="beam" size={28} colors={getPersona('Soren Lindqvist').colors} />
            </div>
            <span className="text-sm font-semibold text-white font-mono">{symbol}</span>
            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 text-emerald-400 bg-emerald-400/10 ring-emerald-400/20">
              AGGREGATION
            </span>
          </div>
          {comm.direction && (
            <span className={`text-xs font-bold px-2.5 py-1 rounded-md ${
              isBullish(comm.direction) ? 'text-emerald-400 bg-emerald-400/10' :
              isBearish(comm.direction) ? 'text-red-400 bg-red-400/10' :
              'text-amber-400 bg-amber-400/10'
            }`}>
              {comm.direction}
            </span>
          )}
        </div>

        {/* Metrics row */}
        <div className="grid grid-cols-3 gap-3 mt-3">
          {confidence != null && (
            <div>
              <p className="text-[9px] font-bold uppercase tracking-wider text-syn-muted">Confidence</p>
              <p className="text-sm font-bold font-mono text-white">{Math.round(confidence * 100)}%</p>
            </div>
          )}
          {consensus != null && (
            <div>
              <p className="text-[9px] font-bold uppercase tracking-wider text-syn-muted">Consensus</p>
              <p className="text-sm font-bold font-mono text-white">{Math.round(consensus * 100)}%</p>
            </div>
          )}
          {quality && (
            <div>
              <p className="text-[9px] font-bold uppercase tracking-wider text-syn-muted">Quality</p>
              <p className={`text-sm font-bold font-mono ${
                quality === 'HIGH' ? 'text-emerald-400' : quality === 'MEDIUM' ? 'text-amber-400' : 'text-red-400'
              }`}>{quality}</p>
            </div>
          )}
        </div>

        {/* Team scores */}
        {Object.keys(teamScores).length > 0 && (
          <div className="flex items-center gap-1.5 mt-3 flex-wrap">
            {Object.entries(teamScores).map(([team, score]) => (
              <span key={team} className="text-[10px] font-mono text-syn-text-tertiary bg-syn-bg px-2 py-0.5 rounded-full">
                {team}: {typeof score === 'number' ? score.toFixed(2) : String(score)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  TRADE CARD                                                         */
/* ------------------------------------------------------------------ */

function TradeCard({ comm }: { comm: AgentComm }) {
  const meta = comm.metadata || {};
  const symbol = comm.symbol?.replace('USDT', '') || '?';
  const side = meta.side || comm.direction || '';
  const price = meta.price;
  const sl = meta.stop_loss;
  const tp = meta.take_profit_1;
  const isBuy = side.toUpperCase() === 'BUY';

  return (
    <div className={`bg-syn-surface border rounded-lg overflow-hidden hover:border-syn-border-hover transition-all duration-200 ${
      isBuy ? 'border-emerald-500/20' : 'border-red-500/20'
    }`}>
      <div className="px-3.5 py-3 sm:px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-md flex items-center justify-center ${
              isBuy ? 'bg-emerald-500/20' : 'bg-red-500/20'
            }`}>
              <span className={`text-sm font-bold ${isBuy ? 'text-emerald-400' : 'text-red-400'}`}>
                {isBuy ? '\u2191' : '\u2193'}
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold font-mono text-white">{symbol}</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  isBuy ? 'text-emerald-400 bg-emerald-400/10' : 'text-red-400 bg-red-400/10'
                }`}>
                  {side.toUpperCase()}
                </span>
              </div>
            </div>
          </div>
          {price > 0 && (
            <span className="text-sm font-bold font-mono text-white">${Number(price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          )}
        </div>

        {/* SL/TP */}
        {(sl > 0 || tp > 0) && (
          <div className="flex items-center gap-4 mt-2">
            {sl > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="text-[9px] font-bold uppercase tracking-wider text-red-400/70">SL</span>
                <span className="text-[11px] font-mono text-syn-text-secondary">${Number(sl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            )}
            {tp > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-400/70">TP</span>
                <span className="text-[11px] font-mono text-syn-text-secondary">${Number(tp).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  CEO REVIEW CARD                                                    */
/* ------------------------------------------------------------------ */

function ReviewCard({ comm }: { comm: AgentComm }) {
  const meta = comm.metadata || {};
  const grade = meta.grade;
  const persona = getPersona(comm.agent_name);

  return (
    <div className="group relative bg-syn-surface border border-syn-border rounded-xl overflow-hidden hover:border-syn-border-hover transition-all duration-300">
      <div className="h-0.5 bg-gradient-to-r from-violet-500 to-purple-500" />
      <div className="p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 shadow-lg ring-1 ring-white/[0.06]">
            <Avatar name={comm.agent_name} variant="beam" size={40} colors={persona.colors} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">{comm.agent_name}</span>
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 text-violet-400 bg-violet-400/10 ring-violet-400/20">
                CEO REVIEW
              </span>
            </div>
            <span className="text-[11px] text-syn-text-tertiary">Post-Cycle Assessment</span>
          </div>
          {grade && (
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg ${
              grade.startsWith('A') ? 'bg-emerald-400/10 text-emerald-400' :
              grade.startsWith('B') ? 'bg-blue-400/10 text-blue-400' :
              grade.startsWith('C') ? 'bg-amber-400/10 text-amber-400' :
              'bg-red-400/10 text-red-400'
            }`}>
              {grade}
            </div>
          )}
        </div>
        <p className="text-sm text-syn-text-secondary mt-3 leading-relaxed whitespace-pre-line">{comm.content}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN EXPORT — dispatches to specialized card                       */
/* ------------------------------------------------------------------ */

export default function CommCard({ comm }: { comm: AgentComm }) {
  switch (comm.comm_type) {
    case 'ceo_directive':
    case 'coo_selection':
    case 'cro_rules':
      return <ExecutiveCard comm={comm} />;
    case 'agent_signal':
    case 'manager_synthesis':
      return <SignalCard comm={comm} />;
    case 'aggregation':
      return <AggregationCard comm={comm} />;
    case 'trade_execution':
      return <TradeCard comm={comm} />;
    case 'ceo_review':
      return <ReviewCard comm={comm} />;
    default:
      return <SignalCard comm={comm} />;
  }
}
