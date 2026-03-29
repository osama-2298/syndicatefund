
'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Wallet, TrendingUp, TrendingDown, BarChart3, Bot,
  Zap, Shield, Activity, Clock, ArrowRight, Signal,
  AlertTriangle, Calendar, Eye, Globe, DollarSign, Newspaper,
  ArrowUpRight, ArrowDownRight, Timer, Gauge, Layers,
} from 'lucide-react';
import { DemoBanner } from '@/components/DemoBanner';

// ── Demo Data ──────────────────────────────────────────────────────────

const demoNews: Record<string, { headline: string; source: string; time: string; sentiment: 'positive' | 'negative' | 'neutral' }[]> = {
  AAPL: [
    { headline: 'Apple Vision Pro 2 enters mass production ahead of WWDC', source: 'Bloomberg', time: '2h ago', sentiment: 'positive' },
    { headline: 'Apple Services revenue hits all-time high in Q1', source: 'Reuters', time: '5h ago', sentiment: 'positive' },
    { headline: 'EU regulators probe Apple Pay dominance in mobile payments', source: 'FT', time: '1d ago', sentiment: 'negative' },
  ],
  NVDA: [
    { headline: 'NVIDIA Blackwell Ultra chips see unprecedented demand from hyperscalers', source: 'Reuters', time: '1h ago', sentiment: 'positive' },
    { headline: 'Jensen Huang: "AI infrastructure spending will exceed $1T by 2028"', source: 'CNBC', time: '4h ago', sentiment: 'positive' },
    { headline: 'China export restrictions could impact 8% of NVIDIA revenue', source: 'WSJ', time: '8h ago', sentiment: 'negative' },
  ],
  MSFT: [
    { headline: 'Microsoft Azure AI revenue growth accelerates to 65% YoY', source: 'Bloomberg', time: '3h ago', sentiment: 'positive' },
    { headline: 'Copilot enterprise adoption surpasses 500K seats', source: 'TechCrunch', time: '6h ago', sentiment: 'positive' },
    { headline: 'Microsoft faces antitrust scrutiny over Teams bundling in Europe', source: 'Reuters', time: '1d ago', sentiment: 'negative' },
  ],
  TSLA: [
    { headline: 'Tesla Robotaxi pilot launches in Austin with 200 vehicles', source: 'Bloomberg', time: '2h ago', sentiment: 'positive' },
    { headline: 'Model Y sales decline 12% in Europe amid rising competition', source: 'Reuters', time: '7h ago', sentiment: 'negative' },
    { headline: 'Elon Musk faces shareholder lawsuit over time allocation to xAI', source: 'WSJ', time: '1d ago', sentiment: 'negative' },
  ],
};

const demoPositions = [
  { symbol: 'AAPL', side: 'BUY', shares: 45, entry: 178.50, current: 182.30, sl: 171.20, tp: 195.00, conviction: 7 },
  { symbol: 'NVDA', side: 'BUY', shares: 12, entry: 890.00, current: 912.50, sl: 845.00, tp: 985.00, conviction: 8 },
  { symbol: 'MSFT', side: 'BUY', shares: 25, entry: 415.00, current: 421.80, sl: 398.00, tp: 450.00, conviction: 6 },
  { symbol: 'TSLA', side: 'SELL', shares: 20, entry: 245.00, current: 238.60, sl: 265.00, tp: 210.00, conviction: 5 },
];

const demoSectors = [
  { name: 'Technology', etf: 'XLK', change1d: 1.2, change5d: 3.1, change1m: 5.4 },
  { name: 'Health Care', etf: 'XLV', change1d: -0.3, change5d: 0.8, change1m: 2.1 },
  { name: 'Financials', etf: 'XLF', change1d: 0.5, change5d: -1.2, change1m: 0.3 },
  { name: 'Consumer Disc.', etf: 'XLY', change1d: 0.8, change5d: 2.4, change1m: 4.2 },
  { name: 'Comm. Services', etf: 'XLC', change1d: 1.5, change5d: 3.8, change1m: 6.1 },
  { name: 'Industrials', etf: 'XLI', change1d: -0.1, change5d: 0.5, change1m: 1.8 },
  { name: 'Staples', etf: 'XLP', change1d: -0.4, change5d: -0.9, change1m: -0.2 },
  { name: 'Energy', etf: 'XLE', change1d: -1.1, change5d: -2.8, change1m: -4.5 },
  { name: 'Utilities', etf: 'XLU', change1d: 0.2, change5d: 0.1, change1m: 1.0 },
  { name: 'Real Estate', etf: 'XLRE', change1d: 0.3, change5d: -0.5, change1m: 0.7 },
  { name: 'Materials', etf: 'XLB', change1d: -0.6, change5d: -1.5, change1m: -2.1 },
];

const demoMarket = {
  regime: 'bull',
  vix: 16.8,
  spy: { price: 5842.50, change: 0.45 },
  qqq: { price: 508.20, change: 0.72 },
  cnnFearGreed: { value: 62, label: 'Greed' },
  treasury10y: 4.25,
  yieldCurve: 0.35,
};

const demoEarnings = [
  { symbol: 'AAPL', date: '2026-03-19', daysAway: 3, inBlackout: true },
  { symbol: 'GOOGL', date: '2026-03-20', daysAway: 4, inBlackout: false },
  { symbol: 'AMZN', date: '2026-03-25', daysAway: 9, inBlackout: false },
];

const demoTeams = [
  { name: 'Technical', agents: 3, weight: 1.2, color: 'blue' },
  { name: 'Sentiment', agents: 3, weight: 1.0, color: 'purple' },
  { name: 'Fundamental', agents: 3, weight: 1.3, color: 'green' },
  { name: 'Macro', agents: 3, weight: 1.0, color: 'orange' },
  { name: 'Institutional', agents: 2, weight: 1.1, color: 'cyan' },
  { name: 'News', agents: 2, weight: 0.9, color: 'pink' },
];

const demoCycles = [
  { id: 42, started_at: '2026-03-16T14:00:00Z', regime: 'bull', stocks_analyzed: 25, signals: 18, trades: 3, duration: 185 },
  { id: 41, started_at: '2026-03-16T10:00:00Z', regime: 'bull', stocks_analyzed: 22, signals: 15, trades: 2, duration: 172 },
  { id: 40, started_at: '2026-03-15T18:00:00Z', regime: 'bull', stocks_analyzed: 28, signals: 20, trades: 4, duration: 198 },
  { id: 39, started_at: '2026-03-15T14:00:00Z', regime: 'ranging', stocks_analyzed: 20, signals: 12, trades: 1, duration: 165 },
  { id: 38, started_at: '2026-03-15T10:00:00Z', regime: 'ranging', stocks_analyzed: 18, signals: 10, trades: 2, duration: 155 },
];

const pipelineSteps = [
  'Market Intelligence', 'CEO Directive', 'Stock Selection (S&P 500)',
  'Technical Analysis', 'Sentiment Analysis', 'Fundamental Analysis',
  'Macro Analysis', 'Institutional Analysis', 'News Analysis',
  'Team Aggregation', 'Signal Aggregation', 'Earnings Blackout Filter',
  'Risk Check', 'Execution (Market Hours)',
];

// ── Helpers ────────────────────────────────────────────────────────────

function isMarketOpen(): { open: boolean; label: string } {
  const now = new Date();
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const day = et.getDay();
  const hours = et.getHours();
  const mins = et.getMinutes();
  const time = hours * 60 + mins;
  if (day === 0 || day === 6) return { open: false, label: 'Weekend' };
  if (time >= 570 && time < 960) return { open: true, label: 'Market Open' };
  if (time < 570) return { open: false, label: 'Pre-Market' };
  return { open: false, label: 'After Hours' };
}

const teamColorMap: Record<string, { bg: string; text: string; ring: string; dot: string }> = {
  blue:   { bg: 'bg-blue-500/10', text: 'text-blue-400', ring: 'ring-blue-500/20', dot: 'bg-blue-400' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-400', ring: 'ring-purple-500/20', dot: 'bg-purple-400' },
  green:  { bg: 'bg-emerald-500/10', text: 'text-emerald-400', ring: 'ring-emerald-500/20', dot: 'bg-emerald-400' },
  orange: { bg: 'bg-orange-500/10', text: 'text-orange-400', ring: 'ring-orange-500/20', dot: 'bg-orange-400' },
  cyan:   { bg: 'bg-cyan-500/10', text: 'text-cyan-400', ring: 'ring-cyan-500/20', dot: 'bg-cyan-400' },
  pink:   { bg: 'bg-pink-500/10', text: 'text-pink-400', ring: 'ring-pink-500/20', dot: 'bg-pink-400' },
};

const sentimentColor = { positive: 'text-emerald-400', negative: 'text-red-400', neutral: 'text-hive-muted' };
const sentimentDot = { positive: 'bg-emerald-400', negative: 'bg-red-400', neutral: 'bg-hive-muted' };

// ── News Tooltip Component ─────────────────────────────────────────────

function NewsTooltip({ symbol, children }: { symbol: string; children: React.ReactNode }) {
  const [show, setShow] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const news = demoNews[symbol];
  if (!news || news.length === 0) return <>{children}</>;

  const handleMouseEnter = (e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setPos({ x: rect.left, y: rect.bottom + 8 });
    timeoutRef.current = setTimeout(() => setShow(true), 300);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShow(false);
  };

  return (
    <div className="relative" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      {children}
      {show && (
        <div
          ref={tooltipRef}
          className="fixed z-[100] w-80 glass-card p-0 shadow-2xl shadow-black/40 overflow-hidden animate-in fade-in"
          style={{ left: Math.min(pos.x, window.innerWidth - 340), top: pos.y }}
        >
          <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
            <Newspaper size={12} className="text-blue-400" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-hive-muted">Latest News — {symbol}</span>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {news.slice(0, 3).map((item, i) => (
              <div key={i} className="px-3 py-2.5 hover:bg-white/[0.02] transition-colors">
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${sentimentDot[item.sentiment]}`} />
                  <div className="min-w-0">
                    <p className="text-xs leading-snug">{item.headline}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-hive-muted">{item.source}</span>
                      <span className="text-[10px] text-hive-muted/50">{item.time}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <a
            href={`/stocks/${symbol.toLowerCase()}`}
            className="block px-3 py-2 text-[10px] font-semibold text-blue-400 hover:bg-blue-500/5 transition-colors text-center border-t border-white/[0.06]"
          >
            View all {symbol} news & analysis →
          </a>
        </div>
      )}
    </div>
  );
}

// ── Mini Stock Chart (TradingView Symbol Overview Widget) ───────────────

function MiniStockChart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = '';

    const isDark = !document.documentElement.classList.contains('light');

    const widgetDiv = document.createElement('div');
    widgetDiv.className = 'tradingview-widget-container__widget';
    widgetDiv.style.height = '100%';
    widgetDiv.style.width = '100%';
    container.appendChild(widgetDiv);

    const copyright = document.createElement('div');
    copyright.className = 'tradingview-widget-copyright';
    container.appendChild(copyright);

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js';
    script.textContent = JSON.stringify({
      symbol: symbol,
      width: '100%',
      height: '100%',
      locale: 'en',
      dateRange: '6M',
      colorTheme: isDark ? 'dark' : 'light',
      isTransparent: true,
      autosize: true,
      largeChartUrl: '',
      chartOnly: false,
      noTimeScale: false,
    });
    container.appendChild(script);

    return () => { container.innerHTML = ''; };
  }, [symbol]);

  return (
    <a href={`/stocks/${symbol.toLowerCase()}`} className="block glass-card-hover overflow-hidden rounded-xl">
      <div
        className="tradingview-widget-container"
        ref={containerRef}
        style={{ height: 200, width: '100%' }}
      />
    </a>
  );
}

// ── Page ───────────────────────────────────────────────────────────────

export default function StocksDashboard() {
  const [marketStatus, setMarketStatus] = useState(isMarketOpen());

  useEffect(() => {
    const interval = setInterval(() => setMarketStatus(isMarketOpen()), 30000);
    return () => clearInterval(interval);
  }, []);

  const invested = demoPositions.reduce((s, p) => s + p.shares * p.current, 0);
  const entryTotal = demoPositions.reduce((s, p) => s + p.shares * p.entry, 0);
  const cash = 100000 - entryTotal;
  const totalValue = cash + invested;
  const returnPct = ((totalValue - 100000) / 100000) * 100;
  const returnUsd = totalValue - 100000;
  const totalSignals = 156;

  // P&L breakdown
  const realizedPnl = 3_142;
  const unrealizedPnl = demoPositions.reduce((s, p) => {
    return s + (p.side === 'BUY'
      ? (p.current - p.entry) * p.shares
      : (p.entry - p.current) * p.shares);
  }, 0);
  const totalPnl = realizedPnl + unrealizedPnl;

  return (
    <div className="slide-up space-y-6">
      <DemoBanner />
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Stock Dashboard</h1>
          <p className="text-sm text-hive-muted mt-1">Autonomous AI stock analysis — 16 agents across 6 teams</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`glass-card flex items-center gap-2 px-3 py-1.5 ${marketStatus.open ? '' : 'opacity-70'}`}>
            <span className="relative flex h-2 w-2">
              {marketStatus.open ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-hive-muted"></span>
              )}
            </span>
            <span className={`text-xs font-medium ${marketStatus.open ? 'text-emerald-400' : 'text-hive-muted'}`}>
              {marketStatus.label.toUpperCase()}
            </span>
          </div>
          <div className="glass-card flex items-center gap-1.5 px-3 py-1.5">
            <Clock size={12} className="text-hive-muted" />
            <span className="text-xs text-hive-muted">
              {new Date(demoCycles[0].started_at).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Portfolio Value */}
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">Portfolio</p>
          <p className={`text-xl font-bold tracking-tight ${returnPct >= 0 ? 'text-hive-text' : 'text-hive-red'}`}>
            ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
          <div className={`mt-1 flex items-center gap-1 text-[10px] font-medium ${returnPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {returnPct >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
            {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%
          </div>
        </div>

        {/* P&L Breakdown */}
        <a href="/stocks/pnl" className="glass-card-hover p-4 block">
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">P&L</p>
            <ArrowRight size={10} className="text-hive-muted/30" />
          </div>
          <div className="flex items-baseline gap-2">
            <div>
              <p className="text-sm font-bold text-emerald-400">+${realizedPnl.toLocaleString()}</p>
              <p className="text-[9px] text-hive-muted">Realized</p>
            </div>
            <div className="h-5 w-px bg-white/[0.06]" />
            <div>
              <p className={`text-sm font-bold ${unrealizedPnl >= 0 ? 'text-blue-400' : 'text-red-400'}`}>
                {unrealizedPnl >= 0 ? '+' : ''}${Math.round(unrealizedPnl).toLocaleString()}
              </p>
              <p className="text-[9px] text-hive-muted">Unrealized</p>
            </div>
          </div>
        </a>

        {/* Drawdown */}
        <a href="/stocks/risk" className="glass-card-hover p-4 block">
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Drawdown</p>
            <ArrowRight size={10} className="text-hive-muted/30" />
          </div>
          <p className="text-xl font-bold text-red-400">-2.4%</p>
          <div className="mt-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
            <div className="h-full bg-red-500/50 rounded-full" style={{ width: '60%' }} />
          </div>
          <p className="text-[9px] text-hive-muted mt-1">Limit: 4.0%</p>
        </a>

        {/* Alpha vs Benchmark */}
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">Alpha vs SPY</p>
          <p className="text-xl font-bold text-emerald-400">+1.83%</p>
          <div className="mt-1 flex items-center gap-2 text-[9px] text-hive-muted">
            <span>Strategy: <span className="text-emerald-400">+4.28%</span></span>
            <span>SPY: <span className="text-hive-text">+2.45%</span></span>
          </div>
        </div>

        {/* VaR */}
        <a href="/stocks/risk" className="glass-card-hover p-4 block">
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">VaR (95%)</p>
            <ArrowRight size={10} className="text-hive-muted/30" />
          </div>
          <p className="text-xl font-bold text-amber-400">$2,180</p>
          <p className="text-[9px] text-hive-muted mt-1">Max daily loss est.</p>
        </a>

        {/* Market Status */}
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">Market</p>
          <p className={`text-sm font-bold ${marketStatus.open ? 'text-emerald-400' : 'text-hive-muted'}`}>
            {marketStatus.open ? 'OPEN' : 'CLOSED'}
          </p>
          <p className="text-[9px] text-hive-muted">{marketStatus.label} (ET)</p>
          <div className="mt-1.5 flex items-center gap-3 text-[9px] text-hive-muted">
            <span><Bot size={9} className="inline" /> 16</span>
            <span><Zap size={9} className="inline" /> {totalSignals}</span>
          </div>
        </div>
      </div>

      {/* ══ Macro Regime Card ══ */}
      <div className="glass-card p-4 relative overflow-hidden">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Globe size={14} className="text-blue-400" />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Macro Regime</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-bold text-emerald-400 tracking-wider">GOLDILOCKS</span>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* Fed Funds Rate */}
          <div className="text-center">
            <p className="text-[10px] text-hive-muted mb-1">Fed Funds Rate</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-lg font-bold font-mono">5.33%</span>
              <ArrowDownRight size={12} className="text-emerald-400" />
            </div>
            <p className="text-[10px] text-hive-muted/70 mt-0.5">Market expects 2 cuts</p>
          </div>
          {/* Yield Curve 2Y/10Y */}
          <div className="text-center">
            <p className="text-[10px] text-hive-muted mb-1">Yield Curve 2Y/10Y</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-lg font-bold font-mono text-amber-400">+0.35%</span>
            </div>
            <div className="flex items-center justify-center gap-1 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              <span className="text-[10px] text-amber-400">Normalizing</span>
            </div>
          </div>
          {/* VIX */}
          <div className="text-center">
            <p className="text-[10px] text-hive-muted mb-1">VIX</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-lg font-bold font-mono text-emerald-400">16.8</span>
            </div>
            <p className="text-[10px] text-hive-muted/70 mt-0.5">25th percentile — low vol</p>
          </div>
          {/* DXY */}
          <div className="text-center">
            <p className="text-[10px] text-hive-muted mb-1">DXY Index</p>
            <div className="flex items-center justify-center gap-1">
              <span className="text-lg font-bold font-mono text-amber-400">103.2</span>
              <ArrowDownRight size={12} className="text-emerald-400" />
            </div>
            <p className="text-[10px] text-hive-muted/70 mt-0.5">Below 200-day MA</p>
          </div>
        </div>
      </div>

      {/* ══ Earnings Calendar + Market Breadth Row ══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Earnings Calendar Widget */}
        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Calendar size={14} className="text-orange-400" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Earnings Calendar — Next 7 Days</span>
            </div>
          </div>
          <div className="space-y-1.5">
            {[
              { symbol: 'AAPL', name: 'Apple Inc.', date: 'Mar 31', move: '3.2%', cap: 'mega', color: 'text-red-400', bg: 'bg-red-500/10', ring: 'border-red-500/20' },
              { symbol: 'MSFT', name: 'Microsoft Corp.', date: 'Apr 1', move: '2.8%', cap: 'mega', color: 'text-red-400', bg: 'bg-red-500/10', ring: 'border-red-500/20' },
              { symbol: 'NVDA', name: 'NVIDIA Corp.', date: 'Apr 3', move: '5.1%', cap: 'mega', color: 'text-red-400', bg: 'bg-red-500/10', ring: 'border-red-500/20' },
              { symbol: 'GOOGL', name: 'Alphabet Inc.', date: 'Apr 3', move: '3.5%', cap: 'mega', color: 'text-red-400', bg: 'bg-red-500/10', ring: 'border-red-500/20' },
              { symbol: 'JPM', name: 'JPMorgan Chase', date: 'Apr 4', move: '2.4%', cap: 'large', color: 'text-orange-400', bg: 'bg-orange-500/10', ring: 'border-orange-500/20' },
              { symbol: 'UNH', name: 'UnitedHealth Group', date: 'Apr 4', move: '2.9%', cap: 'large', color: 'text-orange-400', bg: 'bg-orange-500/10', ring: 'border-orange-500/20' },
            ].map((e) => (
              <div key={e.symbol} className={`flex items-center gap-3 p-2.5 rounded-lg ${e.bg} border ${e.ring}`}>
                <div className="shrink-0 w-10 text-center">
                  <span className={`text-xs font-bold font-mono ${e.color}`}>{e.symbol}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs truncate">{e.name}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[10px] text-hive-muted">{e.date}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[10px] font-mono text-hive-muted">±{e.move}</p>
                  <p className="text-[9px] text-hive-muted/50">{e.cap}-cap</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Market Breadth Card */}
        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <BarChart3 size={14} className="text-cyan-400" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Market Breadth — S&P 500</span>
            </div>
          </div>
          <div className="space-y-4">
            {/* Above 50-day MA */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs">Above 50-Day MA</span>
                <span className="text-sm font-bold font-mono text-emerald-400">72%</span>
              </div>
              <div className="h-2 bg-white/[0.04] rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-emerald-500/60 to-emerald-400/80" style={{ width: '72%' }} />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-[9px] text-red-400/60">Weak &lt;40%</span>
                <span className="text-[9px] text-amber-400/60">40-60%</span>
                <span className="text-[9px] text-emerald-400/60">Healthy &gt;60%</span>
              </div>
            </div>
            {/* Above 200-day MA */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs">Above 200-Day MA</span>
                <span className="text-sm font-bold font-mono text-amber-400">58%</span>
              </div>
              <div className="h-2 bg-white/[0.04] rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-amber-500/60 to-amber-400/80" style={{ width: '58%' }} />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-[9px] text-red-400/60">Bear &lt;40%</span>
                <span className="text-[9px] text-amber-400/60">Neutral</span>
                <span className="text-[9px] text-emerald-400/60">Bull &gt;60%</span>
              </div>
            </div>
            {/* Advance/Decline Ratio */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs">Advance / Decline Ratio</span>
                <span className="text-sm font-bold font-mono text-emerald-400">1.4</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-white/[0.04] rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-emerald-500/60" style={{ width: '58%' }} />
                </div>
                <span className="text-[10px] text-emerald-400 shrink-0">Advancing</span>
              </div>
            </div>
            {/* Summary */}
            <div className="pt-2 border-t border-white/[0.06] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-[10px] text-emerald-400 font-semibold">Breadth confirms uptrend — majority of stocks participating</span>
            </div>
          </div>
        </div>
      </div>

      {/* Analysis Teams Grid */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Analysis Teams</p>
          <a href="/stocks/teams" className="text-xs text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
            View All <ArrowRight size={12} />
          </a>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {demoTeams.map((team) => {
            const colors = teamColorMap[team.color];
            return (
              <div key={team.name} className="glass-card-hover p-3 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`h-2 w-2 rounded-full ${colors.dot}`} />
                  <span className={`text-xs font-semibold ${colors.text}`}>{team.name}</span>
                </div>
                <div className="flex items-end justify-between">
                  <span className="text-lg font-bold">{team.agents}</span>
                  <span className="text-[10px] text-hive-muted">{team.weight.toFixed(1)}x</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Mini Stock Charts */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Stock Charts</p>
          <span className="text-[10px] text-hive-muted">TradingView</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {demoPositions.map((pos) => (
            <MiniStockChart key={pos.symbol} symbol={pos.symbol} />
          ))}
        </div>
      </div>

      {/* Positions + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Open Positions — with hover news tooltip + clickable symbols */}
        <div className="lg:col-span-2 glass-card overflow-visible">
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Signal size={14} className="text-blue-400" />
              <h2 className="text-sm font-semibold">Open Stock Positions</h2>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] text-hive-muted flex items-center gap-1">
                <Newspaper size={10} /> Hover for news
              </span>
              <span className="text-xs text-hive-muted">${invested.toLocaleString(undefined, { maximumFractionDigits: 0 })} invested</span>
            </div>
          </div>
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
                <th className="text-left px-4 py-2.5">Symbol</th>
                <th className="text-left px-4 py-2.5">Side</th>
                <th className="text-right px-4 py-2.5">Shares</th>
                <th className="text-right px-4 py-2.5">Entry</th>
                <th className="text-right px-4 py-2.5">Current</th>
                <th className="text-right px-4 py-2.5">SL</th>
                <th className="text-right px-4 py-2.5">TP</th>
                <th className="text-right px-4 py-2.5">P&L</th>
              </tr>
            </thead>
            <tbody>
              {demoPositions.map((pos, i) => {
                const pnlUsd = pos.side === 'BUY'
                  ? (pos.current - pos.entry) * pos.shares
                  : (pos.entry - pos.current) * pos.shares;
                const pnlPct = pos.side === 'BUY'
                  ? ((pos.current - pos.entry) / pos.entry) * 100
                  : ((pos.entry - pos.current) / pos.entry) * 100;
                const hasNews = !!demoNews[pos.symbol];
                return (
                  <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3">
                      <NewsTooltip symbol={pos.symbol}>
                        <a
                          href={`/stocks/${pos.symbol.toLowerCase()}`}
                          className="group inline-flex items-center gap-1.5"
                        >
                          <span className="font-semibold text-sm group-hover:text-blue-400 transition-colors">{pos.symbol}</span>
                          {hasNews && <Newspaper size={10} className="text-hive-muted/40 group-hover:text-blue-400/60 transition-colors" />}
                          <span className="ml-0.5 text-[10px] text-hive-muted">{pos.conviction}/10</span>
                        </a>
                      </NewsTooltip>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        pos.side === 'BUY'
                          ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20'
                          : 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20'
                      }`}>{pos.side === 'BUY' ? 'LONG' : 'SHORT'}</span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm">{pos.shares}</td>
                    <td className="px-4 py-3 text-right text-sm text-hive-muted">${pos.entry.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-sm font-mono tabular-nums">${pos.current.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-sm text-red-400/70">${pos.sl.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-sm text-emerald-400/70">${pos.tp.toLocaleString()}</td>
                    <td className={`px-4 py-3 text-right text-sm font-semibold ${pnlUsd >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {pnlUsd >= 0 ? '+' : ''}${pnlUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      <span className="text-[10px] ml-1 opacity-60">({pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%)</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-4">
          <div className="glass-card p-5">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-3">Market Regime</p>
            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold ${
              demoMarket.regime === 'bull' ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20' :
              demoMarket.regime === 'bear' ? 'bg-red-500/10 text-red-400 ring-1 ring-red-500/20' :
              demoMarket.regime === 'crisis' ? 'bg-red-900/20 text-red-300 ring-1 ring-red-500/30' :
              'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20'
            }`}>
              {demoMarket.regime === 'bull' ? <TrendingUp size={14} /> : demoMarket.regime === 'bear' ? <TrendingDown size={14} /> : <Shield size={14} />}
              {demoMarket.regime.toUpperCase()}
            </div>
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-hive-muted">VIX</span>
                <span className={`text-sm font-bold ${
                  demoMarket.vix < 15 ? 'text-emerald-400' : demoMarket.vix < 20 ? 'text-hive-text' : demoMarket.vix < 30 ? 'text-amber-400' : 'text-red-400'
                }`}>{demoMarket.vix}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-hive-muted">Fear & Greed</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold">{demoMarket.cnnFearGreed.value}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    demoMarket.cnnFearGreed.value >= 60 ? 'bg-emerald-500/10 text-emerald-400' :
                    demoMarket.cnnFearGreed.value >= 40 ? 'bg-amber-500/10 text-amber-400' : 'bg-red-500/10 text-red-400'
                  }`}>{demoMarket.cnnFearGreed.label}</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-hive-muted">SPY</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold">${demoMarket.spy.price.toLocaleString()}</span>
                  <span className={`text-[10px] ${demoMarket.spy.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {demoMarket.spy.change >= 0 ? '+' : ''}{demoMarket.spy.change}%
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-hive-muted">10Y Treasury</span>
                <span className="text-sm font-bold">{demoMarket.treasury10y}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-hive-muted">Yield Curve (10Y-2Y)</span>
                <span className={`text-sm font-bold ${demoMarket.yieldCurve >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {demoMarket.yieldCurve >= 0 ? '+' : ''}{demoMarket.yieldCurve}%
                </span>
              </div>
            </div>
          </div>

          <div className="glass-card p-5">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-3">Stock Pipeline</p>
            <div className="space-y-2">
              {pipelineSteps.map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <span className="w-5 text-[10px] text-hive-muted/40 text-right">{i + 1}</span>
                  <div className="flex-1 text-xs py-1 px-2 rounded bg-blue-500/5 text-blue-400/60 ring-1 ring-inset ring-blue-500/10">
                    {step}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-hive-muted mt-3">Runs during market hours (9:30-16:00 ET)</p>
          </div>
        </div>
      </div>

      {/* GICS Sector Heatmap + Earnings Blackout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={14} className="text-blue-400" />
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">GICS Sector Performance</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {demoSectors.map((sector) => {
              const bg = sector.change1d >= 0.5 ? 'bg-emerald-500/15 border-emerald-500/20' :
                         sector.change1d >= 0 ? 'bg-emerald-500/5 border-emerald-500/10' :
                         sector.change1d >= -0.5 ? 'bg-red-500/5 border-red-500/10' :
                         'bg-red-500/15 border-red-500/20';
              return (
                <div key={sector.etf} className={`rounded-lg p-3 border ${bg}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold truncate">{sector.name}</span>
                    <span className="text-[10px] text-hive-muted">{sector.etf}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="text-[10px] text-hive-muted">1d</p>
                      <p className={`text-sm font-bold ${sector.change1d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {sector.change1d >= 0 ? '+' : ''}{sector.change1d.toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-hive-muted">5d</p>
                      <p className={`text-sm font-bold ${sector.change5d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {sector.change5d >= 0 ? '+' : ''}{sector.change5d.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Calendar size={14} className="text-amber-400" />
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Earnings Alerts</p>
          </div>
          <div className="space-y-3">
            {demoEarnings.map((e) => (
              <div key={e.symbol} className={`rounded-lg p-3 border ${
                e.inBlackout ? 'bg-red-500/10 border-red-500/20' : 'bg-white/[0.02] border-white/[0.06]'
              }`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-bold">{e.symbol}</span>
                  {e.inBlackout && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-500/20 text-red-400 ring-1 ring-inset ring-red-500/30 flex items-center gap-1">
                      <AlertTriangle size={10} /> BLACKOUT
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between text-xs text-hive-muted">
                  <span>Earnings: {new Date(e.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                  <span className={e.daysAway <= 3 ? 'text-red-400 font-medium' : ''}>{e.daysAway}d away</span>
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-hive-muted mt-3">Blackout: no new positions 3 days before earnings</p>
        </div>
      </div>

      {/* Recent Stock Cycles */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-blue-400" />
            <h2 className="text-sm font-semibold">Recent Stock Cycles</h2>
          </div>
        </div>
        <table className="w-full">
          <thead>
            <tr className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted border-b border-white/[0.06]">
              <th className="text-left px-5 py-2.5">#</th>
              <th className="text-left px-5 py-2.5">Time</th>
              <th className="text-left px-5 py-2.5">Regime</th>
              <th className="text-right px-5 py-2.5">Stocks</th>
              <th className="text-right px-5 py-2.5">Signals</th>
              <th className="text-right px-5 py-2.5">Trades</th>
              <th className="text-right px-5 py-2.5">Duration</th>
            </tr>
          </thead>
          <tbody>
            {demoCycles.map((c) => (
              <tr key={c.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-3 text-sm text-hive-muted">{c.id}</td>
                <td className="px-5 py-3 text-sm">{new Date(c.started_at).toLocaleString()}</td>
                <td className="px-5 py-3">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    c.regime === 'bull' ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20' :
                    c.regime === 'bear' ? 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20' :
                    'bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/20'
                  }`}>{c.regime.toUpperCase()}</span>
                </td>
                <td className="px-5 py-3 text-right text-sm">{c.stocks_analyzed}</td>
                <td className="px-5 py-3 text-right text-sm">{c.signals}</td>
                <td className="px-5 py-3 text-right text-sm">{c.trades}</td>
                <td className="px-5 py-3 text-right text-sm text-hive-muted">{c.duration}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
