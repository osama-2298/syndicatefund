import { type ReactNode } from 'react';

export default function EmptyState({
  icon,
  message,
  detail,
  action,
}: {
  icon: ReactNode;
  message: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <div className="bg-syn-surface border border-syn-border rounded-lg p-10 text-center">
      <div className="mb-3 flex justify-center text-syn-text-tertiary">{icon}</div>
      <p className="text-sm text-syn-text-secondary font-medium">{message}</p>
      {detail && <p className="text-xs text-syn-muted mt-1">{detail}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
