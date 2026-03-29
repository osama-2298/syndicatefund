'use client';

import { useState, useEffect, useRef } from 'react';
import { Bell, X, AlertTriangle, TrendingUp, Shield, Cpu, CheckCheck, Trash2 } from 'lucide-react';

// ── Types ──

type AlertType = 'PRICE' | 'RISK' | 'TRADE' | 'SYSTEM';
type Severity = 'INFO' | 'WARNING' | 'CRITICAL';

interface Alert {
  id: string;
  type: AlertType;
  severity: Severity;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

// ── Demo Alerts ──

const initialAlerts: Alert[] = [
  {
    id: 'a1',
    type: 'RISK',
    severity: 'CRITICAL',
    title: 'VaR Limit Breach',
    message: 'Portfolio 1-day VaR ($142K) exceeds 95% threshold ($125K). Auto-deleveraging triggered for 2 positions.',
    timestamp: '2 min ago',
    read: false,
  },
  {
    id: 'a2',
    type: 'TRADE',
    severity: 'INFO',
    title: 'Trade Executed: NVDA LONG',
    message: 'Bought 12 shares NVDA @ $912.50. Conviction 8/10. Consensus 83%. SL $845 / TP $985.',
    timestamp: '14 min ago',
    read: false,
  },
  {
    id: 'a3',
    type: 'PRICE',
    severity: 'WARNING',
    title: 'AAPL Target Hit',
    message: 'AAPL crossed $180 price alert. Current: $180.25 (+1.8%). Consider profit-taking on partial position.',
    timestamp: '38 min ago',
    read: false,
  },
  {
    id: 'a4',
    type: 'RISK',
    severity: 'WARNING',
    title: 'Sector Concentration Warning',
    message: 'Technology sector exposure at 42% (limit: 40%). Reduce TECH allocation by ~$8K to comply.',
    timestamp: '1 hr ago',
    read: false,
  },
  {
    id: 'a5',
    type: 'TRADE',
    severity: 'INFO',
    title: 'Trade Closed: META +3.19%',
    message: 'Sold 15 shares META @ $518 (TP1 hit). P&L: +$240. Hold time: 3 days.',
    timestamp: '2 hr ago',
    read: false,
  },
  {
    id: 'a6',
    type: 'SYSTEM',
    severity: 'INFO',
    title: 'Market Data Feed Restored',
    message: 'Real-time feed reconnected after 12s interruption. No missed ticks. All agents re-synced.',
    timestamp: '3 hr ago',
    read: true,
  },
  {
    id: 'a7',
    type: 'PRICE',
    severity: 'INFO',
    title: 'BTC Breakout Alert',
    message: 'BTC broke above $68,000 resistance with volume confirmation. Momentum agents monitoring for continuation.',
    timestamp: '4 hr ago',
    read: true,
  },
  {
    id: 'a8',
    type: 'RISK',
    severity: 'CRITICAL',
    title: 'Max Drawdown Warning',
    message: 'Portfolio drawdown reached -6.8% (alert threshold: -5%). Risk manager reviewing all open positions.',
    timestamp: '5 hr ago',
    read: true,
  },
  {
    id: 'a9',
    type: 'SYSTEM',
    severity: 'WARNING',
    title: 'Earnings Blackout: AMZN',
    message: 'AMZN enters earnings blackout window. All pending AMZN orders cancelled. Resume after 2026-04-01.',
    timestamp: '6 hr ago',
    read: true,
  },
];

// ── Styles ──

const typeConfig: Record<AlertType, { icon: React.ReactNode; color: string; bg: string }> = {
  PRICE: { icon: <TrendingUp size={12} />, color: 'text-blue-400', bg: 'bg-blue-500/10 ring-blue-500/20' },
  RISK: { icon: <Shield size={12} />, color: 'text-red-400', bg: 'bg-red-500/10 ring-red-500/20' },
  TRADE: { icon: <AlertTriangle size={12} />, color: 'text-emerald-400', bg: 'bg-emerald-500/10 ring-emerald-500/20' },
  SYSTEM: { icon: <Cpu size={12} />, color: 'text-amber-400', bg: 'bg-amber-500/10 ring-amber-500/20' },
};

const severityBadge: Record<Severity, string> = {
  INFO: 'bg-syn-elevated text-syn-muted',
  WARNING: 'bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/20',
  CRITICAL: 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20',
};

// ── Component ──

export function AlertsBell() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>(initialAlerts);
  const panelRef = useRef<HTMLDivElement>(null);

  const unreadCount = alerts.filter((a) => !a.read).length;

  // Close on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    if (open) window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open]);

  const markAllRead = () => {
    setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
  };

  const dismissAlert = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const markRead = (id: string) => {
    setAlerts((prev) => prev.map((a) => a.id === id ? { ...a, read: true } : a));
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell Button */}
      <button
        onClick={() => { setOpen(!open); }}
        className="relative p-2 rounded-lg hover:bg-white/[0.06] transition-colors text-syn-muted hover:text-syn-text"
        title="Alerts & Notifications"
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 flex items-center justify-center text-[9px] font-bold bg-red-500 text-white rounded-full px-1">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Slide-out Panel */}
      {open && (
        <>
          {/* Mobile backdrop */}
          <div className="fixed inset-0 bg-black/40 z-[90] sm:hidden" onClick={() => setOpen(false)} />

          <div className="fixed right-0 top-0 h-full w-full sm:w-96 bg-syn-surface border-l border-syn-border z-[95] shadow-2xl animate-slide-in-right overflow-hidden flex flex-col">
            {/* Panel Header */}
            <div className="px-4 py-3 border-b border-syn-border flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <Bell size={14} className="text-syn-accent" />
                <h3 className="text-sm font-semibold">Notifications</h3>
                {unreadCount > 0 && (
                  <span className="text-[10px] font-bold bg-syn-accent/20 text-syn-accent px-2 py-0.5 rounded-full">
                    {unreadCount} new
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllRead}
                    className="flex items-center gap-1 text-[10px] text-syn-muted hover:text-syn-text px-2 py-1 rounded hover:bg-white/[0.04] transition-colors"
                    title="Mark all as read"
                  >
                    <CheckCheck size={12} /> Read all
                  </button>
                )}
                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded hover:bg-white/[0.06] transition-colors text-syn-muted hover:text-syn-text"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Alert List */}
            <div className="flex-1 overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-syn-muted">
                  <Bell size={24} className="mb-2 opacity-30" />
                  <p className="text-sm">No notifications</p>
                </div>
              ) : (
                <div className="divide-y divide-white/[0.03]">
                  {alerts.map((alert) => {
                    const cfg = typeConfig[alert.type];
                    return (
                      <div
                        key={alert.id}
                        onClick={() => markRead(alert.id)}
                        className={`px-4 py-3 hover:bg-white/[0.02] transition-colors cursor-pointer group ${
                          !alert.read ? 'bg-white/[0.01]' : ''
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {/* Type icon */}
                          <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ring-1 ${cfg.bg} ${cfg.color} mt-0.5`}>
                            {cfg.icon}
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className="text-xs font-semibold truncate">{alert.title}</span>
                              {!alert.read && (
                                <span className="w-1.5 h-1.5 rounded-full bg-syn-accent shrink-0" />
                              )}
                            </div>
                            <p className="text-[11px] text-syn-muted leading-relaxed">{alert.message}</p>
                            <div className="flex items-center gap-2 mt-1.5">
                              <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${severityBadge[alert.severity]}`}>
                                {alert.severity}
                              </span>
                              <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ring-1 ${cfg.bg} ${cfg.color}`}>
                                {alert.type}
                              </span>
                              <span className="text-[10px] text-syn-text-tertiary ml-auto">{alert.timestamp}</span>
                            </div>
                          </div>

                          {/* Dismiss */}
                          <button
                            onClick={(e) => { e.stopPropagation(); dismissAlert(alert.id); }}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-syn-muted hover:text-red-400 transition-all shrink-0"
                            title="Dismiss"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer disclaimer */}
            <div className="px-4 py-2 border-t border-syn-border text-[9px] text-syn-text-tertiary text-center shrink-0">
              AI-generated alerts for demonstration purposes only
            </div>
          </div>

          <style jsx>{`
            @keyframes slide-in-right {
              from { transform: translateX(100%); }
              to { transform: translateX(0); }
            }
            .animate-slide-in-right { animation: slide-in-right 0.25s ease-out; }
          `}</style>
        </>
      )}
    </div>
  );
}

export default function AlertsPanel() {
  return <AlertsBell />;
}
