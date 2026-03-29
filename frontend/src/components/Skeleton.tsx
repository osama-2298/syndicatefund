'use client';

// ── Base shimmer class ──

const shimmer =
  'relative overflow-hidden bg-syn-elevated rounded before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/[0.04] before:to-transparent before:animate-[shimmer_1.5s_ease-in-out_infinite]';

// ── SkeletonLine ──

export function SkeletonLine({
  width = '100%',
  height = '12px',
  className = '',
}: {
  width?: string;
  height?: string;
  className?: string;
}) {
  return (
    <div
      className={`${shimmer} ${className}`}
      style={{ width, height }}
    />
  );
}

// ── SkeletonCard ──

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`card p-4 space-y-3 ${className}`}>
      <SkeletonLine width="40%" height="10px" />
      <SkeletonLine width="60%" height="20px" />
      <div className="pt-1 space-y-2">
        <SkeletonLine width="100%" height="10px" />
        <SkeletonLine width="80%" height="10px" />
      </div>
    </div>
  );
}

// ── SkeletonTable ──

export function SkeletonTable({
  rowCount = 5,
  colCount = 4,
  className = '',
}: {
  rowCount?: number;
  colCount?: number;
  className?: string;
}) {
  return (
    <div className={`glass-card overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-white/[0.06] flex gap-4">
        {Array.from({ length: colCount }).map((_, i) => (
          <SkeletonLine key={`h-${i}`} width={i === 0 ? '80px' : '60px'} height="8px" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rowCount }).map((_, row) => (
        <div
          key={`r-${row}`}
          className="px-4 py-3 border-b border-white/[0.03] flex gap-4 items-center"
        >
          {Array.from({ length: colCount }).map((_, col) => (
            <SkeletonLine
              key={`c-${col}`}
              width={col === 0 ? '100px' : `${50 + Math.random() * 50}px`}
              height="12px"
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── SkeletonChart ──

export function SkeletonChart({
  height = '200px',
  className = '',
}: {
  height?: string;
  className?: string;
}) {
  return (
    <div className={`card p-4 space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <SkeletonLine width="120px" height="10px" />
        <SkeletonLine width="80px" height="10px" />
      </div>
      <div className={`${shimmer} rounded-lg`} style={{ height }} />
    </div>
  );
}
