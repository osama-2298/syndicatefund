import { type ReactNode } from 'react';

export default function StatBlock({
  label,
  value,
  sub,
  icon,
  className = '',
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`bg-syn-surface border border-syn-border rounded-lg px-4 py-3 ${className}`}>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <p className="stat-label">{label}</p>
      </div>
      <div className="stat-value">{value}</div>
      {sub && <div className="text-[10px] text-syn-text-tertiary mt-1">{sub}</div>}
    </div>
  );
}
