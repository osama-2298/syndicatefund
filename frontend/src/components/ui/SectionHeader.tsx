import { type ReactNode } from 'react';

export default function SectionHeader({
  label,
  badge,
  color = 'text-syn-accent/60',
}: {
  label: string;
  badge?: ReactNode;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-px flex-1 bg-syn-border-subtle" />
      <span className={`text-[10px] font-bold uppercase tracking-[0.2em] ${color}`}>{label}</span>
      {badge}
      <div className="h-px flex-1 bg-syn-border-subtle" />
    </div>
  );
}
