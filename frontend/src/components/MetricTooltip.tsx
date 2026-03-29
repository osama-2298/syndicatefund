'use client';

import { useState, useRef, useEffect } from 'react';
import { Info } from 'lucide-react';

// ── Financial Metric Dictionary ──

const metricDictionary: Record<string, { explanation: string; benchmark?: string }> = {
  'Sharpe Ratio': {
    explanation: 'Risk-adjusted return measured as excess return per unit of total volatility. Higher values indicate better risk-adjusted performance.',
    benchmark: '>1.0 good, >2.0 excellent, >3.0 exceptional',
  },
  'Sortino Ratio': {
    explanation: 'Similar to Sharpe but only penalizes downside volatility, giving a clearer picture of harmful risk vs. beneficial volatility.',
    benchmark: '>1.5 good, >2.5 excellent',
  },
  'VaR': {
    explanation: 'Value at Risk: the maximum expected loss over a given time period at a specified confidence level (typically 95% or 99%).',
    benchmark: 'Lower is better. Institutional limit: typically 1-3% of portfolio',
  },
  'CVaR': {
    explanation: 'Conditional Value at Risk (Expected Shortfall): the average loss in the worst-case scenarios beyond the VaR threshold. More conservative than VaR.',
    benchmark: 'Typically 1.2-1.5x the VaR value',
  },
  'Max Drawdown': {
    explanation: 'The largest peak-to-trough decline in portfolio value. Measures the worst historical loss an investor would have experienced.',
    benchmark: '<10% conservative, <20% moderate, >30% aggressive',
  },
  'Win Rate': {
    explanation: 'Percentage of trades that resulted in a profit. Should be evaluated alongside average win/loss size for meaningful context.',
    benchmark: '>50% for trend following, >60% for mean reversion',
  },
  'Profit Factor': {
    explanation: 'Ratio of gross profits to gross losses. A profit factor of 1.5 means $1.50 earned for every $1.00 lost.',
    benchmark: '>1.0 profitable, >1.5 good, >2.0 excellent',
  },
  'Calmar Ratio': {
    explanation: 'Annualized return divided by maximum drawdown. Measures return relative to the worst-case downside risk.',
    benchmark: '>1.0 good, >3.0 excellent',
  },
  'Information Ratio': {
    explanation: 'Active return (excess over benchmark) divided by tracking error. Measures the consistency of outperformance.',
    benchmark: '>0.5 good, >1.0 exceptional',
  },
  'Beta': {
    explanation: 'Sensitivity of portfolio returns to market returns. Beta of 1.0 moves with the market; <1.0 is defensive; >1.0 is aggressive.',
    benchmark: '1.0 = market. <0.8 defensive, >1.2 aggressive',
  },
  'Alpha': {
    explanation: 'Excess return above what would be predicted by the portfolio\'s beta exposure to the market. Positive alpha = outperformance.',
    benchmark: '>0% indicates outperformance vs. benchmark',
  },
  'Correlation': {
    explanation: 'Statistical measure of how two assets move together. Range: -1 (perfect inverse) to +1 (perfect correlation). 0 = no relationship.',
    benchmark: '<0.3 low, 0.3-0.7 moderate, >0.7 high',
  },
  'Volatility': {
    explanation: 'Annualized standard deviation of returns. Measures the dispersion of returns around the mean. Higher = more uncertain.',
    benchmark: '<10% low vol, 10-20% moderate, >20% high vol',
  },
  'Return': {
    explanation: 'Total percentage gain or loss on the portfolio over the measured period, including realized and unrealized gains.',
  },
  'Exposure': {
    explanation: 'Total market exposure as a percentage of portfolio value. Net exposure = long exposure minus short exposure.',
    benchmark: '80-120% typical for long-biased funds',
  },
  'Turnover': {
    explanation: 'Percentage of portfolio traded over a period. Higher turnover means more frequent trading and typically higher transaction costs.',
    benchmark: '<100% annual for low turnover, >500% for HFT',
  },
  'R-Squared': {
    explanation: 'Percentage of portfolio return variance explained by the benchmark. High R-squared means returns closely track the benchmark.',
    benchmark: '>0.85 high correlation to benchmark',
  },
  'Treynor Ratio': {
    explanation: 'Excess return per unit of systematic risk (beta). Unlike Sharpe, only considers market risk, not total risk.',
    benchmark: 'Higher is better; compare to benchmark Treynor',
  },
};

// ── Types ──

interface MetricTooltipProps {
  label: string;
  value: React.ReactNode;
  explanation?: string;
  benchmark?: string;
  children?: React.ReactNode;
}

// ── Component ──

export default function MetricTooltip({ label, value, explanation, benchmark, children }: MetricTooltipProps) {
  const [show, setShow] = useState(false);
  const [position, setPosition] = useState<'top' | 'bottom'>('top');
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Get from dictionary if not provided
  const dict = metricDictionary[label];
  const finalExplanation = explanation || dict?.explanation || `${label}: a financial performance metric.`;
  const finalBenchmark = benchmark || dict?.benchmark;

  // Position tooltip above or below depending on space
  useEffect(() => {
    if (show && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition(rect.top > 200 ? 'top' : 'bottom');
    }
  }, [show]);

  return (
    <div
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children || (
        <div className="cursor-help">
          <div className="flex items-center gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">{label}</span>
            <Info size={10} className="text-syn-text-tertiary" />
          </div>
          <div className="mt-1 text-lg font-bold tracking-tight">{value}</div>
        </div>
      )}

      {/* Tooltip */}
      {show && (
        <div
          ref={tooltipRef}
          className={`absolute z-50 w-72 p-3 rounded-lg bg-syn-elevated border border-syn-border shadow-xl ${
            position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
          } left-1/2 -translate-x-1/2`}
        >
          {/* Arrow */}
          <div
            className={`absolute left-1/2 -translate-x-1/2 w-2 h-2 bg-syn-elevated border-syn-border rotate-45 ${
              position === 'top'
                ? 'bottom-[-5px] border-r border-b'
                : 'top-[-5px] border-l border-t'
            }`}
          />

          <div className="relative">
            <p className="text-xs font-semibold text-syn-text mb-1">{label}</p>
            <p className="text-[11px] text-syn-muted leading-relaxed">{finalExplanation}</p>
            {finalBenchmark && (
              <div className="mt-2 pt-2 border-t border-white/[0.06]">
                <p className="text-[10px] text-syn-text-tertiary">
                  <span className="font-semibold text-syn-muted">Benchmark: </span>
                  {finalBenchmark}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
