'use client';

import { useEffect, useState } from 'react';
import { Loader2, Clock, FileText, CheckCircle2 } from 'lucide-react';
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
  recommendations: string[] | null;
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

function isFindingsArray(findings: any): findings is Finding[] {
  return Array.isArray(findings);
}

function hasCriticalFinding(report: ResearchReport): boolean {
  if (!report.findings) return false;
  if (isFindingsArray(report.findings)) {
    return report.findings.some((f) => f.severity === 'critical');
  }
  return false;
}

/* ------------------------------------------------------------------ */
/*  SUB-COMPONENTS                                                      */
/* ------------------------------------------------------------------ */

function ResearcherAvatar({ researcher }: { researcher: string }) {
  const config = researcherConfig[researcher];
  if (!config) return null;
  return (
    <div
      className={`w-8 h-8 rounded-full bg-gradient-to-br ${config.gradient} flex items-center justify-center flex-shrink-0`}
    >
      <span className="text-xs font-bold text-white">{config.initial}</span>
    </div>
  );
}

function CriticalAlerts({ reports }: { reports: ResearchReport[] }) {
  const critical = reports.filter(hasCriticalFinding);
  if (critical.length === 0) return null;

  return (
    <div className="mb-8 space-y-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">
        Critical Alerts
      </p>
      {critical.map((report) => {
        const criticalFindings = isFindingsArray(report.findings)
          ? report.findings.filter((f) => f.severity === 'critical')
          : [];
        const config = researcherConfig[report.researcher];

        return (
          <div
            key={`alert-${report.id}`}
            className="bg-syn-surface border border-red-500/30 rounded-xl p-4"
          >
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-red-400 mt-1.5 flex-shrink-0 animate-pulse" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-bold text-white">{report.title}</span>
                  <span className="text-[10px] font-mono tabular-nums text-syn-text-tertiary">
                    {formatRelative(report.created_at)}
                  </span>
                </div>
                {criticalFindings.map((finding, i) => (
                  <p key={i} className="text-sm text-red-400/80">
                    {finding.label || finding.detail || JSON.stringify(finding)}
                  </p>
                ))}
                {config && (
                  <p className="text-[10px] text-syn-text-tertiary mt-1 font-mono">{config.name}</p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FindingsSection({ findings }: { findings: Finding[] | Record<string, any> | null }) {
  if (!findings) return null;

  // Array of findings with severity
  if (isFindingsArray(findings)) {
    return (
      <div className="mt-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-2">
          Findings
        </p>
        {findings.map((finding, i) => (
          <div key={i} className="flex items-start gap-2.5">
            <div className={`w-2 h-2 rounded-full ${severityDot(finding.severity || 'informational')} mt-1.5 flex-shrink-0`} />
            <div className="min-w-0">
              {finding.label && (
                <span className="text-sm font-medium text-syn-text-secondary">{finding.label}</span>
              )}
              {finding.detail && (
                <p className="text-sm text-syn-text-secondary">{finding.detail}</p>
              )}
              {!finding.label && !finding.detail && (
                <p className="text-sm text-syn-text-secondary">{JSON.stringify(finding)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Key-value pairs
  const entries = Object.entries(findings);
  if (entries.length === 0) return null;

  return (
    <div className="mt-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-2">
        Findings
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-baseline gap-2">
            <span className="text-xs text-syn-text-tertiary font-mono">{key.replace(/_/g, ' ')}</span>
            <span className="text-sm font-mono tabular-nums text-syn-text-secondary">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecommendationsSection({ recommendations }: { recommendations: string[] | null }) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="mt-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-2">
        Recommendations
      </p>
      <ol className="space-y-1.5">
        {recommendations.map((rec, i) => (
          <li key={i} className="flex items-start gap-2">
            <CheckCircle2 size={14} className="text-emerald-400/70 mt-0.5 flex-shrink-0" />
            <span className="text-sm text-syn-text-secondary">{rec}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function DataContextFooter({ context }: { context: DataContext | null }) {
  if (!context) return null;

  const entries = Object.entries(context).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) return null;

  return (
    <div className="mt-5 pt-4 border-t border-white/[0.04]">
      <div className="flex flex-wrap gap-2">
        {entries.map(([key, value]) => (
          <span
            key={key}
            className="text-[10px] font-mono tabular-nums font-medium text-syn-text-tertiary bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-syn-border"
          >
            {key.replace(/_/g, ' ')}: {String(value)}
          </span>
        ))}
      </div>
    </div>
  );
}

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

  return (
    <article className="bg-syn-surface border border-syn-border rounded-xl p-6 hover:border-white/[0.10] transition-colors">
      {/* Top row: researcher info + badge/timestamp */}
      <div className="flex items-start justify-between mb-4">
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
        <p className="text-sm text-syn-text-secondary italic leading-relaxed">
          {report.summary}
        </p>
      )}

      {/* Findings */}
      <FindingsSection findings={report.findings} />

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
      // "All" tab — single fetch with no report_type filter
      fetch(`${API_BASE}/api/v1/research/reports?limit=20`)
        .then((r) => r.json())
        .then((data) => setReports(Array.isArray(data) ? data : []))
        .catch(() => setReports([]))
        .finally(() => setLoading(false));
    } else if (types.length === 1) {
      // Single type — direct query
      fetch(`${API_BASE}/api/v1/research/reports?limit=20&report_type=${types[0]}`)
        .then((r) => r.json())
        .then((data) => setReports(Array.isArray(data) ? data : []))
        .catch(() => setReports([]))
        .finally(() => setLoading(false));
    } else {
      // Multiple types — fetch each and merge
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
            .sort((a: ResearchReport, b: ResearchReport) =>
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
      {/* ── Header ── */}
      <div className="mb-10">
        <h1 className="text-2xl font-bold tracking-tight text-white">Research Reports</h1>
        <p className="text-sm text-syn-muted mt-1">
          AI watching AI. Three researchers audit whether the fund&apos;s own agents are any good.
        </p>
      </div>

      {/* ── Filter segmented control ── */}
      <div className="mb-8">
        <div className="inline-flex bg-white/[0.03] rounded-full p-1 ring-1 ring-syn-border">
          {filterTabs.map((tab) => (
            <button
              key={tab.key ?? 'all'}
              onClick={() => setActiveFilter(tab.key)}
              className={`text-xs font-semibold px-4 py-1.5 rounded-full transition-all duration-200 ${
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

      {/* ── Loading state ── */}
      {loading && (
        <div className="flex items-center justify-center py-32">
          <div className="flex items-center gap-3">
            <Loader2 size={18} className="text-syn-accent animate-spin" />
            <p className="text-sm text-syn-text-tertiary">Loading research reports...</p>
          </div>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && reports.length === 0 && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-16 text-center">
          <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-4 ring-1 ring-syn-border">
            <FileText size={20} className="text-syn-text-tertiary" />
          </div>
          <p className="text-sm text-syn-text-secondary font-medium mb-1">No research reports yet</p>
          <p className="text-xs text-syn-text-tertiary max-w-md mx-auto leading-relaxed">
            The research team runs daily analysis at 06:00 UTC and weekly deep research on Saturdays. Reports will appear here.
          </p>
        </div>
      )}

      {/* ── Critical alerts ── */}
      {!loading && reports.length > 0 && <CriticalAlerts reports={reports} />}

      {/* ── Reports feed ── */}
      {!loading && reports.length > 0 && (
        <div className="space-y-0">
          {reports.map((report, idx) => (
            <div key={report.id}>
              {/* Divider between reports */}
              {idx > 0 && (
                <div className="flex items-center gap-3 py-6">
                  <div className="flex-1 h-px bg-white/[0.04]" />
                  <span className="text-[10px] text-syn-text-tertiary font-mono tabular-nums">
                    {formatRelative(report.created_at)}
                  </span>
                  <div className="flex-1 h-px bg-white/[0.04]" />
                </div>
              )}

              <ReportCard report={report} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
