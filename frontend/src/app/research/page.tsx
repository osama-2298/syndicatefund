'use client';

import { useEffect, useState } from 'react';
import { Loader2, Clock, FileText, CheckCircle2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
/*  RESEARCHER CONFIG                                                   */
/* ------------------------------------------------------------------ */

const researcherConfig: Record<string, { name: string; title: string; gradient: string; initial: string }> = {
  head_of_research: {
    name: 'Dr. Elara Voss',
    title: 'Head of Research',
    gradient: 'from-indigo-500 to-violet-500',
    initial: 'E',
  },
  quant_researcher: {
    name: 'Dr. Kai Moretti',
    title: 'Quant Researcher',
    gradient: 'from-cyan-500 to-blue-500',
    initial: 'K',
  },
  strategy_researcher: {
    name: 'Dr. Noor Hadid',
    title: 'Strategy Researcher',
    gradient: 'from-amber-500 to-orange-500',
    initial: 'N',
  },
};

/* ------------------------------------------------------------------ */
/*  REPORT TYPE CONFIG                                                  */
/* ------------------------------------------------------------------ */

const reportTypeConfig: Record<string, { label: string; color: string }> = {
  signal_decay: {
    label: 'SIGNAL DECAY',
    color: 'text-red-400 bg-red-400/10 ring-red-400/20',
  },
  performance_attribution: {
    label: 'ATTRIBUTION',
    color: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20',
  },
  correlation_analysis: {
    label: 'CORRELATION',
    color: 'text-blue-400 bg-blue-400/10 ring-blue-400/20',
  },
  data_source_eval: {
    label: 'DATA SOURCE',
    color: 'text-purple-400 bg-purple-400/10 ring-purple-400/20',
  },
  hypothesis_test: {
    label: 'HYPOTHESIS',
    color: 'text-cyan-400 bg-cyan-400/10 ring-cyan-400/20',
  },
  weekly_digest: {
    label: 'WEEKLY DIGEST',
    color: 'text-amber-400 bg-amber-400/10 ring-amber-400/20',
  },
  risk_analysis: {
    label: 'RISK ANALYSIS',
    color: 'text-orange-400 bg-orange-400/10 ring-orange-400/20',
  },
};

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

function formatTimestamp(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }) + ' · ' + d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }) + ' UTC';
}

function formatRelative(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return 'Just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return formatTimestamp(dateStr);
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
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">
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
            className="bg-[#0d0d15] border border-red-500/30 rounded-xl p-4"
          >
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-red-400 mt-1.5 flex-shrink-0 animate-pulse" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-bold text-white">{report.title}</span>
                  <span className="text-[10px] font-mono tabular-nums text-white/25">
                    {formatRelative(report.created_at)}
                  </span>
                </div>
                {criticalFindings.map((finding, i) => (
                  <p key={i} className="text-sm text-amber-400/80">
                    {finding.label || finding.detail || JSON.stringify(finding)}
                  </p>
                ))}
                {config && (
                  <p className="text-[10px] text-white/25 mt-1 font-mono">{config.name}</p>
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
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-2">
          Findings
        </p>
        {findings.map((finding, i) => (
          <div key={i} className="flex items-start gap-2.5">
            <div className={`w-2 h-2 rounded-full ${severityDot(finding.severity || 'informational')} mt-1.5 flex-shrink-0`} />
            <div className="min-w-0">
              {finding.label && (
                <span className="text-sm font-medium text-white/70">{finding.label}</span>
              )}
              {finding.detail && (
                <p className="text-sm text-white/40">{finding.detail}</p>
              )}
              {!finding.label && !finding.detail && (
                <p className="text-sm text-white/40">{JSON.stringify(finding)}</p>
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
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-2">
        Findings
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-baseline gap-2">
            <span className="text-[11px] text-white/30 font-mono">{key.replace(/_/g, ' ')}</span>
            <span className="text-sm font-mono tabular-nums text-white/60">
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
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-2">
        Recommendations
      </p>
      <ol className="space-y-1.5">
        {recommendations.map((rec, i) => (
          <li key={i} className="flex items-start gap-2">
            <CheckCircle2 size={14} className="text-emerald-400/70 mt-0.5 flex-shrink-0" />
            <span className="text-sm text-white/50">{rec}</span>
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
            className="text-[10px] font-mono tabular-nums font-medium text-white/30 bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-white/[0.06]"
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
    <article className="bg-[#0d0d15] border border-white/[0.06] rounded-xl p-6 hover:border-white/[0.10] transition-colors">
      {/* Top row: researcher info + badge/timestamp */}
      <div className="flex items-start justify-between mb-4">
        {/* Left: researcher */}
        <div className="flex items-center gap-3">
          <ResearcherAvatar researcher={report.researcher} />
          <div>
            <p className="text-sm font-semibold text-white/80">{researcher.name}</p>
            <p className="text-[11px] text-white/30">{researcher.title}</p>
          </div>
        </div>

        {/* Right: report type badge + timestamp */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <span
            className={`text-[10px] font-bold px-2.5 py-0.5 rounded ring-1 ring-inset ${reportType.color}`}
          >
            {reportType.label}
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-white/25 font-mono tabular-nums">
            <Clock size={10} className="text-white/15" />
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
        <p className="text-sm text-white/40 italic leading-relaxed">
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
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-4">
          Research Division
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-white">Research Division</h1>
        <p className="text-sm text-white/30 mt-1">
          Dr. Elara Voss &middot; Dr. Kai Moretti &middot; Dr. Noor Hadid
        </p>
      </div>

      {/* ── Filter segmented control ── */}
      <div className="mb-8">
        <div className="inline-flex bg-white/[0.03] rounded-full p-1 ring-1 ring-white/[0.06]">
          {filterTabs.map((tab) => (
            <button
              key={tab.key ?? 'all'}
              onClick={() => setActiveFilter(tab.key)}
              className={`text-xs font-semibold px-4 py-1.5 rounded-full transition-all duration-200 ${
                activeFilter === tab.key
                  ? 'bg-white/[0.08] text-white shadow-sm'
                  : 'text-white/30 hover:text-white/50'
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
            <Loader2 size={18} className="text-amber-400/60 animate-spin" />
            <p className="text-sm text-white/30">Loading research reports...</p>
          </div>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && reports.length === 0 && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl p-16 text-center">
          <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-4 ring-1 ring-white/[0.06]">
            <FileText size={20} className="text-white/15" />
          </div>
          <p className="text-sm text-white/50 font-medium mb-1">No research reports yet</p>
          <p className="text-xs text-white/25 max-w-md mx-auto leading-relaxed">
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
                  <span className="text-[10px] text-white/15 font-mono tabular-nums">
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
