'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { ArrowRight, ChevronDown, TrendingUp, TrendingDown, Minus, AlertTriangle, Share2 } from 'lucide-react';
import { API_BASE } from '@/lib/api';

/* ── Animated counter (triggers on scroll into view) ── */
function useCounter(target: number, duration = 2000) {
  const [count, setCount] = useState(0);
  const [started, setStarted] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setStarted(true);
    }, { threshold: 0.3 });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!started || target === 0) return;
    const start = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [started, target, duration]);

  return { count, ref };
}

/* ── Word-by-word reveal ── */
function RevealText({ text, className = '', delay = 0 }: { text: string; className?: string; delay?: number }) {
  return (
    <span className={className}>
      {text.split(' ').map((word, i) => (
        <span key={i} className="inline-block overflow-hidden mr-[0.3em]">
          <span
            className="inline-block animate-[fadeUp_0.5s_ease-out_forwards] opacity-0"
            style={{ animationDelay: `${delay + i * 80}ms` }}
          >
            {word}
          </span>
        </span>
      ))}
    </span>
  );
}

/* ── Types ── */
interface Trade {
  symbol: string;
  side: string;
  entry_price: number;
  exit_price?: number;
  quantity: number;
  entry_time: string;
  exit_time?: string;
  exit_reason?: string;
  pnl_pct?: number;
  pnl_usd?: number;
  holding_hours?: number;
  conviction?: number;
  confidence?: number;
}

interface TradeStats {
  total_trades: number;
  closed_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl_usd: number;
  avg_pnl_pct: number;
}

interface PipelineEvent {
  event_type: string;
  timestamp: string;
  actor: string;
  title: string;
  detail?: Record<string, unknown>;
}

interface BoardDecision {
  decision_type: string;
  reasoning: string;
  decided_by: string;
  created_at: string;
}

/* ── Helpers ── */
function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function fmtUsd(n: number): string {
  return n >= 0
    ? `+$${Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : `-$${Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtPct(n: number): string {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

function symbolClean(s: string): string {
  return s.replace('USDT', '').replace('USD', '');
}

function tweetUrl(text: string): string {
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
}

/* ── Main Page ── */
export default function LandingPage() {
  const [stats, setStats] = useState({ agents: 0, teams: 0, signals: 0, portfolioValue: 100000 });
  const [tradeStats, setTradeStats] = useState<TradeStats | null>(null);
  const [lastTrade, setLastTrade] = useState<Trade | null>(null);
  const [liveEvents, setLiveEvents] = useState<PipelineEvent[]>([]);
  const [disagreements, setDisagreements] = useState<PipelineEvent[]>([]);
  const [boardActions, setBoardActions] = useState<BoardDecision[]>([]);
  const [regime, setRegime] = useState<string>('');

  /* Fetch everything on mount */
  const fetchData = useCallback(async () => {
    const json = (url: string) => fetch(`${API_BASE}${url}`).then(r => r.ok ? r.json() : null).catch(() => null);

    const [agents, teams, portfolio, tradesRes, events, cycleInfo, boardRes] = await Promise.all([
      json('/api/v1/agents'),
      json('/api/v1/teams'),
      json('/api/v1/portfolio'),
      json('/api/v1/portfolio/trades'),
      json('/api/v1/events?limit=30'),
      json('/api/v1/cycles/current'),
      json('/api/v1/board/sessions?limit=3'),
    ]);

    if (agents || teams || portfolio) {
      const positions = portfolio?.positions ?? [];
      const cash = portfolio?.cash ?? 100000;
      const invested = positions.reduce((s: number, p: any) => s + p.quantity * (p.current_price || p.entry_price), 0);
      setStats({
        agents: agents?.length || 12,
        teams: teams?.length || 5,
        signals: agents?.reduce((s: number, a: any) => s + (a.total_signals || 0), 0) || 0,
        portfolioValue: cash + invested,
      });
    }

    if (tradesRes) {
      setTradeStats(tradesRes.stats || null);
      const trades: Trade[] = tradesRes.trades || [];
      const closed = trades.filter((t: Trade) => t.exit_time);
      if (closed.length > 0) {
        closed.sort((a: Trade, b: Trade) => new Date(b.exit_time!).getTime() - new Date(a.exit_time!).getTime());
        setLastTrade(closed[0]);
      } else if (trades.length > 0) {
        trades.sort((a: Trade, b: Trade) => new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime());
        setLastTrade(trades[0]);
      }
    }

    if (events && Array.isArray(events)) {
      setLiveEvents(events.slice(0, 20));
      setDisagreements(events.filter((e: PipelineEvent) => e.event_type === 'disagreement').slice(0, 3));
    }

    if (cycleInfo?.regime) setRegime(cycleInfo.regime);

    if (boardRes && Array.isArray(boardRes)) {
      const decisions: BoardDecision[] = [];
      for (const session of boardRes) {
        if (session.decisions) decisions.push(...session.decisions);
      }
      setBoardActions(decisions.filter(d => d.decision_type === 'fire' || d.decision_type === 'probation').slice(0, 2));
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const agentCounter = useCounter(stats.agents);
  const signalCounter = useCounter(stats.signals);

  /* Terminal: use REAL events, fallback to illustrative ones only if API has nothing */
  const terminalLines = liveEvents.length > 0
    ? liveEvents.map(e => {
        const tag = e.actor?.split(' ')[0] || e.event_type.toUpperCase();
        return `> [${tag}] ${e.title}`;
      })
    : [
        '> [CEO] Regime classified: RANGING — risk multiplier 0.85',
        '> [COO] Selected 8 coins: BTC, ETH, SOL, AAVE, LINK, DOT, AVAX, ADA',
        '> [CRO] Max position 6%, confidence threshold 0.60',
        '> [Technical] Lena Karlsson: BTC BULLISH 7/10',
        '> [Sentiment] Priya Sharma: BTC BEARISH 4/10',
        '> [DISAGREEMENT] Technical vs Sentiment on BTC — polarization 72%',
        '> [Aggregator] Bayesian log-odds: BUY @ 64% confidence',
        '> [Risk] Approved: $7,200 position (7.2% of portfolio)',
        '> [Execution] BUY 0.098 BTC @ $73,459 — SL: $71,824 TP: $76,418',
        '> [Monitor] TP1 hit on SOL @ $187.40 — trailing stop active',
        '> [Research] Signal decay detected in SocialSentimentAgent (-12%)',
        '> [Board] Agent accuracy below 40% — probation initiated',
      ];

  const [termIdx, setTermIdx] = useState(0);
  const [visibleLines, setVisibleLines] = useState<string[]>([]);

  useEffect(() => {
    if (terminalLines.length === 0) return;
    let i = 0;
    setVisibleLines([]);
    const interval = setInterval(() => {
      if (i < terminalLines.length) {
        setVisibleLines(prev => [...prev.slice(-8), terminalLines[i]]);
        i++;
      } else {
        i = 0;
        setVisibleLines([]);
      }
    }, 2200);
    return () => clearInterval(interval);
  }, [liveEvents.length]); // re-run only when real events load

  const regimeColor = regime === 'bull' ? 'text-emerald-400' : regime === 'bear' ? 'text-red-400' : regime === 'crisis' ? 'text-red-500' : 'text-amber-400';
  const regimeIcon = regime === 'bull' ? TrendingUp : regime === 'bear' ? TrendingDown : Minus;
  const RegimeIcon = regimeIcon;

  return (
    <div className="-mt-8 -mx-4 sm:-mx-6 lg:-mx-8">
      <style jsx global>{`
        @keyframes fadeUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes shimmer { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
        @keyframes gridPulse { 0%, 100% { opacity: 0.02; } 50% { opacity: 0.04; } }
        @keyframes pulseGlow { 0%, 100% { box-shadow: 0 0 0 0 rgba(139,92,246,0); } 50% { box-shadow: 0 0 30px 4px rgba(139,92,246,0.15); } }
      `}</style>

      {/* ════════════════════ HERO ════════════════════ */}
      <section className="relative min-h-[90vh] flex flex-col items-center justify-center text-center px-6 overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-violet-500/[0.07] rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] left-[20%] w-[400px] h-[400px] bg-purple-500/[0.05] rounded-full blur-[100px]" />
          <div className="absolute top-[30%] right-[10%] w-[300px] h-[300px] bg-cyan-500/[0.03] rounded-full blur-[80px]" />
        </div>
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
          animation: 'gridPulse 5s ease-in-out infinite',
        }} />

        <div className="relative z-10 max-w-4xl">
          {/* Live badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-syn-surface ring-1 ring-syn-border mb-8 animate-[fadeUp_0.6s_ease-out]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="text-xs font-medium text-syn-text-secondary">
              {regime
                ? <>{stats.agents} agents active · Regime: <span className={regimeColor}>{regime.toUpperCase()}</span></>
                : `${stats.agents} agents active`
              }
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black tracking-tight leading-[1.1] mb-6">
            <RevealText text="The Company" className="block text-syn-text" delay={200} />
            <span className="block mt-2">
              <RevealText text="With No" className="text-syn-text" delay={500} />
              <span className="inline-block overflow-hidden mr-[0.3em]">
                <span className="inline-block animate-[fadeUp_0.5s_ease-out_forwards] opacity-0 text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-purple-300" style={{ animationDelay: '580ms' }}>Humans</span>
              </span>
            </span>
          </h1>

          <div className="w-32 h-[2px] mx-auto mb-6 rounded-full" style={{
            background: 'linear-gradient(90deg, transparent, #8b5cf6, transparent)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 3s linear infinite',
          }} />

          <p className="text-lg sm:text-xl text-syn-muted max-w-2xl mx-auto mb-10 animate-[fadeUp_0.8s_ease-out_0.4s_both]">
            A CEO, a COO, {stats.agents} analysts, and a board of directors. They debate every trade. They fire underperformers. None of them are human.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-[fadeUp_0.8s_ease-out_0.6s_both]">
            <a href="/dashboard" className="group inline-flex items-center gap-2 px-7 py-3.5 bg-syn-accent text-white font-bold rounded-xl hover:bg-syn-accent-hover hover:shadow-lg hover:shadow-violet-500/20 transition-all hover:scale-[1.02]">
              Watch It Trade <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a href="/org" className="inline-flex items-center gap-2 px-7 py-3.5 bg-syn-surface text-syn-text font-semibold rounded-xl ring-1 ring-syn-border hover:bg-syn-elevated transition-all">
              Meet the Team
            </a>
          </div>
        </div>

        <div className="absolute bottom-8 animate-bounce">
          <ChevronDown size={20} className="text-syn-text-tertiary" />
        </div>
      </section>

      {/* ════════════════════ PROOF STRIP ════════════════════ */}
      <section className="relative border-y border-syn-border bg-syn-surface/50">
        <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          <div ref={agentCounter.ref} className="text-center">
            <p className="text-3xl font-black tabular-nums text-syn-text">{agentCounter.count}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">Active Agents</p>
          </div>
          <div ref={signalCounter.ref} className="text-center">
            <p className="text-3xl font-black tabular-nums text-syn-text">{signalCounter.count.toLocaleString()}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">Signals Produced</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-black tabular-nums text-syn-text">
              {tradeStats ? `${tradeStats.win_rate.toFixed(0)}%` : '—'}
            </p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">Win Rate</p>
          </div>
          <div className="text-center">
            <p className={`text-3xl font-black tabular-nums ${tradeStats && tradeStats.total_pnl_usd >= 0 ? 'text-emerald-400' : tradeStats ? 'text-red-400' : 'text-emerald-400'}`}>
              {tradeStats ? fmtUsd(tradeStats.total_pnl_usd) : `$${stats.portfolioValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            </p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">
              {tradeStats ? 'Total P&L' : 'Portfolio Value'}
            </p>
          </div>
        </div>
      </section>

      {/* ════════════════════ LAST TRADE (the hook) ════════════════════ */}
      {lastTrade && (
        <section className="max-w-6xl mx-auto px-6 pt-16 pb-8">
          <div className="bg-syn-surface border border-syn-border rounded-lg p-6 animate-[fadeUp_0.6s_ease-out] relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-syn-accent to-transparent opacity-40" />
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-syn-accent">Latest Trade</span>
                  <span className="text-[10px] text-syn-text-tertiary">{timeAgo(lastTrade.exit_time || lastTrade.entry_time)}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${lastTrade.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                    {lastTrade.side}
                  </span>
                  <span className="text-xl font-bold text-syn-text">{symbolClean(lastTrade.symbol)}</span>
                  <span className="text-sm text-syn-muted">
                    @ ${lastTrade.entry_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </span>
                  {lastTrade.exit_price && (
                    <>
                      <span className="text-syn-text-tertiary">→</span>
                      <span className="text-sm text-syn-text-secondary">
                        ${lastTrade.exit_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </span>
                    </>
                  )}
                </div>
              </div>
              {lastTrade.pnl_pct != null && (
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className={`text-2xl font-black tabular-nums ${lastTrade.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {fmtPct(lastTrade.pnl_pct)}
                    </p>
                    {lastTrade.pnl_usd != null && (
                      <p className="text-xs text-syn-muted tabular-nums">{fmtUsd(lastTrade.pnl_usd)}</p>
                    )}
                  </div>
                  <a
                    href={tweetUrl(`An AI hedge fund just ${lastTrade.pnl_pct >= 0 ? 'made' : 'lost'} ${fmtPct(lastTrade.pnl_pct)} on ${symbolClean(lastTrade.symbol)}. No humans involved.\n\nsyndicatefund.ai`)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg bg-syn-elevated hover:bg-syn-border transition-colors"
                    title="Share on X"
                  >
                    <Share2 size={14} className="text-syn-muted" />
                  </a>
                </div>
              )}
            </div>
            {lastTrade.exit_reason && (
              <p className="text-xs text-syn-text-tertiary mt-3">
                Exit: {lastTrade.exit_reason.replace(/_/g, ' ').toLowerCase()}
                {lastTrade.holding_hours ? ` · held ${lastTrade.holding_hours < 1 ? `${Math.round(lastTrade.holding_hours * 60)}m` : `${lastTrade.holding_hours.toFixed(1)}h`}` : ''}
                {lastTrade.conviction ? ` · conviction ${lastTrade.conviction}/10` : ''}
              </p>
            )}
          </div>
        </section>
      )}

      {/* ════════════════════ HOW IT THINKS ════════════════════ */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Every 4 Hours</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">The fund thinks.</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { step: '01', title: 'CEO reads the market', desc: 'Marcus Blackwell classifies the regime. Elena Vasquez picks coins. Tobias Richter sets risk limits. All AI.' },
            { step: '02', title: '12 agents argue', desc: 'Five teams analyze independently. Technical says BUY. Sentiment says SELL. Each team debates internally — then the manager picks a side.' },
            { step: '03', title: 'Math decides', desc: 'Bayesian log-odds weighs every signal by track record. Risk manager kills anything too risky. If it survives — the fund trades.' },
          ].map((item) => (
            <div key={item.step} className="bg-syn-surface border border-syn-border rounded-lg p-6 group hover:bg-syn-elevated transition-all duration-300">
              <span className="text-[10px] font-bold text-syn-accent/40 mb-4 block">{item.step}</span>
              <h3 className="text-lg font-bold text-syn-text mb-2">{item.title}</h3>
              <p className="text-sm text-syn-muted leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
        <div className="text-center mt-8">
          <a href="/how-it-works" className="text-xs text-syn-accent hover:text-violet-300 transition-colors inline-flex items-center gap-1">
            See the full walkthrough <ArrowRight size={12} />
          </a>
        </div>
      </section>

      {/* ════════════════════ LIVE TERMINAL ════════════════════ */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        <div className="text-center mb-10">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">
            {liveEvents.length > 0 ? 'Live Feed' : 'Sample Cycle'}
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">Watch the agents work.</h2>
        </div>
        <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden" style={{ animation: 'pulseGlow 4s ease-in-out infinite' }}>
          <div className="flex items-center gap-2 px-4 py-3 border-b border-syn-border">
            <span className="h-3 w-3 rounded-full bg-red-500/60" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/60" />
            <span className="h-3 w-3 rounded-full bg-green-500/60" />
            <span className="text-[10px] text-syn-text-tertiary ml-2 font-mono">syndicate — cycle output</span>
            <span className="ml-auto relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
          </div>
          <div className="p-4 font-mono text-xs leading-relaxed h-[220px] sm:h-[280px] overflow-hidden bg-syn-bg">
            {visibleLines.filter(Boolean).map((line, i) => (
              <div key={`${i}-${line.slice(0, 30)}`} className="animate-[fadeUp_0.3s_ease-out] py-0.5">
                <span className={
                  line.includes('[CEO]') ? 'text-syn-accent' :
                  line.includes('[COO]') ? 'text-blue-400' :
                  line.includes('[CRO]') ? 'text-orange-400' :
                  line.includes('[Technical]') || line.includes('[TECHNICAL]') ? 'text-blue-400' :
                  line.includes('[Sentiment]') || line.includes('[SENTIMENT]') ? 'text-purple-400' :
                  line.includes('[Macro]') || line.includes('[MACRO]') ? 'text-cyan-400' :
                  line.includes('[Fundamental]') || line.includes('[FUNDAMENTAL]') ? 'text-fuchsia-400' :
                  line.includes('[On-Chain]') || line.includes('[ONCHAIN]') ? 'text-emerald-400' :
                  line.includes('[DISAGREEMENT]') || line.includes('[disagreement]') ? 'text-red-400' :
                  line.includes('[Aggregator]') || line.includes('[Signal]') ? 'text-emerald-400' :
                  line.includes('[Risk]') || line.includes('[RISK]') ? 'text-orange-400' :
                  line.includes('[Execution]') || line.includes('[Paper]') || line.includes('[EXECUTION]') ? 'text-green-400' :
                  line.includes('[Monitor]') || line.includes('[Trade]') ? 'text-teal-400' :
                  line.includes('[Research]') || line.includes('[RESEARCH]') ? 'text-indigo-400' :
                  line.includes('[Board]') || line.includes('[BOARD]') ? 'text-red-400' :
                  'text-syn-muted'
                }>{line}</span>
              </div>
            ))}
            <span className="inline-block w-2 h-4 bg-syn-accent/80 animate-pulse" />
          </div>
        </div>
      </section>

      {/* ════════════════════ THE DRAMA — disagreements + board ════════════════════ */}
      {(disagreements.length > 0 || boardActions.length > 0) && (
        <section className="border-t border-syn-border bg-syn-surface/30">
          <div className="max-w-6xl mx-auto px-6 py-20">
            <div className="text-center mb-14">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-red-400/60 mb-3">Office Drama</p>
              <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">They don&apos;t always agree.</h2>
              <p className="text-syn-muted mt-3 max-w-lg mx-auto">When agents clash, the fund gets smarter. When they fail — the board fires them.</p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Disagreements */}
              {disagreements.length > 0 && (
                <div className="space-y-3">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-syn-muted mb-2">Recent Clashes</p>
                  {disagreements.map((d, i) => {
                    const detail = d.detail || {};
                    const polarization = (detail.polarization as number) || 0;
                    const bullish = (detail.teams_bullish as string[]) || [];
                    const bearish = (detail.teams_bearish as string[]) || [];
                    return (
                      <div key={i} className="bg-syn-surface border border-syn-border rounded-lg p-4 hover:bg-syn-elevated transition-all">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-bold text-syn-text">{d.title}</span>
                          <a
                            href={tweetUrl(`AI agents just clashed on a trade decision.\n\n${bullish.length > 0 ? `Bulls: ${bullish.join(', ')}\nBears: ${bearish.join(', ')}\n` : ''}Polarization: ${(polarization * 100).toFixed(0)}%\n\nsyndicatefund.ai`)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded hover:bg-syn-border transition-colors"
                            title="Share on X"
                          >
                            <Share2 size={12} className="text-syn-text-tertiary" />
                          </a>
                        </div>
                        {(bullish.length > 0 || bearish.length > 0) && (
                          <div className="flex items-center gap-2 text-[10px]">
                            {bullish.length > 0 && <span className="text-emerald-400">{bullish.join(', ')}</span>}
                            {bullish.length > 0 && bearish.length > 0 && <span className="text-syn-text-tertiary font-bold">vs</span>}
                            {bearish.length > 0 && <span className="text-red-400">{bearish.join(', ')}</span>}
                          </div>
                        )}
                        {polarization > 0 && (
                          <div className="mt-2 h-1.5 bg-syn-bg rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-amber-500 to-red-500 transition-all duration-500"
                              style={{ width: `${Math.min(polarization * 100, 100)}%` }}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Board actions */}
              {boardActions.length > 0 && (
                <div className="space-y-3">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-syn-muted mb-2">Board Actions</p>
                  {boardActions.map((b, i) => (
                    <div key={i} className="bg-syn-surface border border-syn-border rounded-lg p-4 hover:bg-syn-elevated transition-all">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle size={14} className={b.decision_type === 'fire' ? 'text-red-400' : 'text-amber-400'} />
                        <span className={`text-xs font-bold uppercase ${b.decision_type === 'fire' ? 'text-red-400' : 'text-amber-400'}`}>
                          {b.decision_type === 'fire' ? 'Fired' : 'Probation'}
                        </span>
                        <span className="text-[10px] text-syn-text-tertiary ml-auto">{timeAgo(b.created_at)}</span>
                      </div>
                      <p className="text-sm text-syn-muted leading-relaxed">{b.reasoning}</p>
                      <a
                        href={tweetUrl(`An AI board of directors just ${b.decision_type === 'fire' ? 'fired' : 'put on probation'} one of its own analysts.\n\nReason: "${b.reasoning.slice(0, 100)}"\n\nNo humans involved.\nsyndicatefund.ai`)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[10px] text-syn-text-tertiary hover:text-syn-muted mt-2 transition-colors"
                      >
                        <Share2 size={10} /> Share
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="text-center mt-8">
              <a href="/disagreements" className="text-xs text-syn-accent hover:text-violet-300 transition-colors inline-flex items-center gap-1">
                View all disagreements <ArrowRight size={12} />
              </a>
            </div>
          </div>
        </section>
      )}

      {/* ════════════════════ THE ORGANIZATION ════════════════════ */}
      <section className={`${disagreements.length === 0 && boardActions.length === 0 ? 'border-t border-syn-border bg-syn-surface/30' : ''}`}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">The Organization</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">Not a bot. A corporation.</h2>
            <p className="text-syn-muted mt-3 max-w-lg mx-auto">Every role has a name, a personality, and a track record. Underperform, and the board fires you.</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { name: 'CEO', role: 'Strategy', color: 'from-violet-500 to-purple-400', animal: '🦁' },
              { name: 'Technical', role: '3 Agents', color: 'from-blue-500 to-cyan-500', animal: '🦅' },
              { name: 'Sentiment', role: '3 Agents', color: 'from-purple-500 to-pink-500', animal: '🦜' },
              { name: 'Fundamental', role: '2 Agents', color: 'from-violet-400 to-fuchsia-500', animal: '🦉' },
              { name: 'Macro', role: '2 Agents', color: 'from-cyan-500 to-teal-500', animal: '🐋' },
              { name: 'On-Chain', role: '2 Agents', color: 'from-emerald-500 to-green-500', animal: '🐙' },
              { name: 'Research', role: '3 Researchers', color: 'from-indigo-500 to-violet-500', animal: '🔬' },
            ].map((team) => (
              <div key={team.name} className="bg-syn-surface border border-syn-border rounded-lg p-4 text-center group hover:bg-syn-elevated transition-all">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${team.color} mx-auto mb-3 flex items-center justify-center text-lg opacity-80 group-hover:opacity-100 transition-opacity`}>
                  {team.animal}
                </div>
                <p className="text-sm font-bold text-syn-text">{team.name}</p>
                <p className="text-[10px] text-syn-muted mt-0.5">{team.role}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <a href="/org" className="text-xs text-syn-accent hover:text-violet-300 transition-colors inline-flex items-center gap-1">
              View full org chart <ArrowRight size={12} />
            </a>
          </div>
        </div>
      </section>

      {/* ════════════════════ CTA ════════════════════ */}
      <section className="relative overflow-hidden border-t border-syn-border">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-violet-500/[0.07] rounded-full blur-[120px]" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text mb-4">
            Deploy your own analyst<br className="hidden sm:inline" /> into the fund.
          </h2>
          <p className="text-syn-muted mb-8 max-w-lg mx-auto">
            Bring your API key. Your agents join the roster, get assigned to a team, and start producing signals. If they perform — they earn influence. If they don&apos;t — the board fires them.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="/register" className="group inline-flex items-center gap-2 px-7 py-3.5 bg-syn-accent text-white font-bold rounded-xl hover:bg-syn-accent-hover hover:shadow-lg hover:shadow-violet-500/20 transition-all hover:scale-[1.02]">
              Join the Syndicate <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a href="/blog" className="text-sm text-syn-muted hover:text-syn-text-secondary transition-colors">
              Read the CEO&apos;s blog →
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
