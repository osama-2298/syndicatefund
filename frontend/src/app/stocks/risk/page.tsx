
'use client';

import {
  Shield, AlertTriangle, TrendingDown, BarChart3, Activity,
  Gauge, PieChart, Zap, Power,
} from 'lucide-react';
import { DemoBanner } from '@/components/DemoBanner';

// ── Demo Risk Data ──

const riskMetrics = {
  totalExposure: 37_850,
  cashPct: 62.2,
  maxDrawdownReached: 2.4,
  drawdownLimit: 4.0,
  var95: 2_180,
  var99: 3_420,
  cvar: 4_150,
  sharpeRatio: 1.45,
  sortinoRatio: 2.1,
  betaToSpy: 0.82,
  correlationToSpy: 0.71,
};

const sectorExposure = [
  { sector: 'Technology', pct: 48.2, amount: 18_240, limit: 50, color: 'bg-blue-500' },
  { sector: 'Consumer Disc.', pct: 18.5, amount: 7_000, limit: 25, color: 'bg-amber-500' },
  { sector: 'Financials', pct: 14.8, amount: 5_600, limit: 20, color: 'bg-emerald-500' },
  { sector: 'Health Care', pct: 10.2, amount: 3_860, limit: 20, color: 'bg-purple-500' },
  { sector: 'Communication', pct: 8.3, amount: 3_150, limit: 15, color: 'bg-cyan-500' },
];

const positionHeat = [
  { symbol: 'AAPL', weight: 21.7, risk: 'LOW', pnlPct: 2.1, beta: 1.1 },
  { symbol: 'NVDA', weight: 28.9, risk: 'MEDIUM', pnlPct: 2.5, beta: 1.8 },
  { symbol: 'MSFT', weight: 27.8, risk: 'LOW', pnlPct: 1.6, beta: 0.9 },
  { symbol: 'TSLA', weight: 21.6, risk: 'HIGH', pnlPct: -2.6, beta: 2.1 },
];

const riskAlerts = [
  { level: 'WARNING', message: 'NVDA position (28.9%) approaching concentration limit (30%)', icon: AlertTriangle },
  { level: 'INFO', message: 'Technology sector at 48.2% — above recommended 25% max', icon: Shield },
  { level: 'INFO', message: 'Portfolio beta 0.82 — slightly below market. Defensive posture.', icon: Activity },
];

const drawdownHistory = [
  { date: 'Mar 10', dd: 0 },
  { date: 'Mar 11', dd: -0.8 },
  { date: 'Mar 12', dd: -0.2 },
  { date: 'Mar 13', dd: -1.5 },
  { date: 'Mar 14', dd: -0.4 },
  { date: 'Mar 15', dd: -0.1 },
  { date: 'Mar 16', dd: -2.4 },
  { date: 'Mar 17', dd: -1.8 },
];

// ── Stress Test Data ──

const stressTests = [
  { scenario: '2008 GFC Replay', impactDollar: -8_420, impactPct: -22.2, severity: 'CRITICAL' },
  { scenario: 'COVID Mar 2020', impactDollar: -5_310, impactPct: -14.0, severity: 'HIGH' },
  { scenario: 'Fed +100bp Shock', impactDollar: -2_850, impactPct: -7.5, severity: 'MEDIUM' },
  { scenario: 'Tech Sector -15%', impactDollar: -4_120, impactPct: -10.9, severity: 'HIGH' },
  { scenario: 'USD +10% Rally', impactDollar: -1_200, impactPct: -3.2, severity: 'LOW' },
  { scenario: 'Oil Spike $120/bbl', impactDollar: -980, impactPct: -2.6, severity: 'LOW' },
];

// ── Correlation Matrix ──

const corrSymbols = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'SPY'];
const corrMatrix = [
  [1.00, 0.72, 0.85, 0.48, 0.89],
  [0.72, 1.00, 0.68, 0.55, 0.78],
  [0.85, 0.68, 1.00, 0.42, 0.91],
  [0.48, 0.55, 0.42, 1.00, 0.52],
  [0.89, 0.78, 0.91, 0.52, 1.00],
];

// ── Circuit Breakers ──

const circuitBreakers = [
  { name: 'Max Drawdown', threshold: '4.0%', current: '2.4%', status: 'ACTIVE' as const },
  { name: 'Single Position Loss', threshold: '$1,500', current: '$420', status: 'ACTIVE' as const },
  { name: 'Daily Loss Limit', threshold: '$3,000', current: '$0', status: 'ACTIVE' as const },
  { name: 'Volatility Spike', threshold: 'VIX > 35', current: 'VIX 18.2', status: 'ACTIVE' as const },
  { name: 'Correlation Breakdown', threshold: 'r < -0.5', current: 'r = 0.71', status: 'DISABLED' as const },
];

// ── Risk Budget per Team ──

const riskBudget = [
  { team: 'Technical', allocated: 35, used: 28, color: 'bg-blue-500' },
  { team: 'Fundamental', allocated: 25, used: 18, color: 'bg-emerald-500' },
  { team: 'News', allocated: 20, used: 22, color: 'bg-pink-500' },
  { team: 'Institutional', allocated: 10, used: 7, color: 'bg-cyan-500' },
  { team: 'Macro', allocated: 5, used: 4, color: 'bg-orange-500' },
  { team: 'Sentiment', allocated: 5, used: 3, color: 'bg-purple-500' },
];

const riskColor = (risk: string) => {
  if (risk === 'HIGH') return 'text-red-400 bg-red-500/10';
  if (risk === 'MEDIUM') return 'text-amber-400 bg-amber-500/10';
  return 'text-emerald-400 bg-emerald-500/10';
};

const severityColor = (severity: string) => {
  if (severity === 'CRITICAL') return 'text-red-400 bg-red-500/10';
  if (severity === 'HIGH') return 'text-orange-400 bg-orange-500/10';
  if (severity === 'MEDIUM') return 'text-amber-400 bg-amber-500/10';
  return 'text-emerald-400 bg-emerald-500/10';
};

const corrCellColor = (v: number) => {
  if (v >= 0.9) return 'bg-red-500/40 text-red-300';
  if (v >= 0.7) return 'bg-orange-500/30 text-orange-300';
  if (v >= 0.5) return 'bg-amber-500/20 text-amber-300';
  if (v >= 0.3) return 'bg-blue-500/15 text-blue-300';
  return 'bg-emerald-500/10 text-emerald-300';
};

export default function RiskPage() {
  const maxDd = Math.max(...drawdownHistory.map(d => Math.abs(d.dd)));
  const varMax = Math.max(riskMetrics.var95, riskMetrics.var99, riskMetrics.cvar);

  return (
    <div className="slide-up space-y-6">
      <DemoBanner />
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Risk Monitor</h1>
        <p className="text-sm text-hive-muted mt-1">Live risk exposure, concentration, drawdown tracking</p>
      </div>

      {/* Risk Alerts */}
      {riskAlerts.length > 0 && (
        <div className="space-y-2">
          {riskAlerts.map((alert, i) => (
            <div key={i} className={`glass-card px-4 py-3 flex items-center gap-3 ${
              alert.level === 'WARNING' ? 'border-amber-500/20' : ''
            }`}>
              <alert.icon size={14} className={alert.level === 'WARNING' ? 'text-amber-400' : 'text-blue-400'} />
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                alert.level === 'WARNING' ? 'bg-amber-500/10 text-amber-400' : 'bg-blue-500/10 text-blue-400'
              }`}>{alert.level}</span>
              <span className="text-xs text-hive-muted">{alert.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Key Risk Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Exposure', value: `$${riskMetrics.totalExposure.toLocaleString()}`, sub: `${riskMetrics.cashPct}% cash`, color: 'text-hive-text' },
          { label: 'VaR (95%)', value: `$${riskMetrics.var95.toLocaleString()}`, sub: 'Max daily loss (95% conf.)', color: 'text-amber-400' },
          { label: 'Max Drawdown', value: `-${riskMetrics.maxDrawdownReached}%`, sub: `Limit: ${riskMetrics.drawdownLimit}%`, color: 'text-red-400' },
          { label: 'Portfolio Beta', value: riskMetrics.betaToSpy.toFixed(2), sub: `Corr to SPY: ${riskMetrics.correlationToSpy}`, color: 'text-blue-400' },
        ].map((m) => (
          <div key={m.label} className="glass-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">{m.label}</p>
            <p className={`text-xl font-bold tracking-tight ${m.color}`}>{m.value}</p>
            <p className="text-[10px] text-hive-muted mt-1">{m.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Drawdown Chart */}
        <div className="lg:col-span-2 glass-card p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4">Drawdown History</p>
          <div className="space-y-2">
            {drawdownHistory.map((d) => {
              const width = maxDd > 0 ? (Math.abs(d.dd) / riskMetrics.drawdownLimit) * 100 : 0;
              return (
                <div key={d.date} className="flex items-center gap-3">
                  <span className="text-[10px] text-hive-muted w-12 shrink-0">{d.date}</span>
                  <div className="flex-1 h-4 bg-white/[0.03] rounded overflow-hidden relative">
                    <div className={`h-full rounded ${Math.abs(d.dd) > 2 ? 'bg-red-500/50' : 'bg-amber-500/30'}`} style={{ width: `${Math.min(width, 100)}%` }} />
                    {/* Limit line */}
                    <div className="absolute top-0 bottom-0 w-px bg-red-500/40" style={{ left: '100%' }} />
                  </div>
                  <span className={`text-xs font-bold w-12 text-right ${Math.abs(d.dd) > 2 ? 'text-red-400' : 'text-amber-400'}`}>
                    {d.dd}%
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-4 mt-3 text-[10px] text-hive-muted">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-500/30 rounded" /> Normal</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-500/50 rounded" /> Elevated (&gt;2%)</span>
            <span className="flex items-center gap-1"><span className="w-px h-3 bg-red-500/40" /> Limit ({riskMetrics.drawdownLimit}%)</span>
          </div>
        </div>

        {/* Sector Concentration */}
        <div className="glass-card p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4">Sector Concentration</p>
          <div className="space-y-3">
            {sectorExposure.map((s) => (
              <div key={s.sector}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium">{s.sector}</span>
                  <span className="text-xs font-bold">{s.pct}%</span>
                </div>
                <div className="h-2 bg-white/[0.04] rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${s.color}/60`} style={{ width: `${s.pct}%` }} />
                </div>
                <p className="text-[10px] text-hive-muted mt-0.5">${s.amount.toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Position Heat Map */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-white/[0.06]">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Position Risk Heat Map</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
                <th className="text-left px-4 py-2.5">Symbol</th>
                <th className="text-right px-4 py-2.5">Weight</th>
                <th className="text-center px-4 py-2.5">Risk Level</th>
                <th className="text-right px-4 py-2.5">P&L</th>
                <th className="text-right px-4 py-2.5">Beta</th>
                <th className="text-left px-4 py-2.5">Concentration</th>
              </tr>
            </thead>
            <tbody>
              {positionHeat.map((p) => (
                <tr key={p.symbol} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 font-semibold text-sm">{p.symbol}</td>
                  <td className="px-4 py-3 text-right text-sm">{p.weight}%</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${riskColor(p.risk)}`}>{p.risk}</span>
                  </td>
                  <td className={`px-4 py-3 text-right text-sm font-bold ${p.pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {p.pnlPct >= 0 ? '+' : ''}{p.pnlPct}%
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-hive-muted">{p.beta}</td>
                  <td className="px-4 py-3">
                    <div className="w-24 h-2 bg-white/[0.04] rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${p.weight > 25 ? 'bg-red-500/60' : p.weight > 15 ? 'bg-amber-500/50' : 'bg-emerald-500/40'}`}
                        style={{ width: `${Math.min(p.weight * 3.3, 100)}%` }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Risk Ratios */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Sharpe Ratio', value: riskMetrics.sharpeRatio.toFixed(2), good: riskMetrics.sharpeRatio >= 1 },
          { label: 'Sortino Ratio', value: riskMetrics.sortinoRatio.toFixed(2), good: riskMetrics.sortinoRatio >= 1.5 },
          { label: 'VaR (99%)', value: `$${riskMetrics.var99.toLocaleString()}`, good: false },
          { label: 'SPY Correlation', value: riskMetrics.correlationToSpy.toFixed(2), good: riskMetrics.correlationToSpy < 0.8 },
        ].map((r) => (
          <div key={r.label} className="glass-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">{r.label}</p>
            <p className={`text-lg font-bold ${r.good ? 'text-emerald-400' : 'text-hive-text'}`}>{r.value}</p>
          </div>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* VaR Breakdown Bar Chart                             */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="glass-card p-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4">Value at Risk Breakdown</p>
        <div className="space-y-3">
          {[
            { label: 'VaR 95%', value: riskMetrics.var95, color: 'bg-amber-500/50', textColor: 'text-amber-400' },
            { label: 'VaR 99%', value: riskMetrics.var99, color: 'bg-orange-500/50', textColor: 'text-orange-400' },
            { label: 'CVaR (Expected Shortfall)', value: riskMetrics.cvar, color: 'bg-red-500/50', textColor: 'text-red-400' },
          ].map((item) => {
            const width = (item.value / varMax) * 100;
            return (
              <div key={item.label} className="flex items-center gap-3">
                <span className="text-xs text-hive-muted w-44 shrink-0">{item.label}</span>
                <div className="flex-1 h-6 bg-white/[0.03] rounded overflow-hidden">
                  <div className={`h-full rounded ${item.color} flex items-center pl-2`} style={{ width: `${width}%` }}>
                    <span className="text-[10px] font-bold text-white/80">${item.value.toLocaleString()}</span>
                  </div>
                </div>
                <span className={`text-sm font-bold w-20 text-right ${item.textColor}`}>
                  ${item.value.toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-[10px] text-hive-muted mt-3">CVaR represents expected loss in the worst 1% of scenarios (tail risk).</p>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Stress Test Results                                 */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-white/[0.06]">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted flex items-center gap-1.5">
            <Zap size={11} /> Stress Test Results
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
                <th className="text-left px-4 py-2.5">Scenario</th>
                <th className="text-right px-4 py-2.5">Impact ($)</th>
                <th className="text-right px-4 py-2.5">Impact (%)</th>
                <th className="text-center px-4 py-2.5">Severity</th>
              </tr>
            </thead>
            <tbody>
              {stressTests.map((t) => (
                <tr key={t.scenario} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 text-sm font-medium">{t.scenario}</td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-red-400">
                    -${Math.abs(t.impactDollar).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-bold text-red-400">
                    {t.impactPct}%
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${severityColor(t.severity)}`}>
                      {t.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Sector Limit Enforcement + Correlation Heatmap      */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Sector Exposure Enforcement */}
        <div className="glass-card p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4 flex items-center gap-1.5">
            <Shield size={11} /> Sector Limit Enforcement
          </p>
          <div className="space-y-3">
            {sectorExposure.map((s) => {
              const breached = s.pct > s.limit;
              return (
                <div key={s.sector} className="flex items-center gap-3">
                  <span className="text-xs font-medium w-28 shrink-0">{s.sector}</span>
                  <div className="flex-1 h-3 bg-white/[0.04] rounded-full overflow-hidden relative">
                    <div
                      className={`h-full rounded-full ${breached ? 'bg-red-500/60' : 'bg-emerald-500/40'}`}
                      style={{ width: `${Math.min((s.pct / s.limit) * 100, 100)}%` }}
                    />
                  </div>
                  <span className={`text-[10px] font-bold w-20 text-right ${breached ? 'text-red-400' : 'text-emerald-400'}`}>
                    {s.pct}% / {s.limit}%
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${breached ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                    {breached ? 'BREACH' : 'OK'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Correlation Heatmap */}
        <div className="glass-card p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4 flex items-center gap-1.5">
            <PieChart size={11} /> Correlation Heatmap
          </p>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="px-1 py-1 text-[10px] text-hive-muted w-12" />
                  {corrSymbols.map((s) => (
                    <th key={s} className="px-1 py-1 text-[10px] font-bold text-hive-muted text-center w-14">{s}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {corrMatrix.map((row, i) => (
                  <tr key={corrSymbols[i]}>
                    <td className="px-1 py-1 text-[10px] font-bold text-hive-muted">{corrSymbols[i]}</td>
                    {row.map((val, j) => (
                      <td key={j} className="px-1 py-1 text-center">
                        <div className={`rounded px-1 py-1.5 text-[10px] font-bold ${i === j ? 'bg-white/[0.06] text-white/40' : corrCellColor(val)}`}>
                          {val.toFixed(2)}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-3 mt-3 text-[10px] text-hive-muted flex-wrap">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-500/40 rounded" /> High (&ge;0.9)</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-orange-500/30 rounded" /> Medium (&ge;0.7)</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-500/20 rounded" /> Moderate</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500/15 rounded" /> Low</span>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Circuit Breaker Status                              */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-white/[0.06]">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted flex items-center gap-1.5">
            <Power size={11} /> Circuit Breaker Status
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.06]">
          {circuitBreakers.map((cb) => {
            const statusStyles: Record<string, string> = {
              ACTIVE: 'text-emerald-400 bg-emerald-500/10',
              TRIGGERED: 'text-red-400 bg-red-500/10',
              DISABLED: 'text-zinc-500 bg-zinc-500/10',
            };
            const dotStyles: Record<string, string> = {
              ACTIVE: 'bg-emerald-400',
              TRIGGERED: 'bg-red-400 animate-pulse',
              DISABLED: 'bg-zinc-600',
            };
            return (
              <div key={cb.name} className="p-4 flex flex-col items-center text-center gap-2">
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${dotStyles[cb.status]}`} />
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${statusStyles[cb.status]}`}>
                    {cb.status}
                  </span>
                </div>
                <p className="text-xs font-semibold">{cb.name}</p>
                <p className="text-[10px] text-hive-muted">Threshold: {cb.threshold}</p>
                <p className="text-[10px] text-zinc-400">Current: {cb.current}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Risk Budget per Team                                */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="glass-card p-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4 flex items-center gap-1.5">
          <BarChart3 size={11} /> Risk Budget Allocation vs Usage
        </p>
        <div className="space-y-3">
          {riskBudget.map((t) => {
            const overBudget = t.used > t.allocated;
            return (
              <div key={t.team}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium">{t.team}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold ${overBudget ? 'text-red-400' : 'text-emerald-400'}`}>
                      {t.used}% / {t.allocated}%
                    </span>
                    {overBudget && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">OVER</span>
                    )}
                  </div>
                </div>
                <div className="h-3 bg-white/[0.04] rounded-full overflow-hidden relative">
                  <div className="absolute inset-y-0 left-0 bg-white/[0.04] rounded-full" style={{ width: `${t.allocated}%` }} />
                  <div
                    className={`h-full rounded-full relative z-10 ${overBudget ? 'bg-red-500/60' : `${t.color}/50`}`}
                    style={{ width: `${t.used}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-3 text-[10px] text-hive-muted">
          <span className="flex items-center gap-1"><span className="w-3 h-1.5 bg-white/[0.06] rounded" /> Allocated</span>
          <span className="flex items-center gap-1"><span className="w-3 h-1.5 bg-blue-500/50 rounded" /> Used</span>
          <span className="flex items-center gap-1"><span className="w-3 h-1.5 bg-red-500/60 rounded" /> Over Budget</span>
        </div>
      </div>
    </div>
  );
}
