import { type ReactNode } from 'react';

export default function Card({
  children,
  className = '',
  hover = false,
  ...props
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`bg-syn-surface border border-syn-border rounded-lg ${hover ? 'hover:border-syn-text-tertiary transition-colors' : ''} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
