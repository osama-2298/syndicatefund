'use client';

import { useEffect, useState, useRef } from 'react';

export default function AnimatedNumber({
  value,
  prefix = '$',
  decimals = 0,
}: {
  value: number;
  prefix?: string;
  decimals?: number;
}) {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);

  useEffect(() => {
    const start = prevRef.current;
    prevRef.current = value;
    const startTime = performance.now();
    const duration = 800;
    let raf: number;
    const animate = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(start + (value - start) * eased);
      if (progress < 1) raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return (
    <span className="tabular-nums font-mono">
      {prefix}{display.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
    </span>
  );
}
