'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';

const disclosures = [
  {
    title: 'Investment Risks',
    content:
      'All investments involve risk, including the possible loss of principal. The value of investments may fluctuate and, as a result, you may receive more or less than your original investment upon redemption. Past performance is not indicative of future results. There is no guarantee that any investment strategy will achieve its objectives, generate profits, or avoid losses. Market conditions and economic factors may materially affect investment outcomes.',
  },
  {
    title: 'AI / Algorithm Risks',
    content:
      'This platform uses artificial intelligence and algorithmic models to generate trading signals and manage portfolio risk. AI models are trained on historical data and may not accurately predict future market conditions. Algorithmic strategies may experience periods of significant underperformance, especially during unusual market events, black swan scenarios, or regime changes not represented in training data. Model outputs should not be considered investment advice.',
  },
  {
    title: 'Cryptocurrency & Volatility Risks',
    content:
      'Cryptocurrency and digital asset markets are highly volatile and subject to rapid price swings. Digital assets are not backed by any government and are not subject to the same regulatory protections as traditional securities. Exchange failures, hacks, regulatory changes, and technological vulnerabilities may result in total loss of capital. Leveraged positions amplify both gains and losses.',
  },
  {
    title: 'Past Performance Warning',
    content:
      'Past performance, whether actual or indicated by historical tests of strategies, is not indicative of future results. Results shown may be based on backtesting or paper trading simulations and do not represent actual trading. Simulated performance results have certain inherent limitations including hindsight bias, and they do not involve financial risk. No representation is made that any account will or is likely to achieve profits or losses similar to those shown.',
  },
];

export function RiskDisclosure() {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const toggle = (i: number) => {
    setExpandedIndex(expandedIndex === i ? null : i);
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-3 border-b border-white/[0.06] flex items-center gap-2">
        <AlertTriangle size={12} className="text-amber-400" />
        <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">
          Risk Disclosures
        </p>
      </div>
      <div className="divide-y divide-white/[0.06]">
        {disclosures.map((d, i) => (
          <div key={d.title}>
            <button
              onClick={() => toggle(i)}
              className="w-full flex items-center justify-between px-5 py-3 hover:bg-white/[0.02] transition-colors text-left"
            >
              <span className="text-xs font-semibold text-syn-text">{d.title}</span>
              {expandedIndex === i ? (
                <ChevronDown size={14} className="text-syn-muted shrink-0" />
              ) : (
                <ChevronRight size={14} className="text-syn-muted shrink-0" />
              )}
            </button>
            {expandedIndex === i && (
              <div className="px-5 pb-4">
                <p className="text-xs text-syn-text-secondary leading-relaxed">{d.content}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
