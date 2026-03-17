import { Loader2 } from 'lucide-react';

export default function LoadingState({ message }: { message?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex items-center gap-3">
        <Loader2 size={20} className="animate-spin text-syn-accent" />
        {message && <p className="text-sm text-syn-text-secondary">{message}</p>}
      </div>
    </div>
  );
}
