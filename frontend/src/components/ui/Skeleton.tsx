export default function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-syn-border/50 rounded ${className}`} />
  );
}
