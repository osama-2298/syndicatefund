import { type ReactNode } from 'react';

const variants = {
  primary: 'bg-syn-accent text-white hover:bg-syn-accent-hover',
  secondary: 'bg-transparent text-syn-text-secondary border border-syn-border hover:bg-syn-surface hover:text-syn-text',
  danger: 'bg-syn-danger/10 text-syn-danger border border-syn-danger/20 hover:bg-syn-danger/20',
  ghost: 'bg-transparent text-syn-text-secondary hover:bg-syn-surface hover:text-syn-text',
};

const sizes = {
  sm: 'text-xs px-3 py-1.5',
  md: 'text-sm px-5 py-2.5',
  lg: 'text-sm px-7 py-3.5',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  ...props
}: {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  children: ReactNode;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
