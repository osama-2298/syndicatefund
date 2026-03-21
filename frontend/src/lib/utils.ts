// ── Shared utility functions ──
// Extracted from dashboard, results, polymarket, and home pages

/**
 * Format a number as USD currency string.
 * For values >= 1000, omits decimals. Otherwise shows up to 2 decimals.
 */
export function fmtUsd(n: number | undefined | null): string {
  const v = n ?? 0;
  if (Math.abs(v) >= 1000) return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

/**
 * Format a number as a signed percentage string (e.g. "+1.23%" or "-0.45%").
 */
export function fmtPct(n: number | undefined | null): string {
  const v = n ?? 0;
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
}

/**
 * Relative time display (e.g. "just now", "5m ago", "3h ago", "2d ago").
 * Returns '--' for null/undefined input.
 */
export function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return '--';
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 0) return 'just now';
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/**
 * Human-readable exit reason label.
 */
export function exitReasonLabel(reason: string): string {
  const map: Record<string, string> = {
    STOP_LOSS: 'Stop Loss',
    TAKE_PROFIT_1: 'TP1',
    TAKE_PROFIT_2: 'TP2',
    TRAILING_STOP: 'Trail',
    BREAKEVEN_STOP: 'BE Stop',
    TIME_STOP: 'Time',
    OPEN: 'Open',
  };
  return map[reason] || reason;
}
