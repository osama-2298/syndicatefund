'use client';

import { useState } from 'react';
import {
  Shield, AlertTriangle, Eye, Clock, Activity, UserCheck,
  ChevronDown, ChevronRight, OctagonX, Search, BarChart3,
  HeartPulse, Bot, FileText, Lock, Siren,
} from 'lucide-react';
import { DemoBanner } from '@/components/DemoBanner';
import { RiskDisclosure } from '@/components/RiskDisclosure';
import { ComplianceFooter } from '@/components/ComplianceFooter';

// ── KYC / AML Data ──

const kycStats = {
  verified: 1_842,
  pending: 23,
  flagged: 4,
  total: 1_869,
};

// ── Audit Trail ──

const auditTrail = [
  { id: 1, actor: 'System', action: 'Circuit breaker check passed', timestamp: '2026-03-28 14:32:01', type: 'SYSTEM' },
  { id: 2, actor: 'Risk Engine', action: 'VaR recalculated: $2,180 (95%)', timestamp: '2026-03-28 14:30:00', type: 'RISK' },
  { id: 3, actor: 'Compliance Bot', action: 'Wash trade scan completed — 0 alerts', timestamp: '2026-03-28 14:28:45', type: 'SURVEILLANCE' },
  { id: 4, actor: 'Admin', action: 'Updated sector exposure limit: Tech 50% -> 55%', timestamp: '2026-03-28 14:15:22', type: 'CONFIG' },
  { id: 5, actor: 'Risk Engine', action: 'Portfolio rebalance signal emitted', timestamp: '2026-03-28 14:10:00', type: 'RISK' },
  { id: 6, actor: 'System', action: 'Daily KYC batch verification: 12 accounts processed', timestamp: '2026-03-28 14:00:00', type: 'KYC' },
  { id: 7, actor: 'Compliance Bot', action: 'Spoofing detection sweep — 1 alert generated', timestamp: '2026-03-28 13:55:30', type: 'SURVEILLANCE' },
  { id: 8, actor: 'System', action: 'Heartbeat: all 6 subsystems operational', timestamp: '2026-03-28 13:50:00', type: 'SYSTEM' },
  { id: 9, actor: 'Risk Engine', action: 'Drawdown threshold 60% utilization', timestamp: '2026-03-28 13:45:12', type: 'RISK' },
  { id: 10, actor: 'Admin', action: 'Emergency halt test — dry run successful', timestamp: '2026-03-28 13:30:00', type: 'CONFIG' },
  { id: 11, actor: 'Compliance Bot', action: 'Concentration check: NVDA 28.9% (limit 30%)', timestamp: '2026-03-28 13:25:00', type: 'SURVEILLANCE' },
  { id: 12, actor: 'System', action: 'API rate limit audit — within bounds', timestamp: '2026-03-28 13:20:00', type: 'SYSTEM' },
  { id: 13, actor: 'Risk Engine', action: 'Correlation matrix updated', timestamp: '2026-03-28 13:15:00', type: 'RISK' },
  { id: 14, actor: 'System', action: 'Database backup completed', timestamp: '2026-03-28 13:00:00', type: 'SYSTEM' },
  { id: 15, actor: 'Admin', action: 'User role updated: analyst -> senior_analyst', timestamp: '2026-03-28 12:45:00', type: 'CONFIG' },
  { id: 16, actor: 'Compliance Bot', action: 'AML screening batch: 0 matches', timestamp: '2026-03-28 12:30:00', type: 'KYC' },
  { id: 17, actor: 'System', action: 'TLS certificate check — valid for 248 days', timestamp: '2026-03-28 12:15:00', type: 'SYSTEM' },
  { id: 18, actor: 'Risk Engine', action: 'Stress test suite executed (6 scenarios)', timestamp: '2026-03-28 12:00:00', type: 'RISK' },
  { id: 19, actor: 'System', action: 'Log rotation completed', timestamp: '2026-03-28 11:45:00', type: 'SYSTEM' },
  { id: 20, actor: 'Admin', action: 'Compliance report generated for Q1 2026', timestamp: '2026-03-28 11:30:00', type: 'CONFIG' },
];

// ── Surveillance Alerts ──

const surveillanceAlerts = [
  { id: 1, type: 'WASH TRADE', description: 'Rapid buy-sell pattern detected on TSLA (3 round trips in 5 min)', severity: 'HIGH', timestamp: '14:28', status: 'INVESTIGATING' },
  { id: 2, type: 'SPOOFING', description: 'Large order placed and cancelled within 200ms on NVDA', severity: 'CRITICAL', timestamp: '13:55', status: 'OPEN' },
  { id: 3, type: 'CONCENTRATION', description: 'NVDA position at 28.9% — approaching 30% limit', severity: 'MEDIUM', timestamp: '13:25', status: 'MONITORING' },
  { id: 4, type: 'WASH TRADE', description: 'Potential wash trade flagged on AAPL — under review', severity: 'LOW', timestamp: '12:10', status: 'DISMISSED' },
  { id: 5, type: 'CONCENTRATION', description: 'Technology sector at 48.2% — above 25% advisory', severity: 'MEDIUM', timestamp: '11:45', status: 'ACKNOWLEDGED' },
];

// ── Trade Surveillance Summary ──

const alertsByType = [
  { type: 'Wash Trade', count: 12, color: 'bg-red-500' },
  { type: 'Spoofing', count: 3, color: 'bg-orange-500' },
  { type: 'Concentration', count: 28, color: 'bg-amber-500' },
  { type: 'Front Running', count: 0, color: 'bg-blue-500' },
  { type: 'Layering', count: 1, color: 'bg-purple-500' },
];

// ── System Health ──

const systemHealth = [
  { name: 'Trading Engine', status: 'HEALTHY', latency: '12ms', uptime: '99.99%' },
  { name: 'Risk Engine', status: 'HEALTHY', latency: '45ms', uptime: '99.97%' },
  { name: 'Market Data Feed', status: 'HEALTHY', latency: '3ms', uptime: '99.99%' },
  { name: 'Compliance Scanner', status: 'HEALTHY', latency: '120ms', uptime: '99.95%' },
  { name: 'Database Cluster', status: 'HEALTHY', latency: '8ms', uptime: '100%' },
  { name: 'Auth Service', status: 'DEGRADED', latency: '340ms', uptime: '99.82%' },
];

const severityColor = (severity: string) => {
  if (severity === 'CRITICAL') return 'text-red-400 bg-red-500/10';
  if (severity === 'HIGH') return 'text-orange-400 bg-orange-500/10';
  if (severity === 'MEDIUM') return 'text-amber-400 bg-amber-500/10';
  return 'text-emerald-400 bg-emerald-500/10';
};

const statusColor = (status: string) => {
  if (status === 'OPEN' || status === 'INVESTIGATING') return 'text-red-400 bg-red-500/10';
  if (status === 'MONITORING') return 'text-amber-400 bg-amber-500/10';
  if (status === 'ACKNOWLEDGED') return 'text-blue-400 bg-blue-500/10';
  return 'text-zinc-500 bg-zinc-500/10';
};

const auditTypeColor = (type: string) => {
  if (type === 'SURVEILLANCE') return 'text-red-400 bg-red-500/10';
  if (type === 'RISK') return 'text-amber-400 bg-amber-500/10';
  if (type === 'KYC') return 'text-emerald-400 bg-emerald-500/10';
  if (type === 'CONFIG') return 'text-purple-400 bg-purple-500/10';
  return 'text-blue-400 bg-blue-500/10';
};

export default function CompliancePage() {
  const [haltConfirmOpen, setHaltConfirmOpen] = useState(false);
  const [haltTriggered, setHaltTriggered] = useState(false);
  const maxAlertCount = Math.max(...alertsByType.map(a => a.count), 1);

  return (
    <div className="slide-up space-y-6 pb-0">
      <DemoBanner />
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Compliance Dashboard</h1>
        <p className="text-sm text-hive-muted mt-1">KYC/AML, surveillance, audit trail, system health</p>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* KYC / AML Status                                    */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Accounts', value: kycStats.total.toLocaleString(), icon: UserCheck, color: 'text-hive-text' },
          { label: 'KYC Verified', value: kycStats.verified.toLocaleString(), icon: Shield, color: 'text-emerald-400' },
          { label: 'Pending Review', value: kycStats.pending.toString(), icon: Clock, color: 'text-amber-400' },
          { label: 'Flagged / Blocked', value: kycStats.flagged.toString(), icon: AlertTriangle, color: 'text-red-400' },
        ].map((m) => (
          <div key={m.label} className="glass-card p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">{m.label}</p>
              <m.icon size={13} className="text-hive-muted" />
            </div>
            <p className={`text-xl font-bold tracking-tight ${m.color}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Emergency Halt                                      */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className={`glass-card p-5 ${haltTriggered ? 'border-red-500/40 bg-red-500/5' : ''}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <OctagonX size={18} className={haltTriggered ? 'text-red-400 animate-pulse' : 'text-red-400'} />
            <div>
              <p className="text-sm font-bold">Emergency Kill Switch</p>
              <p className="text-[10px] text-hive-muted mt-0.5">
                {haltTriggered
                  ? 'ALL TRADING HALTED — Manual restart required'
                  : 'Immediately halt all trading activity across all teams and strategies'}
              </p>
            </div>
          </div>
          {!haltTriggered ? (
            !haltConfirmOpen ? (
              <button
                onClick={() => setHaltConfirmOpen(true)}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-lg transition-colors uppercase tracking-wider"
              >
                HALT ALL TRADING
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-red-400 font-bold">Are you sure?</span>
                <button
                  onClick={() => { setHaltTriggered(true); setHaltConfirmOpen(false); }}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-[10px] font-bold rounded transition-colors"
                >
                  CONFIRM HALT
                </button>
                <button
                  onClick={() => setHaltConfirmOpen(false)}
                  className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 text-white text-[10px] font-bold rounded transition-colors"
                >
                  CANCEL
                </button>
              </div>
            )
          ) : (
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
              <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">HALTED</span>
            </div>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Surveillance Alerts                                 */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-white/[0.06] flex items-center gap-2">
          <Eye size={12} className="text-amber-400" />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Surveillance Alerts</p>
          <span className="ml-auto text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400">
            {surveillanceAlerts.filter(a => a.status === 'OPEN' || a.status === 'INVESTIGATING').length} ACTIVE
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
                <th className="text-left px-4 py-2.5">Type</th>
                <th className="text-left px-4 py-2.5">Description</th>
                <th className="text-center px-4 py-2.5">Severity</th>
                <th className="text-center px-4 py-2.5">Status</th>
                <th className="text-right px-4 py-2.5">Time</th>
              </tr>
            </thead>
            <tbody>
              {surveillanceAlerts.map((a) => (
                <tr key={a.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white/[0.06] text-white/70">
                      {a.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-hive-muted max-w-xs">{a.description}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${severityColor(a.severity)}`}>
                      {a.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${statusColor(a.status)}`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-[10px] text-hive-muted font-mono">{a.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Trade Surveillance Summary + System Health          */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Alerts by Type chart */}
        <div className="glass-card p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4 flex items-center gap-1.5">
            <BarChart3 size={11} /> Alerts by Type (Last 30 Days)
          </p>
          <div className="space-y-3">
            {alertsByType.map((a) => (
              <div key={a.type} className="flex items-center gap-3">
                <span className="text-xs text-hive-muted w-28 shrink-0">{a.type}</span>
                <div className="flex-1 h-5 bg-white/[0.03] rounded overflow-hidden">
                  <div
                    className={`h-full rounded ${a.color}/40 flex items-center pl-2`}
                    style={{ width: `${maxAlertCount > 0 ? (a.count / maxAlertCount) * 100 : 0}%` }}
                  >
                    {a.count > 0 && <span className="text-[10px] font-bold text-white/70">{a.count}</span>}
                  </div>
                </div>
                <span className="text-xs font-bold w-8 text-right">{a.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* System Health */}
        <div className="glass-card p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-4 flex items-center gap-1.5">
            <HeartPulse size={11} /> System Health
          </p>
          <div className="space-y-2">
            {systemHealth.map((s) => {
              const isHealthy = s.status === 'HEALTHY';
              return (
                <div key={s.name} className="flex items-center gap-3 py-1.5">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${isHealthy ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
                  <span className="text-xs font-medium flex-1">{s.name}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isHealthy ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                    {s.status}
                  </span>
                  <span className="text-[10px] text-hive-muted w-14 text-right font-mono">{s.latency}</span>
                  <span className="text-[10px] text-hive-muted w-14 text-right">{s.uptime}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Audit Trail                                         */}
      {/* ═══════════════════════════════════════════════════ */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-white/[0.06] flex items-center gap-2">
          <FileText size={12} className="text-blue-400" />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Audit Trail</p>
          <span className="ml-auto text-[10px] text-hive-muted">{auditTrail.length} entries</span>
        </div>
        <div className="max-h-[400px] overflow-y-auto">
          <div className="divide-y divide-white/[0.04]">
            {auditTrail.map((entry) => (
              <div key={entry.id} className="flex items-center gap-3 px-5 py-2.5 hover:bg-white/[0.02] transition-colors">
                <span className="text-[10px] font-mono text-hive-muted w-36 shrink-0">{entry.timestamp}</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 w-24 text-center ${auditTypeColor(entry.type)}`}>
                  {entry.type}
                </span>
                <span className="text-[10px] font-semibold text-zinc-300 w-28 shrink-0">{entry.actor}</span>
                <span className="text-xs text-hive-muted truncate">{entry.action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════ */}
      {/* Regulatory Disclosures                              */}
      {/* ═══════════════════════════════════════════════════ */}
      <RiskDisclosure />

      {/* ═══════════════════════════════════════════════════ */}
      {/* Compliance Footer                                   */}
      {/* ═══════════════════════════════════════════════════ */}
      <ComplianceFooter />
    </div>
  );
}
