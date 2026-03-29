'use client';

import { usePathname } from 'next/navigation';
import { BarChart3, Bitcoin } from 'lucide-react';

export default function MarketSwitcher() {
  const pathname = usePathname();
  const isStocks = pathname.startsWith('/stocks');

  return (
    <div className="flex items-center bg-white/[0.04] rounded-lg p-0.5 border border-white/[0.06]">
      <a
        href="/"
        className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
          !isStocks
            ? 'bg-amber-500/15 text-amber-400 ring-1 ring-inset ring-amber-500/20'
            : 'text-syn-text-secondary hover:text-syn-text'
        }`}
      >
        <Bitcoin size={12} />
        Crypto
      </a>
      <a
        href="/stocks"
        className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
          isStocks
            ? 'bg-blue-500/15 text-blue-400 ring-1 ring-inset ring-blue-500/20'
            : 'text-syn-text-secondary hover:text-syn-text'
        }`}
      >
        <BarChart3 size={12} />
        Stocks
      </a>
    </div>
  );
}
