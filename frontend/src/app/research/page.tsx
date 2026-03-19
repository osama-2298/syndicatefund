'use client';

import { useEffect, useState } from 'react';
import {
  Loader2,
  Clock,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  Beaker,
  Shield,
  Zap,
  Target,
  Eye,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';
import { researcherConfig, reportTypeConfig } from '@/lib/constants';
import { formatTimestamp, formatRelative } from '@/lib/format';

/* ------------------------------------------------------------------ */
/*  TYPES                                                              */
/* ------------------------------------------------------------------ */

interface Finding {
  severity?: string;
  label?: string;
  detail?: string;
  [key: string]: any;
}

interface DataContext {
  period?: string;
  sample_size?: string | number;
  [key: string]: any;
}

interface ResearchReport {
  id: string;
  researcher: string;
  report_type: string;
  title: string;
  summary: string;
  findings: Finding[] | Record<string, any> | null;
  recommendations: string[] | any[] | null;
  data_context: DataContext | null;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  FILTER TABS                                                         */
/* ------------------------------------------------------------------ */

interface FilterTab {
  key: string | null;
  label: string;
  types: string[];
}

const filterTabs: FilterTab[] = [
  { key: null, label: 'All', types: [] },
  { key: 'signal_health', label: 'Signal Health', types: ['signal_decay', 'risk_analysis'] },
  { key: 'attribution', label: 'Attribution', types: ['performance_attribution', 'hypothesis_test'] },
  { key: 'data_sources', label: 'Data Sources', types: ['data_source_eval', 'correlation_analysis'] },
  { key: 'weekly', label: 'Weekly Digest', types: ['weekly_digest'] },
];

/* ------------------------------------------------------------------ */
/*  HELPERS                                                             */
/* ------------------------------------------------------------------ */

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'text-red-400';
    case 'important':
    case 'warning':
      return 'text-amber-400';
    default:
      return 'text-white/50';
  }
}

function severityBg(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-500/10 border-red-500/20';
    case 'important':
    case 'warning':
      return 'bg-amber-500/10 border-amber-500/20';
    default:
      return 'bg-white/[0.02] border-white/[0.06]';
  }
}

function severityDot(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-400';
    case 'important':
    case 'warning':
      return 'bg-amber-400';
    default:
      return 'bg-white/40';
  }
}

function healthColor(health: string): string {
  switch (health) {
    case 'healthy':
      return 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20';
    case 'degrading':
      return 'text-amber-400 bg-amber-400/10 ring-amber-400/20';
    case 'critical':
      return 'text-red-400 bg-red-400/10 ring-red-400/20';
    default:
      return 'text-white/60 bg-white/5 ring-white/10';
  }
}

function isFindingsArray(findings: any): findings is Finding[] {
  return Array.isArray(findings);
}

function hasCriticalFinding(report: ResearchReport): boolean {
  if (!report.findings) return false;
  if (isFindingsArray(report.findings)) {
    return report.findings.some((f) => f.severity === 'critical');
  }
  // Check object findings for critical markers
  const f = report.findings as Record<string, any>;
  if (f.overall_health === 'critical') return true;
  if (Array.isArray(f.critical_alerts) && f.critical_alerts.length > 0) return true;
  if (Array.isArray(f.agents_flagged)) {
    return f.agents_flagged.some((a: any) => a.severity === 'critical');
  }
  if (Array.isArray(f.key_findings)) {
    return f.key_findings.some((kf: any) => kf.severity === 'critical');
  }
  return false;
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/* ------------------------------------------------------------------ */
/*  EXPANDABLE TEXT                                                     */
/* ------------------------------------------------------------------ */

function ExpandableText({ text, maxLength = 280 }: { text: string; maxLength?: number }) {
  const [expanded, setExpanded] = useState(false);
  if (text.length <= maxLength) {
    return <span>{text}</span>;
  }
  return (
    <span>
      {expanded ? text : text.slice(0, maxLength) + '...'}
      <button
        onClick={() => setExpanded(!expanded)}
        className="ml-1.5 text-syn-accent hover:text-syn-accent/80 text-xs font-medium transition-colors"
      >
        {expanded ? 'Show less' : 'Read more'}
      </button>
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  COLLAPSIBLE SECTION                                                 */
/* ------------------------------------------------------------------ */

function CollapsibleSection({
  title,
  icon: Icon,
  defaultOpen = true,
  count,
  children,
}: {
  title: string;
  icon?: any;
  defaultOpen?: boolean;
  count?: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mt-5">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left group"
      >
        {Icon && <Icon size={13} className="text-syn-text-tertiary" />}
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted group-hover:text-syn-text-secondary transition-colors">
          {title}
        </span>
        {count !== undefined && (
          <span className="text-[10px] font-mono text-syn-text-tertiary bg-white/[0.04] px-1.5 py-0.5 rounded">
            {count}
          </span>
        )}
        <div className="flex-1" />
        {open ? (
          <ChevronUp size={12} className="text-syn-text-tertiary" />
        ) : (
          <ChevronDown size={12} className="text-syn-text-tertiary" />
        )}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  SUB-COMPONENTS                                                      */
/* ------------------------------------------------------------------ */

function ResearcherAvatar({ researcher }: { researcher: string }) {
  const config = researcherConfig[researcher];
  if (!config) return null;
  return (
    <div
      className={`w-10 h-10 rounded-full bg-gradient-to-br ${config.gradient} flex items-center justify-center flex-shrink-0`}
    >
      <span className="text-sm font-bold text-white">{config.initial}</span>
    </div>
  );
}

function CriticalAlerts({ reports }: { reports: ResearchReport[] }) {
  const critical = reports.filter(hasCriticalFinding);
  if (critical.length === 0) return null;

  return (
    <div className="mb-8 space-y-3">
      <div className="flex items-center gap-2">
        <AlertTriangle size={14} className="text-red-400" />
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-red-400/80">
          Critical Alerts
        </p>
      </div>
      {critical.map((report) => {
        const config = researcherConfig[report.researcher];
        const alerts: string[] = [];

        if (isFindingsArray(report.findings)) {
          report.findings
            .filter((f) => f.severity === 'critical')
            .forEach((f) => alerts.push(f.label || f.detail || JSON.stringify(f)));
        } else if (report.findings) {
          const f = report.findings as Record<string, any>;
          if (Array.isArray(f.critical_alerts)) {
            alerts.push(...f.critical_alerts);
          }
          if (Array.isArray(f.agents_flagged)) {
            f.agents_flagged
              .filter((a: any) => a.severity === 'critical')
              .forEach((a: any) => alerts.push(a.issue || a.evidence || ''));
          }
          if (Array.isArray(f.key_findings)) {
            f.key_findings
              .filter((kf: any) => kf.severity === 'critical')
              .forEach((kf: any) => alerts.push(kf.finding || kf.evidence || ''));
          }
        }

        return (
          <div
            key={`alert-${report.id}`}
            className="bg-red-500/[0.06] border border-red-500/20 rounded-xl p-4"
          >
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-red-400 mt-1.5 flex-shrink-0 animate-pulse" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <span className="text-sm font-bold text-white">{report.title}</span>
                  <span className="text-[10px] font-mono tabular-nums text-syn-text-tertiary">
                    {formatRelative(report.created_at)}
                  </span>
                </div>
                {alerts.map((alert, i) => (
                  <p key={i} className="text-sm text-red-400/80 leading-relaxed">
                    {alert}
                  </p>
                ))}
                {config && (
                  <p className="text-[10px] text-syn-text-tertiary mt-2 font-mono">
                    {config.name}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  SIGNAL HEALTH FINDINGS                                              */
/* ------------------------------------------------------------------ */

function SignalHealthFindings({ findings }: { findings: Record<string, any> }) {
  const health = findings.overall_health;
  const flagged = findings.agents_flagged || [];
  const clusters = findings.correlation_clusters || [];
  const metrics = findings.key_metrics;
  const decaySummary = findings.decay_summary;

  return (
    <>
      {/* Health status + key metrics */}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        {health && (
          <span
            className={`text-xs font-bold px-3 py-1 rounded-full ring-1 ring-inset ${healthColor(health)}`}
          >
            {health.toUpperCase()}
          </span>
        )}
        {metrics && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(metrics).map(([k, v]) => (
              <span
                key={k}
                className="text-[11px] font-mono tabular-nums text-syn-text-tertiary bg-white/[0.03] px-2.5 py-1 rounded-lg"
              >
                {formatKey(k)}: <span className="text-syn-text-secondary">{typeof v === 'number' ? (k === 'avg_accuracy' ? formatPercent(v) : String(v)) : String(v)}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {decaySummary && (
        <p className="mt-3 text-sm text-syn-text-secondary leading-relaxed">{decaySummary}</p>
      )}

      {/* Flagged agents */}
      {flagged.length > 0 && (
        <CollapsibleSection title="Flagged Agents" icon={AlertTriangle} count={flagged.length}>
          <div className="space-y-2">
            {flagged.map((agent: any, i: number) => (
              <div
                key={i}
                className={`rounded-lg border p-3 ${severityBg(agent.severity || 'informational')}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono font-semibold text-white">
                        {formatKey(agent.agent_id || agent.agent || 'Unknown')}
                      </span>
                      {agent.severity && (
                        <span
                          className={`text-[9px] font-bold uppercase ${severityColor(agent.severity)}`}
                        >
                          {agent.severity}
                        </span>
                      )}
                    </div>
                    {agent.issue && (
                      <p className="text-sm text-syn-text-secondary leading-relaxed">{agent.issue}</p>
                    )}
                    {agent.evidence && (
                      <p className="text-xs text-syn-text-tertiary mt-1 font-mono">{agent.evidence}</p>
                    )}
                  </div>
                </div>
                {agent.recommendation && (
                  <p className="text-xs text-syn-accent/70 mt-2 flex items-start gap-1.5">
                    <Target size={10} className="mt-0.5 flex-shrink-0" />
                    {agent.recommendation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Correlation clusters */}
      {clusters.length > 0 && (
        <CollapsibleSection title="Correlation Clusters" icon={Activity} defaultOpen={false}>
          <div className="space-y-2">
            {clusters.map((cluster: any, i: number) => (
              <div key={i} className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex flex-wrap gap-1">
                    {(cluster.agents || []).map((a: string) => (
                      <span
                        key={a}
                        className="text-[10px] font-mono bg-white/[0.05] px-2 py-0.5 rounded text-syn-text-secondary"
                      >
                        {formatKey(a)}
                      </span>
                    ))}
                  </div>
                  {cluster.agreement_rate && (
                    <span className="text-[10px] font-mono text-amber-400">
                      {formatPercent(cluster.agreement_rate)} agreement
                    </span>
                  )}
                </div>
                {cluster.implication && (
                  <p className="text-xs text-syn-text-tertiary">{cluster.implication}</p>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  ATTRIBUTION FINDINGS                                                */
/* ------------------------------------------------------------------ */

function AttributionFindings({ findings }: { findings: Record<string, any> }) {
  const regimeInsights = findings.regime_insights || [];
  const teamInsights = findings.team_insights || [];
  const worstPatterns = findings.worst_patterns || findings.worst_concerns || [];
  const convictionCal = findings.conviction_calibration;
  const posSizing = findings.position_sizing_recommendation;
  const overall = findings.overall_assessment;

  return (
    <>
      {overall && (
        <p className="mt-4 text-sm text-syn-text-secondary leading-relaxed">{overall}</p>
      )}

      {convictionCal && (
        <div className="mt-4 bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <Target size={12} className="text-syn-text-tertiary" />
            <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted">
              Conviction Calibration
            </span>
          </div>
          <p className="text-sm text-syn-text-secondary leading-relaxed">{convictionCal}</p>
        </div>
      )}

      {/* Regime insights */}
      {regimeInsights.length > 0 && (
        <CollapsibleSection title="By Regime" icon={BarChart3} count={regimeInsights.length}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {regimeInsights.map((r: any, i: number) => (
              <div key={i} className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  {r.regime === 'bull' ? (
                    <TrendingUp size={12} className="text-emerald-400" />
                  ) : r.regime === 'bear' ? (
                    <TrendingDown size={12} className="text-red-400" />
                  ) : (
                    <Activity size={12} className="text-amber-400" />
                  )}
                  <span className="text-xs font-semibold text-white capitalize">{r.regime}</span>
                  {r.win_rate !== undefined && (
                    <span className="text-[10px] font-mono tabular-nums text-syn-text-tertiary ml-auto">
                      WR: {typeof r.win_rate === 'number' && r.win_rate <= 1 ? formatPercent(r.win_rate) : r.win_rate}
                    </span>
                  )}
                </div>
                <p className="text-sm text-syn-text-secondary">{r.finding}</p>
                {r.recommendation && (
                  <p className="text-xs text-syn-accent/60 mt-1.5">{r.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Team insights */}
      {teamInsights.length > 0 && (
        <CollapsibleSection title="By Team" icon={Zap} count={teamInsights.length}>
          <div className="space-y-2">
            {teamInsights.map((t: any, i: number) => (
              <div key={i} className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono font-semibold text-white">
                    {formatKey(t.team || 'Unknown')}
                  </span>
                </div>
                <p className="text-sm text-syn-text-secondary">{t.finding}</p>
                {t.recommendation && (
                  <p className="text-xs text-syn-accent/60 mt-1.5">{t.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Worst patterns / concerns */}
      {worstPatterns.length > 0 && (
        <CollapsibleSection title="Risk Patterns" icon={AlertTriangle} count={worstPatterns.length}>
          <div className="space-y-1.5">
            {worstPatterns.map((pattern: any, i: number) => (
              <div key={i} className="flex items-start gap-2.5 bg-red-500/[0.04] border border-red-500/10 rounded-lg px-3 py-2">
                <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
                <p className="text-sm text-red-400/80 leading-relaxed">
                  {typeof pattern === 'string' ? pattern : pattern.detail || pattern.label || JSON.stringify(pattern)}
                </p>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {posSizing && (
        <div className="mt-4 bg-syn-accent/[0.06] border border-syn-accent/15 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Shield size={12} className="text-syn-accent/70" />
            <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-accent/50">
              Position Sizing
            </span>
          </div>
          <p className="text-sm text-syn-text-secondary">{posSizing}</p>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  DATA SOURCE EVAL FINDINGS                                           */
/* ------------------------------------------------------------------ */

function DataSourceFindings({ findings }: { findings: Record<string, any> }) {
  const ranked = findings.ranked_sources || [];
  const toDrop = findings.sources_to_drop || [];
  const toInvestigate = findings.sources_to_investigate || [];
  const summary = findings.summary;

  const powerColor = (power: string) => {
    switch (power) {
      case 'strong':
        return 'text-emerald-400 bg-emerald-400/10';
      case 'moderate':
        return 'text-amber-400 bg-amber-400/10';
      case 'weak':
        return 'text-orange-400 bg-orange-400/10';
      case 'noise':
        return 'text-red-400 bg-red-400/10';
      default:
        return 'text-white/50 bg-white/5';
    }
  };

  return (
    <>
      {summary && (
        <p className="mt-4 text-sm text-syn-text-secondary leading-relaxed">{summary}</p>
      )}

      {ranked.length > 0 && (
        <CollapsibleSection title="Ranked Sources" icon={BarChart3} count={ranked.length}>
          <div className="space-y-2">
            {ranked.map((src: any, i: number) => (
              <div key={i} className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-sm font-semibold text-white">{src.source}</span>
                  {src.predictive_power && (
                    <span
                      className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded ${powerColor(src.predictive_power)}`}
                    >
                      {src.predictive_power}
                    </span>
                  )}
                  {src.correlation !== undefined && (
                    <span className="text-[10px] font-mono tabular-nums text-syn-text-tertiary ml-auto">
                      r = {typeof src.correlation === 'number' ? src.correlation.toFixed(3) : src.correlation}
                    </span>
                  )}
                </div>
                {src.evidence && (
                  <p className="text-xs text-syn-text-tertiary leading-relaxed">{src.evidence}</p>
                )}
                {src.recommendation && (
                  <p className="text-xs text-syn-accent/60 mt-1">{src.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {(toDrop.length > 0 || toInvestigate.length > 0) && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {toDrop.length > 0 && (
            <div className="bg-red-500/[0.04] border border-red-500/10 rounded-lg p-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-red-400/60 mb-2">
                Drop
              </p>
              <div className="flex flex-wrap gap-1.5">
                {toDrop.map((s: string, i: number) => (
                  <span key={i} className="text-xs font-mono text-red-400/80 bg-red-400/10 px-2 py-0.5 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {toInvestigate.length > 0 && (
            <div className="bg-amber-500/[0.04] border border-amber-500/10 rounded-lg p-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-amber-400/60 mb-2">
                Investigate
              </p>
              <div className="flex flex-wrap gap-1.5">
                {toInvestigate.map((s: string, i: number) => (
                  <span key={i} className="text-xs font-mono text-amber-400/80 bg-amber-400/10 px-2 py-0.5 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  HYPOTHESIS TEST FINDINGS                                            */
/* ------------------------------------------------------------------ */

function HypothesisTestFindings({ findings }: { findings: Record<string, any> }) {
  const hypothesis = findings.hypothesis;
  const methodology = findings.methodology;
  const results = findings.results;
  const significance = findings.statistical_significance;
  const recommendation = findings.recommendation;
  const risks = findings.risks || [];

  const recColor = (rec: string) => {
    switch (rec) {
      case 'deploy':
        return 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20';
      case 'reject':
        return 'text-red-400 bg-red-400/10 ring-red-400/20';
      case 'needs_more_data':
        return 'text-amber-400 bg-amber-400/10 ring-amber-400/20';
      default:
        return 'text-cyan-400 bg-cyan-400/10 ring-cyan-400/20';
    }
  };

  return (
    <>
      {hypothesis && (
        <div className="mt-4 bg-white/[0.02] border border-white/[0.06] rounded-lg p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted mb-1.5">
            Hypothesis
          </p>
          <p className="text-sm text-white font-medium leading-relaxed">{hypothesis}</p>
        </div>
      )}

      {methodology && (
        <div className="mt-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted mb-1.5">
            Methodology
          </p>
          <p className="text-sm text-syn-text-secondary leading-relaxed">{methodology}</p>
        </div>
      )}

      {results && (
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted mb-2">
            Results
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
            {Object.entries(results).map(([k, v]) => {
              const pctKeys = ['win_rate', 'max_drawdown'];
              const intKeys = ['sample_size'];
              let display: string;
              if (typeof v === 'number') {
                if (pctKeys.includes(k)) display = formatPercent(v);
                else if (intKeys.includes(k)) display = String(Math.round(v));
                else display = v.toFixed(2);
              } else {
                display = String(v);
              }
              return (
                <div key={k} className="bg-white/[0.03] border border-white/[0.06] rounded-lg p-2.5 text-center">
                  <p className="text-[10px] text-syn-text-tertiary font-mono">{formatKey(k)}</p>
                  <p className="text-lg font-bold font-mono tabular-nums text-white mt-0.5">
                    {display}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {significance && (
          <span className="text-xs font-mono text-syn-text-secondary bg-white/[0.03] px-3 py-1.5 rounded-lg">
            {significance}
          </span>
        )}
        {recommendation && (
          <span
            className={`text-xs font-bold uppercase px-3 py-1 rounded-full ring-1 ring-inset ${recColor(recommendation)}`}
          >
            {formatKey(recommendation)}
          </span>
        )}
      </div>

      {risks.length > 0 && (
        <CollapsibleSection title="Risks" icon={Shield} defaultOpen={false} count={risks.length}>
          <div className="space-y-1.5">
            {risks.map((risk: string, i: number) => (
              <div key={i} className="flex items-start gap-2 text-sm text-syn-text-secondary">
                <div className="w-1 h-1 rounded-full bg-amber-400 mt-2 flex-shrink-0" />
                <span>{risk}</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  WEEKLY DIGEST FINDINGS                                              */
/* ------------------------------------------------------------------ */

function WeeklyDigestFindings({ findings }: { findings: Record<string, any> }) {
  const execSummary = findings.executive_summary;
  const keyFindings = findings.key_findings || [];
  const criticalAlerts = findings.critical_alerts || [];
  const boardRecs = findings.recommendations_for_board || [];
  const signalHealth = findings.signal_health_summary;
  const outlook = findings.market_outlook;

  return (
    <>
      {execSummary && (
        <div className="mt-4 bg-white/[0.02] border-l-2 border-syn-accent/30 pl-4 py-2">
          <p className="text-sm text-white font-medium leading-relaxed">{execSummary}</p>
        </div>
      )}

      {criticalAlerts.length > 0 && (
        <CollapsibleSection title="Critical Alerts" icon={AlertTriangle} count={criticalAlerts.length}>
          <div className="space-y-1.5">
            {criticalAlerts.map((alert: string, i: number) => (
              <div key={i} className="flex items-start gap-2.5 bg-red-500/[0.04] border border-red-500/10 rounded-lg px-3 py-2">
                <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0 animate-pulse" />
                <p className="text-sm text-red-400/80">{alert}</p>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {keyFindings.length > 0 && (
        <CollapsibleSection title="Key Findings" icon={Eye} count={keyFindings.length}>
          <div className="space-y-2">
            {keyFindings.map((kf: any, i: number) => (
              <div
                key={i}
                className={`border rounded-lg p-3 ${severityBg(kf.severity || 'informational')}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div
                    className={`w-2 h-2 rounded-full flex-shrink-0 ${severityDot(kf.severity || 'informational')}`}
                  />
                  {kf.severity && (
                    <span className={`text-[9px] font-bold uppercase ${severityColor(kf.severity)}`}>
                      {kf.severity}
                    </span>
                  )}
                </div>
                <p className="text-sm text-syn-text-secondary leading-relaxed">
                  {kf.finding || kf.label || kf.detail}
                </p>
                {kf.evidence && (
                  <p className="text-xs text-syn-text-tertiary mt-1 font-mono">{kf.evidence}</p>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {boardRecs.length > 0 && (
        <CollapsibleSection title="Board Recommendations" icon={Target} count={boardRecs.length}>
          <div className="space-y-2">
            {boardRecs.map((rec: any, i: number) => {
              if (typeof rec === 'string') {
                return (
                  <div key={i} className="flex items-start gap-2">
                    <CheckCircle2 size={14} className="text-emerald-400/70 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-syn-text-secondary">{rec}</span>
                  </div>
                );
              }
              const priorityColor =
                rec.priority === 'immediate'
                  ? 'text-red-400 bg-red-400/10'
                  : rec.priority === 'next_cycle'
                    ? 'text-amber-400 bg-amber-400/10'
                    : 'text-white/50 bg-white/5';
              return (
                <div
                  key={i}
                  className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 size={12} className="text-emerald-400/70 flex-shrink-0" />
                    <span className="text-sm font-medium text-white flex-1">{rec.action}</span>
                    {rec.priority && (
                      <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded ${priorityColor}`}>
                        {formatKey(rec.priority)}
                      </span>
                    )}
                  </div>
                  {rec.rationale && (
                    <p className="text-xs text-syn-text-tertiary mt-1 ml-5">{rec.rationale}</p>
                  )}
                </div>
              );
            })}
          </div>
        </CollapsibleSection>
      )}

      {signalHealth && (
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted mb-1.5">
            Signal Health
          </p>
          <p className="text-sm text-syn-text-secondary leading-relaxed">{signalHealth}</p>
        </div>
      )}

      {outlook && (
        <div className="mt-4 bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <TrendingUp size={12} className="text-syn-text-tertiary" />
            <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted">
              Market Outlook
            </span>
          </div>
          <p className="text-sm text-syn-text-secondary leading-relaxed">{outlook}</p>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  GENERIC OBJECT FINDINGS (fallback)                                  */
/* ------------------------------------------------------------------ */

function GenericObjectFindings({ findings }: { findings: Record<string, any> }) {
  // Filter out `title` — already rendered as report.title above the findings
  const entries = Object.entries(findings).filter(
    ([k, v]) => v !== null && v !== undefined && k !== 'title'
  );
  if (entries.length === 0) return null;

  return (
    <CollapsibleSection title="Findings" icon={FileText}>
      <div className="space-y-3">
        {entries.map(([key, value]) => (
          <div key={key}>
            <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted mb-1.5">
              {formatKey(key)}
            </p>
            {typeof value === 'string' ? (
              <p className="text-sm text-syn-text-secondary leading-relaxed">{value}</p>
            ) : Array.isArray(value) ? (
              <div className="space-y-1.5">
                {value.map((item, i) =>
                  typeof item === 'string' ? (
                    <div key={i} className="flex items-start gap-2">
                      <div className="w-1 h-1 rounded-full bg-white/30 mt-2 flex-shrink-0" />
                      <p className="text-sm text-syn-text-secondary">{item}</p>
                    </div>
                  ) : typeof item === 'object' && item !== null ? (
                    <div
                      key={i}
                      className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3"
                    >
                      {Object.entries(item).map(([ik, iv]) => (
                        <div key={ik} className="mb-1 last:mb-0">
                          <span className="text-[10px] text-syn-text-tertiary font-mono">
                            {formatKey(ik)}:
                          </span>{' '}
                          <span className="text-sm text-syn-text-secondary">
                            {String(iv)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p key={i} className="text-sm text-syn-text-secondary">{String(item)}</p>
                  )
                )}
              </div>
            ) : typeof value === 'object' ? (
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
                {Object.entries(value).map(([ik, iv]) => (
                  <div key={ik} className="flex items-baseline gap-2 mb-1 last:mb-0">
                    <span className="text-[10px] text-syn-text-tertiary font-mono">
                      {formatKey(ik)}
                    </span>
                    <span className="text-sm font-mono tabular-nums text-syn-text-secondary">
                      {typeof iv === 'object' ? JSON.stringify(iv) : String(iv)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm font-mono tabular-nums text-syn-text-secondary">
                {String(value)}
              </p>
            )}
          </div>
        ))}
      </div>
    </CollapsibleSection>
  );
}

/* ------------------------------------------------------------------ */
/*  FINDINGS ROUTER                                                     */
/* ------------------------------------------------------------------ */

function FindingsSection({
  findings,
  reportType,
}: {
  findings: Finding[] | Record<string, any> | null;
  reportType: string;
}) {
  if (!findings) return null;

  // Array-based findings (severity / label / detail)
  if (isFindingsArray(findings)) {
    if (findings.length === 0) return null;
    return (
      <CollapsibleSection title="Findings" icon={FileText} count={findings.length}>
        <div className="space-y-2">
          {findings.map((finding, i) => (
            <div
              key={i}
              className={`border rounded-lg p-3 ${severityBg(finding.severity || 'informational')}`}
            >
              <div className="flex items-start gap-2.5">
                <div
                  className={`w-2 h-2 rounded-full ${severityDot(finding.severity || 'informational')} mt-1.5 flex-shrink-0`}
                />
                <div className="min-w-0">
                  {finding.label && (
                    <span className="text-sm font-medium text-white">{finding.label}</span>
                  )}
                  {finding.detail && (
                    <p className="text-sm text-syn-text-secondary leading-relaxed">
                      <ExpandableText text={finding.detail} />
                    </p>
                  )}
                  {!finding.label && !finding.detail && (
                    <p className="text-sm text-syn-text-secondary">
                      {Object.entries(finding)
                        .filter(([k]) => k !== 'severity')
                        .map(([k, v]) => `${formatKey(k)}: ${v}`)
                        .join(' | ')}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CollapsibleSection>
    );
  }

  // Object-based: route to specialized component by report type
  const f = findings as Record<string, any>;

  // Signal Health / Signal Decay
  if (
    reportType === 'signal_decay' ||
    reportType === 'risk_analysis' ||
    f.overall_health !== undefined ||
    f.agents_flagged !== undefined
  ) {
    return <SignalHealthFindings findings={f} />;
  }

  // Attribution
  if (
    reportType === 'performance_attribution' ||
    f.team_insights !== undefined ||
    f.regime_insights !== undefined ||
    f.worst_patterns !== undefined ||
    f.worst_concerns !== undefined
  ) {
    return <AttributionFindings findings={f} />;
  }

  // Data Source Eval
  if (
    reportType === 'data_source_eval' ||
    reportType === 'correlation_analysis' ||
    f.ranked_sources !== undefined
  ) {
    return <DataSourceFindings findings={f} />;
  }

  // Hypothesis Test
  if (reportType === 'hypothesis_test' || f.hypothesis !== undefined) {
    return <HypothesisTestFindings findings={f} />;
  }

  // Weekly Digest
  if (
    reportType === 'weekly_digest' ||
    f.executive_summary !== undefined ||
    f.key_findings !== undefined
  ) {
    return <WeeklyDigestFindings findings={f} />;
  }

  // Fallback: generic object rendering
  return <GenericObjectFindings findings={f} />;
}

/* ------------------------------------------------------------------ */
/*  RECOMMENDATIONS                                                     */
/* ------------------------------------------------------------------ */

function RecommendationsSection({
  recommendations,
}: {
  recommendations: string[] | any[] | null;
}) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <CollapsibleSection title="Recommendations" icon={CheckCircle2} count={recommendations.length}>
      <div className="space-y-1.5">
        {recommendations.map((rec, i) => {
          if (typeof rec === 'string') {
            return (
              <div key={i} className="flex items-start gap-2.5">
                <CheckCircle2 size={14} className="text-emerald-400/70 mt-0.5 flex-shrink-0" />
                <span className="text-sm text-syn-text-secondary leading-relaxed">{rec}</span>
              </div>
            );
          }
          // Object recommendation (e.g., weekly digest board recs)
          if (typeof rec === 'object' && rec !== null) {
            const priorityColor =
              rec.priority === 'immediate'
                ? 'text-red-400 bg-red-400/10'
                : rec.priority === 'next_cycle'
                  ? 'text-amber-400 bg-amber-400/10'
                  : 'text-white/50 bg-white/5';
            return (
              <div key={i} className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle2 size={12} className="text-emerald-400/70 flex-shrink-0" />
                  <span className="text-sm font-medium text-white flex-1">
                    {rec.action || rec.label || rec.title || JSON.stringify(rec)}
                  </span>
                  {rec.priority && (
                    <span
                      className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded ${priorityColor}`}
                    >
                      {formatKey(rec.priority)}
                    </span>
                  )}
                </div>
                {rec.rationale && (
                  <p className="text-xs text-syn-text-tertiary mt-1 ml-5">{rec.rationale}</p>
                )}
              </div>
            );
          }
          return (
            <div key={i} className="flex items-start gap-2.5">
              <CheckCircle2 size={14} className="text-emerald-400/70 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-syn-text-secondary">{String(rec)}</span>
            </div>
          );
        })}
      </div>
    </CollapsibleSection>
  );
}

/* ------------------------------------------------------------------ */
/*  DATA CONTEXT FOOTER                                                 */
/* ------------------------------------------------------------------ */

function DataContextFooter({ context }: { context: DataContext | null }) {
  if (!context) return null;

  const entries = Object.entries(context).filter(
    ([, v]) => v !== null && v !== undefined && v !== ''
  );
  if (entries.length === 0) return null;

  return (
    <div className="mt-5 pt-4 border-t border-white/[0.04]">
      <div className="flex flex-wrap gap-2">
        {entries.map(([key, value]) => (
          <span
            key={key}
            className="text-[10px] font-mono tabular-nums font-medium text-syn-text-tertiary bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-syn-border"
          >
            {formatKey(key).toLowerCase()}: {typeof value === 'object' ? Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(', ') : String(value)}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  REPORT CARD                                                         */
/* ------------------------------------------------------------------ */

function ReportCard({ report }: { report: ResearchReport }) {
  const researcher = researcherConfig[report.researcher] || {
    name: report.researcher,
    title: 'Researcher',
    gradient: 'from-gray-500 to-gray-600',
    initial: '?',
  };
  const reportType = reportTypeConfig[report.report_type] || {
    label: report.report_type.replace(/_/g, ' ').toUpperCase(),
    color: 'text-gray-400 bg-gray-400/10 ring-gray-400/20',
  };
  const isCritical = hasCriticalFinding(report);

  return (
    <article
      className={`bg-syn-surface border rounded-xl p-5 sm:p-6 transition-colors ${
        isCritical
          ? 'border-red-500/20 hover:border-red-500/30'
          : 'border-syn-border hover:border-white/[0.10]'
      }`}
    >
      {/* Top row: researcher info + badge/timestamp */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
        {/* Left: researcher */}
        <div className="flex items-center gap-3">
          <ResearcherAvatar researcher={report.researcher} />
          <div>
            <p className="text-sm font-semibold text-syn-text">{researcher.name}</p>
            <p className="text-xs text-syn-text-tertiary">{researcher.title}</p>
          </div>
        </div>

        {/* Right: report type badge + timestamp */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <span
            className={`text-[10px] font-bold px-2.5 py-0.5 rounded ring-1 ring-inset ${reportType.color}`}
          >
            {reportType.label}
          </span>
          <span className="flex items-center gap-1.5 text-xs text-syn-text-tertiary font-mono tabular-nums">
            <Clock size={10} className="text-syn-text-tertiary" />
            {formatTimestamp(report.created_at)}
          </span>
        </div>
      </div>

      {/* Title */}
      <h2 className="text-lg font-bold tracking-tight text-white mb-2 leading-tight">
        {report.title}
      </h2>

      {/* Summary */}
      {report.summary && (
        <p className="text-sm text-syn-text-secondary leading-relaxed">
          <ExpandableText text={report.summary} maxLength={350} />
        </p>
      )}

      {/* Findings — routed by report type */}
      <FindingsSection findings={report.findings} reportType={report.report_type} />

      {/* Recommendations */}
      <RecommendationsSection recommendations={report.recommendations} />

      {/* Data context */}
      <DataContextFooter context={report.data_context} />
    </article>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN PAGE                                                          */
/* ------------------------------------------------------------------ */

export default function ResearchPage() {
  const [reports, setReports] = useState<ResearchReport[]>([]);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);

    const tab = filterTabs.find((t) => t.key === activeFilter);
    const types = tab?.types || [];

    if (types.length === 0) {
      fetch(`${API_BASE}/api/v1/research/reports?limit=20`)
        .then((r) => r.json())
        .then((data) => setReports(Array.isArray(data) ? data : []))
        .catch(() => setReports([]))
        .finally(() => setLoading(false));
    } else if (types.length === 1) {
      fetch(`${API_BASE}/api/v1/research/reports?limit=20&report_type=${types[0]}`)
        .then((r) => r.json())
        .then((data) => setReports(Array.isArray(data) ? data : []))
        .catch(() => setReports([]))
        .finally(() => setLoading(false));
    } else {
      Promise.all(
        types.map((t) =>
          fetch(`${API_BASE}/api/v1/research/reports?limit=20&report_type=${t}`)
            .then((r) => r.json())
            .catch(() => [])
        )
      )
        .then((results) => {
          const merged = results
            .flat()
            .filter((r: any) => r && r.id)
            .sort(
              (a: ResearchReport, b: ResearchReport) =>
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            );
          setReports(merged);
        })
        .catch(() => setReports([]))
        .finally(() => setLoading(false));
    }
  }, [activeFilter]);

  return (
    <div className="max-w-4xl mx-auto slide-up">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 flex items-center justify-center ring-1 ring-indigo-500/20">
            <Beaker size={18} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Research Reports</h1>
            <p className="text-sm text-syn-muted">
              AI watching AI. Three researchers audit whether the fund&apos;s agents are any good.
            </p>
          </div>
        </div>
      </div>

      {/* Filter segmented control */}
      <div className="mb-8 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
        <div className="inline-flex bg-white/[0.03] rounded-full p-1 ring-1 ring-syn-border">
          {filterTabs.map((tab) => (
            <button
              key={tab.key ?? 'all'}
              onClick={() => setActiveFilter(tab.key)}
              className={`text-xs font-semibold px-3 sm:px-4 py-1.5 rounded-full transition-all duration-200 whitespace-nowrap ${
                activeFilter === tab.key
                  ? 'bg-syn-accent/15 text-syn-accent shadow-sm'
                  : 'text-syn-text-tertiary hover:text-syn-text-secondary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-32">
          <div className="flex items-center gap-3">
            <Loader2 size={18} className="text-syn-accent animate-spin" />
            <p className="text-sm text-syn-text-tertiary">Loading research reports...</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && reports.length === 0 && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-8 sm:p-16 text-center">
          <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-4 ring-1 ring-syn-border">
            <FileText size={20} className="text-syn-text-tertiary" />
          </div>
          <p className="text-sm text-syn-text-secondary font-medium mb-1">No research reports yet</p>
          <p className="text-xs text-syn-text-tertiary max-w-md mx-auto leading-relaxed">
            The research team runs daily analysis at 06:00 UTC and weekly deep research on Saturdays.
            Reports will appear here.
          </p>
        </div>
      )}

      {/* Critical alerts */}
      {!loading && reports.length > 0 && <CriticalAlerts reports={reports} />}

      {/* Reports feed */}
      {!loading && reports.length > 0 && (
        <div className="space-y-4">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      )}
    </div>
  );
}
