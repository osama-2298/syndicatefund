'use client';

import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState, Suspense } from 'react';
import {
  ArrowLeft, Newspaper, TrendingUp, TrendingDown, BarChart3,
  AlertTriangle, Clock, ExternalLink, Shield, Activity, Eye,
  LineChart, Signal, Building2, ChevronRight, Gauge, Globe,
  Users, DollarSign, Calendar, Target, Zap, ShieldAlert,
  ArrowUpRight, ArrowDownRight, Percent, Info,
} from 'lucide-react';

// ── Demo data per stock ─────────────────────────────────────────────────

const stockData: Record<string, {
  name: string;
  sector: string;
  price: number;
  change: number;
  marketCap: string;
  pe: number;
  position: { side: string; shares: number; entry: number; sl: number; tp: number; conviction: number } | null;
  earnings: { date: string; daysAway: number; inBlackout: boolean; beatRate: string; avgSurprise: string } | null;
  shortInterest: string;
  institutionalPct: string;
  news: { headline: string; source: string; time: string; sentiment: 'positive' | 'negative' | 'neutral'; summary: string }[];
  agentSignals: { team: string; direction: string; conviction: number; reasoning: string }[];
}> = {
  aapl: {
    name: 'Apple Inc.',
    sector: 'Technology',
    price: 182.30,
    change: 2.13,
    marketCap: '$2.83T',
    pe: 28.4,
    position: { side: 'BUY', shares: 45, entry: 178.50, sl: 171.20, tp: 195.00, conviction: 7 },
    earnings: { date: '2026-03-19', daysAway: 3, inBlackout: true, beatRate: '92%', avgSurprise: '+6.2%' },
    shortInterest: '0.7%',
    institutionalPct: '61.2%',
    news: [
      { headline: 'Apple Vision Pro 2 enters mass production ahead of WWDC', source: 'Bloomberg', time: '2h ago', sentiment: 'positive', summary: 'Apple has begun mass production of the second-generation Vision Pro headset at Foxconn facilities in China. The device features a lighter design, M4 chip, and improved hand tracking. Launch expected at WWDC 2026 in June.' },
      { headline: 'Apple Services revenue hits all-time high in Q1', source: 'Reuters', time: '5h ago', sentiment: 'positive', summary: 'Apple\'s Services segment generated $26.3B in Q1 2026, a 19% YoY increase driven by Apple TV+, iCloud, and App Store growth. The segment now represents 25% of total revenue with margins above 70%.' },
      { headline: 'EU regulators probe Apple Pay dominance in mobile payments', source: 'Financial Times', time: '1d ago', sentiment: 'negative', summary: 'The European Commission has opened a formal investigation into Apple Pay\'s near-monopoly on NFC payments on iOS devices. Apple could face fines up to 10% of global revenue if found in violation of the Digital Markets Act.' },
      { headline: 'Apple increases dividend by 5%, announces $110B buyback', source: 'CNBC', time: '2d ago', sentiment: 'positive', summary: 'Apple\'s board approved a 5% dividend increase to $1.00/share and a new $110B share repurchase authorization, the largest in corporate history. The company returned $29B to shareholders last quarter.' },
      { headline: 'iPhone 18 leak suggests major camera overhaul with periscope zoom', source: 'MacRumors', time: '2d ago', sentiment: 'neutral', summary: 'Supply chain reports indicate the iPhone 18 lineup will feature a 48MP periscope telephoto lens across all Pro models, along with a new custom image signal processor co-developed with Sony.' },
      { headline: 'Analyst upgrades: Goldman raises AAPL target to $210', source: 'MarketWatch', time: '3d ago', sentiment: 'positive', summary: 'Goldman Sachs analyst Michael Ng raised his price target on Apple from $195 to $210, citing accelerating Services growth and Vision Pro ecosystem expansion as key catalysts for re-rating.' },
    ],
    agentSignals: [
      { team: 'Technical', direction: 'BULLISH', conviction: 7, reasoning: 'Price above SMA200 ($168), RSI 58 trending up, MACD bullish crossover confirmed on daily.' },
      { team: 'Sentiment', direction: 'BULLISH', conviction: 6, reasoning: 'Reddit mentions surging +45% WoW. Put/call ratio 0.72 (neutral-bullish). VIX low at 16.8.' },
      { team: 'Fundamental', direction: 'BULLISH', conviction: 0, reasoning: 'EARNINGS BLACKOUT — 3 days to report. Conviction forced to 0. No new positions allowed.' },
      { team: 'Macro', direction: 'BULLISH', conviction: 5, reasoning: 'Technology sector overweight in current cycle. Fed rate cut expectations supporting growth stocks.' },
      { team: 'Institutional', direction: 'BULLISH', conviction: 7, reasoning: 'Vanguard added 2.1M shares last quarter. Insider buying: Tim Cook purchased $5M in open market.' },
      { team: 'News', direction: 'BULLISH', conviction: 8, reasoning: 'Vision Pro 2 production is a major catalyst. Services ATH confirms recurring revenue thesis. EU probe is manageable risk.' },
    ],
  },
  nvda: {
    name: 'NVIDIA Corporation',
    sector: 'Technology',
    price: 912.50,
    change: 2.53,
    marketCap: '$2.24T',
    pe: 62.1,
    position: { side: 'BUY', shares: 12, entry: 890.00, sl: 845.00, tp: 985.00, conviction: 8 },
    earnings: null,
    shortInterest: '1.1%',
    institutionalPct: '65.8%',
    news: [
      { headline: 'NVIDIA Blackwell Ultra chips see unprecedented demand from hyperscalers', source: 'Reuters', time: '1h ago', sentiment: 'positive', summary: 'Microsoft, Google, and Amazon have collectively ordered over $15B worth of NVIDIA\'s Blackwell Ultra GPUs for 2026 delivery. The chips offer 4x inference performance over H100 at similar power consumption.' },
      { headline: 'Jensen Huang: "AI infrastructure spending will exceed $1T by 2028"', source: 'CNBC', time: '4h ago', sentiment: 'positive', summary: 'Speaking at GTC 2026, NVIDIA CEO Jensen Huang projected global AI infrastructure investment will surpass $1 trillion annually by 2028, with NVIDIA positioned to capture 70-80% of the GPU compute market.' },
      { headline: 'China export restrictions could impact 8% of NVIDIA revenue', source: 'WSJ', time: '8h ago', sentiment: 'negative', summary: 'The Biden administration is considering tightening AI chip export controls to China. NVIDIA estimates the restrictions could affect approximately $5B in annual revenue from Chinese customers.' },
      { headline: 'NVIDIA partners with Toyota for autonomous driving AI platform', source: 'Bloomberg', time: '1d ago', sentiment: 'positive', summary: 'NVIDIA and Toyota announced a strategic partnership to deploy NVIDIA DRIVE Thor across Toyota\'s entire autonomous vehicle lineup starting 2027. The deal is estimated at $2B over 5 years.' },
      { headline: 'AMD Instinct MI400 benchmarks show narrowing gap with NVIDIA H200', source: 'AnandTech', time: '2d ago', sentiment: 'negative', summary: 'Independent benchmarks of AMD\'s upcoming MI400 GPU show it achieving 85-90% of NVIDIA H200 performance on key AI workloads, potentially threatening NVIDIA\'s premium pricing power.' },
    ],
    agentSignals: [
      { team: 'Technical', direction: 'BULLISH', conviction: 8, reasoning: 'Strong uptrend, all timeframes aligned. RSI 64 with room to run. Volume confirming breakout above $900.' },
      { team: 'Sentiment', direction: 'BULLISH', conviction: 7, reasoning: 'Most mentioned stock on r/wallstreetbets. Unusual call activity at $950 strike. VIX supportive.' },
      { team: 'Fundamental', direction: 'BULLISH', conviction: 6, reasoning: 'P/E 62 is high but PEG 1.1 reasonable given 55% earnings growth. Revenue growth accelerating.' },
      { team: 'Macro', direction: 'BULLISH', conviction: 7, reasoning: 'AI capex cycle in early innings. Rate environment supportive of growth. Sector rotation favoring tech.' },
      { team: 'Institutional', direction: 'BULLISH', conviction: 8, reasoning: 'Institutional ownership rising QoQ. No significant insider selling. Short interest minimal at 1.1%.' },
      { team: 'News', direction: 'BULLISH', conviction: 9, reasoning: 'Blackwell Ultra demand is the strongest product cycle signal in years. Toyota deal expands TAM. China risk is priced in.' },
    ],
  },
  msft: {
    name: 'Microsoft Corporation',
    sector: 'Technology',
    price: 421.80,
    change: 1.64,
    marketCap: '$3.13T',
    pe: 34.2,
    position: { side: 'BUY', shares: 25, entry: 415.00, sl: 398.00, tp: 450.00, conviction: 6 },
    earnings: null,
    shortInterest: '0.5%',
    institutionalPct: '72.1%',
    news: [
      { headline: 'Microsoft Azure AI revenue growth accelerates to 65% YoY', source: 'Bloomberg', time: '3h ago', sentiment: 'positive', summary: 'Azure AI services revenue grew 65% year-over-year in Q1 FY2027, with OpenAI-powered offerings driving the majority of new workload migrations from AWS and Google Cloud.' },
      { headline: 'Copilot enterprise adoption surpasses 500K seats', source: 'TechCrunch', time: '6h ago', sentiment: 'positive', summary: 'Microsoft 365 Copilot has been deployed to over 500,000 enterprise seats, generating an estimated $3.6B in annual recurring revenue. Fortune 500 adoption rate is now 42%.' },
      { headline: 'Microsoft faces antitrust scrutiny over Teams bundling in Europe', source: 'Reuters', time: '1d ago', sentiment: 'negative', summary: 'EU antitrust officials are investigating whether Microsoft\'s bundling of Teams with Office 365 violates competition rules, following complaints from Slack and Zoom.' },
      { headline: 'Microsoft acquires cybersecurity startup CrowdAI for $2.3B', source: 'WSJ', time: '2d ago', sentiment: 'positive', summary: 'Microsoft announced the acquisition of CrowdAI, a next-generation threat detection platform, to strengthen its Microsoft Sentinel and Defender product lines.' },
    ],
    agentSignals: [
      { team: 'Technical', direction: 'BULLISH', conviction: 6, reasoning: 'Above SMA200, RSI 54 neutral. MACD slightly positive. Consolidating near highs.' },
      { team: 'Sentiment', direction: 'BULLISH', conviction: 5, reasoning: 'Moderate Reddit mentions. P/C ratio neutral. Institutional flow steady.' },
      { team: 'Fundamental', direction: 'BULLISH', conviction: 7, reasoning: 'P/E 34 reasonable for quality. Azure growth accelerating. FCF yield 2.8% attractive.' },
      { team: 'Macro', direction: 'BULLISH', conviction: 6, reasoning: 'Cloud/AI secular trend intact. Rate environment neutral for mega-cap quality.' },
      { team: 'Institutional', direction: 'BULLISH', conviction: 6, reasoning: '72% institutional ownership, stable. Low short interest. No insider selling signals.' },
      { team: 'News', direction: 'BULLISH', conviction: 7, reasoning: 'Azure AI acceleration and Copilot adoption are strong growth drivers. EU risk is manageable.' },
    ],
  },
  tsla: {
    name: 'Tesla, Inc.',
    sector: 'Consumer Discretionary',
    price: 238.60,
    change: -2.61,
    marketCap: '$758B',
    pe: 58.7,
    position: { side: 'SELL', shares: 20, entry: 245.00, sl: 265.00, tp: 210.00, conviction: 5 },
    earnings: null,
    shortInterest: '3.2%',
    institutionalPct: '44.1%',
    news: [
      { headline: 'Tesla Robotaxi pilot launches in Austin with 200 vehicles', source: 'Bloomberg', time: '2h ago', sentiment: 'positive', summary: 'Tesla has deployed 200 Model 3 vehicles equipped with FSD v13 for a supervised robotaxi pilot in Austin, TX. Rides are free during the pilot phase with plans to charge by Q3 2026.' },
      { headline: 'Model Y sales decline 12% in Europe amid rising competition', source: 'Reuters', time: '7h ago', sentiment: 'negative', summary: 'Tesla Model Y registrations in Europe fell 12% YoY in February, losing market share to BYD Seal U, BMW iX3, and Volkswagen ID.4 as competition intensifies in the EV market.' },
      { headline: 'Elon Musk faces shareholder lawsuit over time allocation to xAI', source: 'WSJ', time: '1d ago', sentiment: 'negative', summary: 'A group of Tesla institutional shareholders filed suit alleging Musk\'s significant time commitment to xAI and other ventures represents a breach of fiduciary duty to Tesla shareholders.' },
      { headline: 'Tesla Megapack orders surge 80% as utility storage demand explodes', source: 'CNBC', time: '1d ago', sentiment: 'positive', summary: 'Tesla Energy\'s Megapack business saw order volume increase 80% QoQ, with the Lathrop factory now producing 40 GWh annually. Energy storage is now Tesla\'s fastest-growing segment.' },
      { headline: 'Short sellers increase Tesla bets as competition narrative builds', source: 'Financial Times', time: '2d ago', sentiment: 'negative', summary: 'Short interest in Tesla rose to 3.2% of float, up from 2.8% last month. Bearish analysts cite declining auto margins, European market share losses, and Musk distraction risk.' },
    ],
    agentSignals: [
      { team: 'Technical', direction: 'BEARISH', conviction: 6, reasoning: 'Below SMA50 ($248), RSI 42 trending down. MACD bearish. Support at $230 being tested.' },
      { team: 'Sentiment', direction: 'BEARISH', conviction: 5, reasoning: 'Mixed WSB sentiment. Rising short interest at 3.2%. Put/call ratio elevated at 1.15.' },
      { team: 'Fundamental', direction: 'BEARISH', conviction: 4, reasoning: 'P/E 58 hard to justify with declining auto margins. Robotaxi/Energy not yet in earnings.' },
      { team: 'Macro', direction: 'BEARISH', conviction: 5, reasoning: 'Consumer discretionary under pressure. Competition narrative weighing on sector rotation.' },
      { team: 'Institutional', direction: 'BEARISH', conviction: 6, reasoning: 'Institutional ownership declining QoQ. Rising short interest. Musk lawsuit adds governance risk.' },
      { team: 'News', direction: 'BEARISH', conviction: 5, reasoning: 'Europe sales decline and Musk lawsuit outweigh Robotaxi pilot. Megapack positive but not enough to offset.' },
    ],
  },
};

const sentimentColor = { positive: 'text-emerald-400', negative: 'text-red-400', neutral: 'text-hive-muted' };
const sentimentBg = { positive: 'bg-emerald-500/10', negative: 'bg-red-500/10', neutral: 'bg-white/[0.04]' };
const sentimentDot = { positive: 'bg-emerald-400', negative: 'bg-red-400', neutral: 'bg-hive-muted' };
const sentimentLabel = { positive: 'Bullish', negative: 'Bearish', neutral: 'Neutral' };

// ── TradingView Widgets ─────────────────────────────────────────────────

function useTheme() {
  const isLight = typeof document !== 'undefined' && document.documentElement.classList.contains('light');
  return isLight ? 'light' : 'dark';
}

function TVWidget({ widgetType, config, height }: { widgetType: string; config: Record<string, any>; height: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const theme = useTheme();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.innerHTML = '';

    const widgetDiv = document.createElement('div');
    widgetDiv.className = 'tradingview-widget-container__widget';
    widgetDiv.style.height = height + 'px';
    widgetDiv.style.width = '100%';
    container.appendChild(widgetDiv);

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.src = `https://s3.tradingview.com/external-embedding/embed-widget-${widgetType}.js`;
    script.textContent = JSON.stringify({
      ...config,
      height: height,
      width: '100%',
    });
    container.appendChild(script);

    return () => { container.innerHTML = ''; };
  }, [widgetType, config.symbol, theme, height]);

  return (
    <div className="relative" style={{ height, width: '100%' }}>
      {/* Skeleton placeholder while chart loads */}
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/[0.02] rounded animate-pulse pointer-events-none z-0">
        <BarChart3 size={32} className="text-hive-muted/10 mb-2" />
        <p className="text-[10px] text-hive-muted/30">Loading chart...</p>
      </div>
      <div
        className="tradingview-widget-container relative z-10"
        ref={containerRef}
        style={{ height, width: '100%' }}
      />
    </div>
  );
}

function SignalLevelsPanel({ position, currentPrice }: {
  position: { side: string; entry: number; sl: number; tp: number; conviction: number } | null;
  currentPrice: number;
}) {
  if (!position) return null;
  const { entry, sl, tp } = position;
  const isLong = position.side === 'BUY';
  const risk = Math.abs(entry - sl);
  const reward = Math.abs(tp - entry);
  const rr = risk > 0 ? (reward / risk).toFixed(1) : '—';
  const pnlPct = isLong
    ? ((currentPrice - entry) / entry * 100)
    : ((entry - currentPrice) / entry * 100);

  // R-multiple progress
  const currentR = risk > 0 ? (isLong ? (currentPrice - entry) / risk : (entry - currentPrice) / risk) : 0;
  const progressToTp = reward > 0
    ? Math.min(100, Math.max(0, (isLong ? (currentPrice - entry) : (entry - currentPrice)) / reward * 100))
    : 0;
  const progressToSl = risk > 0
    ? Math.min(100, Math.max(0, (isLong ? (entry - currentPrice) : (currentPrice - entry)) / risk * 100))
    : 0;
  const riskAmount = risk * (position as any).shares || risk * 10;  // estimate
  const riskPctPortfolio = (riskAmount / 100000 * 100);

  // Visual bar: map SL → Entry → TP to a 0-100% bar
  const allPrices = [sl, entry, tp, currentPrice];
  const lo = Math.min(...allPrices);
  const hi = Math.max(...allPrices);
  const span = hi - lo || 1;
  const pct = (p: number) => ((p - lo) / span) * 100;

  return (
    <div className="px-5 py-4 border-t border-white/[0.06]">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${isLong ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20' : 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20'}`}>
            {isLong ? 'LONG' : 'SHORT'}
          </span>
          <span className="text-xs text-hive-muted">Signal Levels</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-hive-muted">R:R <span className="font-bold text-hive-text">{rr}</span></span>
          <span className={`text-[10px] font-bold ${pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Visual price range bar */}
      <div className="relative h-8 rounded-lg overflow-hidden bg-white/[0.03] border border-white/[0.06]">
        {/* Loss zone */}
        <div className="absolute top-0 bottom-0 bg-red-500/10" style={{ left: `${Math.min(pct(sl), pct(entry))}%`, width: `${Math.abs(pct(entry) - pct(sl))}%` }} />
        {/* Profit zone */}
        <div className="absolute top-0 bottom-0 bg-emerald-500/10" style={{ left: `${Math.min(pct(tp), pct(entry))}%`, width: `${Math.abs(pct(tp) - pct(entry))}%` }} />

        {/* SL marker */}
        <div className="absolute top-0 bottom-0 w-0.5 bg-red-500" style={{ left: `${pct(sl)}%` }}>
          <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 -translate-y-full text-[9px] font-bold text-red-400 whitespace-nowrap bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
            SL ${sl.toFixed(2)}
          </div>
        </div>

        {/* Entry marker */}
        <div className="absolute top-0 bottom-0 w-0.5 bg-blue-500" style={{ left: `${pct(entry)}%` }}>
          <div className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 translate-y-full text-[9px] font-bold text-blue-400 whitespace-nowrap bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">
            Entry ${entry.toFixed(2)}
          </div>
        </div>

        {/* TP marker */}
        <div className="absolute top-0 bottom-0 w-0.5 bg-emerald-500" style={{ left: `${pct(tp)}%` }}>
          <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 -translate-y-full text-[9px] font-bold text-emerald-400 whitespace-nowrap bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
            TP ${tp.toFixed(2)}
          </div>
        </div>

        {/* Current price marker */}
        <div className="absolute top-0 bottom-0 flex items-center" style={{ left: `${pct(currentPrice)}%` }}>
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400 border-2 border-amber-500 shadow-lg shadow-amber-500/30 -translate-x-1/2" />
        </div>
      </div>

      {/* R-Multiple Progress */}
      <div className="mt-3 grid grid-cols-3 gap-3">
        <div className="glass-card p-2.5 text-center">
          <p className="text-[9px] text-hive-muted uppercase">Current R</p>
          <p className={`text-sm font-bold ${currentR >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{currentR >= 0 ? '+' : ''}{currentR.toFixed(2)}R</p>
        </div>
        <div className="glass-card p-2.5 text-center">
          <p className="text-[9px] text-hive-muted uppercase">Progress to TP</p>
          <p className="text-sm font-bold text-emerald-400">{progressToTp.toFixed(0)}%</p>
          <div className="h-1 bg-white/[0.04] rounded-full mt-1 overflow-hidden">
            <div className="h-full bg-emerald-500/60 rounded-full" style={{ width: `${progressToTp}%` }} />
          </div>
        </div>
        <div className="glass-card p-2.5 text-center">
          <p className="text-[9px] text-hive-muted uppercase">Risk at Stake</p>
          <p className="text-sm font-bold text-red-400">${Math.round(riskAmount)}</p>
          <p className="text-[8px] text-hive-muted">{riskPctPortfolio.toFixed(1)}% of portfolio</p>
        </div>
      </div>

      {/* Legend row */}
      <div className="flex items-center justify-between mt-3 text-[10px]">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-red-500 rounded" />
          <span className="text-red-400">SL ${sl.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-blue-500 rounded" />
          <span className="text-blue-400">Entry ${entry.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 border border-amber-500" />
          <span className="text-amber-400">Now ${currentPrice.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-emerald-500 rounded" />
          <span className="text-emerald-400">TP ${tp.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}

function TradingViewSection({ symbol, position, currentPrice }: {
  symbol: string;
  position: { side: string; entry: number; sl: number; tp: number; conviction: number } | null;
  currentPrice: number;
}) {
  const theme = useTheme();
  const isDark = theme === 'dark';
  const bgColor = isDark ? 'rgba(10, 10, 15, 1)' : 'rgba(248, 249, 251, 1)';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.05)';

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-blue-400" />
          <h2 className="text-sm font-semibold">{symbol}</h2>
        </div>
        <a
          href={`https://www.tradingview.com/chart/?symbol=${symbol}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
        >
          Open in TradingView <ExternalLink size={9} />
        </a>
      </div>
      <TVWidget
        widgetType="advanced-chart"
        height={800}
        config={{
          autosize: true,
          symbol: symbol,
          interval: 'D',
          timezone: 'America/New_York',
          theme: theme,
          style: '1',
          locale: 'en',
          range: '3M',
          allow_symbol_change: false,
          details: false,
          hotlist: false,
          calendar: false,
          studies: [],
          show_popup_button: true,
          popup_width: '900',
          popup_height: '600',
          backgroundColor: bgColor,
          gridColor: gridColor,
          hide_side_toolbar: false,
          hide_top_toolbar: false,
          hide_legend: false,
          save_image: true,
          enable_publishing: false,
          withdateranges: true,
          hide_volume: false,
        }}
      />
      <SignalLevelsPanel position={position} currentPrice={currentPrice} />
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────────

export default function StockDetailPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="w-5 h-5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" /></div>}>
      <StockDetailContent />
    </Suspense>
  );
}

function StockDetailContent() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toLowerCase();
  const stock = stockData[symbol];

  if (!stock) {
    return (
      <div className="slide-up flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <BarChart3 size={40} className="text-hive-muted/20" />
        <p className="text-lg font-semibold text-hive-muted">Stock not found</p>
        <a href="/stocks" className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1">
          <ArrowLeft size={14} /> Back to dashboard
        </a>
      </div>
    );
  }

  const sym = symbol.toUpperCase();
  const pnlUsd = stock.position
    ? stock.position.side === 'BUY'
      ? (stock.price - stock.position.entry) * stock.position.shares
      : (stock.position.entry - stock.price) * stock.position.shares
    : 0;
  const pnlPct = stock.position
    ? stock.position.side === 'BUY'
      ? ((stock.price - stock.position.entry) / stock.position.entry) * 100
      : ((stock.position.entry - stock.price) / stock.position.entry) * 100
    : 0;

  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams.get('tab');
  const validTabs = ['chart', 'signals', 'news', 'fundamentals'] as const;
  type TabId = typeof validTabs[number];
  const activeTab: TabId = validTabs.includes(tabParam as TabId) ? (tabParam as TabId) : 'chart';

  const setActiveTab = (tab: TabId) => {
    router.push(`/stocks/${symbol}?tab=${tab}`, { scroll: false });
  };

  const tabs = [
    { id: 'chart' as TabId, label: 'Chart', icon: LineChart },
    { id: 'signals' as TabId, label: 'Signals', icon: Signal },
    { id: 'news' as TabId, label: 'News', icon: Newspaper },
    { id: 'fundamentals' as TabId, label: 'Fundamentals', icon: Building2 },
  ];

  return (
    <div className="slide-up space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <a href="/stocks" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 mb-2">
            <ArrowLeft size={12} /> Back to dashboard
          </a>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-black tracking-tight">{sym}</h1>
            <span className="text-lg text-hive-muted font-medium">{stock.name}</span>
          </div>
          <div className="flex items-center gap-3 mt-1.5">
            <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20">{stock.sector}</span>
            <span className="text-sm text-hive-muted">MCap {stock.marketCap}</span>
            <span className="text-sm text-hive-muted">P/E {stock.pe}</span>
            <span className="text-sm text-hive-muted">SI {stock.shortInterest}</span>
            <span className="text-sm text-hive-muted">Inst. {stock.institutionalPct}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold tracking-tight">${stock.price.toLocaleString()}</p>
          <p className={`text-sm font-semibold flex items-center gap-1 justify-end ${stock.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {stock.change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Earnings Blackout Banner */}
      {stock.earnings?.inBlackout && (
        <div className="glass-card p-4 border-red-500/20 bg-red-500/5">
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} className="text-red-400 shrink-0" />
            <div>
              <p className="text-sm font-bold text-red-400">Earnings Blackout Active</p>
              <p className="text-xs text-hive-muted mt-0.5">
                Earnings on {new Date(stock.earnings.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} ({stock.earnings.daysAway} days away).
                No new positions allowed. Beat rate: {stock.earnings.beatRate} | Avg surprise: {stock.earnings.avgSurprise}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Position Summary Bar (always visible) */}
      {stock.position && (
        <div className="glass-card px-5 py-3 flex items-center gap-6">
          <span className={`text-[10px] font-bold px-2.5 py-1 rounded ${
            stock.position.side === 'BUY'
              ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20'
              : 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20'
          }`}>{stock.position.side === 'BUY' ? 'LONG' : 'SHORT'}</span>
          <span className="text-sm">{stock.position.shares} shares</span>
          <span className="text-sm text-hive-muted">Entry <span className="text-blue-400">${stock.position.entry}</span></span>
          <span className="text-sm text-hive-muted">SL <span className="text-red-400">${stock.position.sl}</span></span>
          <span className="text-sm text-hive-muted">TP <span className="text-emerald-400">${stock.position.tp}</span></span>
          <span className="text-[10px] text-hive-muted">Conv. {stock.position.conviction}/10</span>
          <span className={`ml-auto text-sm font-bold ${pnlUsd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {pnlUsd >= 0 ? '+' : ''}${pnlUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            <span className="text-[10px] ml-1 opacity-60">({pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%)</span>
          </span>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.06]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === tab.id
                ? 'bg-blue-500/15 text-blue-400 ring-1 ring-inset ring-blue-500/20'
                : 'text-hive-muted hover:text-hive-text hover:bg-white/[0.03]'
            }`}
          >
            <tab.icon size={13} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Chart ── */}
      {activeTab === 'chart' && (
        <TradingViewSection
          symbol={sym}
          position={stock.position}
          currentPrice={stock.price}
        />
      )}

      {/* ── Tab: Signals ── */}
      {activeTab === 'signals' && (
        <div className="space-y-3">
        <p className="text-[9px] text-hive-muted/50 flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-blue-500/10 flex items-center justify-center"><span className="text-[7px]">AI</span></span> AI-generated signals — for research purposes only, not investment advice. All team names are fictional AI personas.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {stock.agentSignals.map((sig) => {
            const isBullish = sig.direction === 'BULLISH';
            const isBlackout = sig.conviction === 0;
            return (
              <div key={sig.team} className="glass-card p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold">{sig.team}</span>
                  <div className="flex items-center gap-2">
                    {isBlackout ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-500/20 text-red-400">BLACKOUT</span>
                    ) : (
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        isBullish ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                      }`}>{sig.direction}</span>
                    )}
                    <span className="text-sm font-bold">{sig.conviction}/10</span>
                  </div>
                </div>
                <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden mb-3">
                  <div
                    className={`h-full rounded-full ${isBlackout ? 'bg-red-500' : isBullish ? 'bg-emerald-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(sig.conviction * 10, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-hive-muted leading-relaxed">{sig.reasoning}</p>
              </div>
            );
          })}
        </div>
        </div>
      )}

      {/* ── Tab: News ── */}
      {activeTab === 'news' && (
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Newspaper size={14} className="text-blue-400" />
              <h2 className="text-sm font-semibold">{sym} News & Analysis</h2>
            </div>
            <span className="text-xs text-hive-muted">{stock.news.length} articles</span>
          </div>
          <div className="divide-y divide-white/[0.03]">
            {stock.news.map((item, i) => (
              <div key={i} className="px-5 py-4 hover:bg-white/[0.02] transition-colors">
                <div className="flex items-start gap-3">
                  <div className={`mt-1 h-2 w-2 rounded-full shrink-0 ${sentimentDot[item.sentiment]}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-4">
                      <h3 className="text-sm font-semibold leading-snug">{item.headline}</h3>
                      <span className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded ${sentimentBg[item.sentiment]} ${sentimentColor[item.sentiment]}`}>
                        {sentimentLabel[item.sentiment]}
                      </span>
                    </div>
                    <p className="text-xs text-hive-muted mt-2 leading-relaxed">{item.summary}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-[10px] font-medium text-hive-muted">{item.source}</span>
                      <span className="text-[10px] text-hive-muted/50 flex items-center gap-1"><Clock size={9} /> {item.time}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tab: Fundamentals ── */}
      {activeTab === 'fundamentals' && (
        <div className="space-y-4">
          {/* Row 1: Risk Metrics + Sector Context */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

            {/* Risk Metrics Card */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Gauge size={14} className="text-amber-400" />
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Risk Metrics</p>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Beta to SPY</span>
                  <span className="font-bold font-mono">1.15</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">20-day Realized Vol</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">28%</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/20">62nd pctl</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">ATR (14)</span>
                  <span className="font-bold font-mono">$5.40</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Implied Vol Rank</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">68%</span>
                    <div className="w-16 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                      <div className="h-full bg-amber-500/60 rounded-full" style={{ width: '68%' }} />
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Expected Earnings Move</span>
                  <span className="font-bold font-mono text-violet-400">&plusmn;4.1%</span>
                </div>
              </div>
            </div>

            {/* Sector Context Card */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Globe size={14} className="text-blue-400" />
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Sector Context</p>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Sector</span>
                  <span className="font-bold">Technology <span className="text-syn-muted font-normal">(XLK)</span></span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Sector vs S&P</span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-emerald-400">1d +0.8%</span>
                    <span className="text-syn-muted/30">|</span>
                    <span className="text-emerald-400">5d +2.1%</span>
                    <span className="text-syn-muted/30">|</span>
                    <span className="text-emerald-400">1m +5.4%</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Relative Strength vs SPY</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">1.12</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20 flex items-center gap-0.5">
                      <ArrowUpRight size={9} /> +12%
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Correlation to 10Y Yield</span>
                  <span className="font-bold font-mono text-red-400">-0.45</span>
                </div>
              </div>
            </div>
          </div>

          {/* Row 2: Institutional Ownership + Valuation */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

            {/* Institutional Ownership Card */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Users size={14} className="text-violet-400" />
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Institutional Ownership</p>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">13F Holders</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">347</span>
                    <span className="text-[10px] text-syn-muted">(79% of major HFs)</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Quarterly Trend</span>
                  <div className="flex items-center gap-2">
                    <span className="text-emerald-400 font-bold font-mono">+12 funds</span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20">ACCUMULATING</span>
                  </div>
                </div>
                <div className="border-t border-white/[0.06] pt-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-syn-muted">Insider Activity (90d)</span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20">BULLISH</span>
                  </div>
                  <p className="text-xs text-syn-muted leading-relaxed">
                    <span className="text-emerald-400 font-semibold">6 buys</span> ($2.1M) at $175-180 range, <span className="text-syn-muted">0 sells</span> past 3 months
                  </p>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Short Interest</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">8.2%</span>
                    <span className="text-[10px] text-syn-muted">DTC: 2.4</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Valuation Card */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <DollarSign size={14} className="text-emerald-400" />
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Valuation & Consensus</p>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">P/E</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">32.4x</span>
                    <span className="text-[10px] text-syn-muted">sector med: 28.1x</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">PEG Ratio</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">1.6</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20">Fair Value</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">EV/Sales</span>
                  <span className="font-bold font-mono">8.2x</span>
                </div>
                <div className="border-t border-white/[0.06] pt-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-syn-muted">Analyst Consensus</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400">22 Buy</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400">3 Hold</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-400">0 Sell</span>
                  </div>
                  {/* Consensus bar */}
                  <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden flex">
                    <div className="h-full bg-emerald-500/60" style={{ width: '88%' }} />
                    <div className="h-full bg-amber-500/60" style={{ width: '12%' }} />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Price Target (median)</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono">$245</span>
                    <span className="text-[10px] text-emerald-400 flex items-center gap-0.5"><ArrowUpRight size={9} /> +8.2%</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-syn-muted">Recent Changes (30d)</span>
                  <div className="flex items-center gap-2 text-[10px]">
                    <span className="text-emerald-400 font-semibold">2 upgrades</span>
                    <span className="text-syn-muted/30">|</span>
                    <span className="text-syn-muted">0 downgrades</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Row 3: Earnings & Catalysts (full width) */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Calendar size={14} className="text-red-400" />
              <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">Earnings & Catalysts</p>
              <span className="ml-auto text-[10px] font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20 flex items-center gap-1">
                <ShieldAlert size={10} /> BLACKOUT ACTIVE
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              {/* Next Earnings */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mb-3">Next Earnings</p>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
                    <Calendar size={18} className="text-red-400" />
                  </div>
                  <div>
                    <p className="text-lg font-bold">Apr 1</p>
                    <p className="text-[10px] text-red-400 font-semibold">4 days away</p>
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-red-500/5 border border-red-500/10">
                  <div className="flex items-start gap-1.5">
                    <AlertTriangle size={11} className="text-red-400 mt-0.5 shrink-0" />
                    <p className="text-[10px] text-red-400/80 leading-relaxed">
                      Position TP targets may be unreliable within 3 days of earnings
                    </p>
                  </div>
                </div>
              </div>

              {/* Last 4 Earnings */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mb-3">Last 4 Earnings</p>
                <div className="space-y-2">
                  {[
                    { q: 'Q4', pct: '+8.2%', type: 'beat' },
                    { q: 'Q3', pct: '+3.1%', type: 'beat' },
                    { q: 'Q2', pct: '-2.3%', type: 'miss' },
                    { q: 'Q1', pct: '+5.1%', type: 'beat' },
                  ].map((e) => (
                    <div key={e.q} className="flex items-center justify-between text-sm">
                      <span className="text-syn-muted font-mono text-xs">{e.q}</span>
                      <div className="flex items-center gap-2">
                        <span className={`font-bold font-mono ${e.type === 'beat' ? 'text-emerald-400' : 'text-red-400'}`}>{e.pct}</span>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${e.type === 'beat' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                          {e.type.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Upcoming Catalysts */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mb-3">Upcoming Catalysts</p>
                <div className="space-y-2.5">
                  {[
                    { event: 'Product Launch', date: 'Apr 15', icon: Zap },
                    { event: 'WWDC', date: 'Jun', icon: Target },
                    { event: 'Services Growth', date: 'Ongoing', icon: TrendingUp },
                  ].map((c) => (
                    <div key={c.event} className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded bg-white/[0.04] flex items-center justify-center shrink-0">
                        <c.icon size={12} className="text-blue-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold truncate">{c.event}</p>
                        <p className="text-[10px] text-syn-muted">{c.date}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Row 4: Original basic Valuation + Earnings (preserved) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="glass-card p-5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mb-4">Overview</p>
              <div className="space-y-3 text-sm">
                {[
                  { label: 'Market Cap', value: stock.marketCap },
                  { label: 'P/E Ratio', value: stock.pe.toString() },
                  { label: 'Short Interest', value: stock.shortInterest },
                  { label: 'Institutional %', value: stock.institutionalPct },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between">
                    <span className="text-syn-muted">{row.label}</span>
                    <span className="font-bold">{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
            {stock.earnings && (
              <div className="glass-card p-5">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mb-4">Earnings Schedule</p>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between"><span className="text-syn-muted">Next Earnings</span><span>{stock.earnings.date}</span></div>
                  <div className="flex justify-between"><span className="text-syn-muted">Days Away</span><span className={stock.earnings.inBlackout ? 'text-red-400 font-bold' : ''}>{stock.earnings.daysAway}d {stock.earnings.inBlackout ? '(BLACKOUT)' : ''}</span></div>
                  <div className="flex justify-between"><span className="text-syn-muted">Beat Rate</span><span className="text-emerald-400">{stock.earnings.beatRate}</span></div>
                  <div className="flex justify-between"><span className="text-syn-muted">Avg Surprise</span><span className="text-emerald-400">{stock.earnings.avgSurprise}</span></div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
