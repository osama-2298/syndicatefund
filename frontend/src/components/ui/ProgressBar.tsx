export default function ProgressBar({
  value,
  max = 100,
  color = 'bg-syn-accent',
  className = '',
  showLabel = false,
}: {
  value: number;
  max?: number;
  color?: string;
  className?: string;
  showLabel?: boolean;
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex-1 h-1.5 bg-syn-border-subtle rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      {showLabel && <span className="text-xs font-mono tabular-nums text-syn-text-secondary">{Math.round(pct)}%</span>}
    </div>
  );
}
