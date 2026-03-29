/**
 * Wilson score interval for binomial proportion.
 * Returns [lower, upper] bounds at given confidence level.
 */
export function wilsonInterval(correct: number, total: number, z = 1.96): [number, number] {
  if (total === 0) return [0, 0];
  const p = correct / total;
  const denom = 1 + (z * z) / total;
  const centre = (p + (z * z) / (2 * total)) / denom;
  const spread = (z / denom) * Math.sqrt((p * (1 - p)) / total + (z * z) / (4 * total * total));
  return [Math.max(0, centre - spread), Math.min(1, centre + spread)];
}

/**
 * Format accuracy with confidence interval.
 * e.g., "62% (48-76%)" with n=45 signals
 */
export function formatAccuracyCI(accuracy: number, total: number, minSignals = 5): string {
  if (total < minSignals) return '—';
  const pct = Math.round(accuracy * 100);
  const correct = Math.round(accuracy * total);
  const [lo, hi] = wilsonInterval(correct, total);
  const loPct = Math.round(lo * 100);
  const hiPct = Math.round(hi * 100);
  return `${pct}% (${loPct}-${hiPct}%)`;
}
