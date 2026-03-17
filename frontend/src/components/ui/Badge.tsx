import { type ReactNode } from 'react';

const colorMap: Record<string, string> = {
  violet: 'text-violet-400 bg-violet-400/10 ring-violet-400/20',
  emerald: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20',
  red: 'text-red-400 bg-red-400/10 ring-red-400/20',
  amber: 'text-amber-400 bg-amber-400/10 ring-amber-400/20',
  blue: 'text-blue-400 bg-blue-400/10 ring-blue-400/20',
  cyan: 'text-cyan-400 bg-cyan-400/10 ring-cyan-400/20',
  purple: 'text-purple-400 bg-purple-400/10 ring-purple-400/20',
  orange: 'text-orange-400 bg-orange-400/10 ring-orange-400/20',
  gray: 'text-gray-400 bg-gray-400/10 ring-gray-400/20',
  rose: 'text-rose-400 bg-rose-400/10 ring-rose-400/20',
  indigo: 'text-indigo-400 bg-indigo-400/10 ring-indigo-400/20',
  fuchsia: 'text-fuchsia-400 bg-fuchsia-400/10 ring-fuchsia-400/20',
  sky: 'text-sky-400 bg-sky-400/10 ring-sky-400/20',
  neutral: 'text-neutral-400 bg-neutral-400/10 ring-neutral-400/20',
};

export default function Badge({
  children,
  color = 'gray',
  className = '',
}: {
  children: ReactNode;
  color?: string;
  className?: string;
}) {
  const colorClass = colorMap[color] || colorMap.gray;
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${colorClass} ${className}`}>
      {children}
    </span>
  );
}
