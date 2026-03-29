
'use client';

import {
  BookOpen, Clock, TrendingUp, TrendingDown, ChevronDown, ChevronUp,
  Target, Shield, AlertTriangle, CheckCircle, XCircle,
} from 'lucide-react';
import { DemoBanner } from '@/components/DemoBanner';
import { useState } from 'react';

// ── Demo Trade Journal Data ──

const journalEntries = [
  {
    id: 'T-042',
    symbol: 'NVDA',
    side: 'BUY',
    status: 'OPEN',
    entryPrice: 890,
    currentPrice: 912.50,
    exitPrice: null,
    shares: 12,
    sl: 845,
    tp: 985,
    entryTime: '2026-03-15 14:32 ET',
    exitTime: null,
    exitReason: null,
    conviction: 8,
    confidence: 0.78,
    consensus: 0.83,
    regime: 'BULL',
    pnl: 270,
    pnlPct: 2.53,
    teamVotes: [
      { team: 'Technical', direction: 'BULLISH', conviction: 8, reasoning: 'All timeframes aligned, breakout above $900 resistance with volume.' },
      { team: 'Sentiment', direction: 'BULLISH', conviction: 7, reasoning: 'WSB call volume surging. Put/call 0.62. VIX supportive.' },
      { team: 'Fundamental', direction: 'BULLISH', conviction: 6, reasoning: 'P/E 62 stretched but PEG 1.1 justified by 55% earnings growth.' },
      { team: 'Macro', direction: 'BULLISH', conviction: 7, reasoning: 'AI capex cycle in early innings. Rate environment supports growth.' },
      { team: 'Institutional', direction: 'BULLISH', conviction: 8, reasoning: 'Institutional ownership rising QoQ. No insider selling.' },
      { team: 'News', direction: 'BULLISH', conviction: 9, reasoning: 'Blackwell Ultra demand is strongest product cycle in years.' },
    ],
  },
  {
    id: 'T-039',
    symbol: 'META',
    side: 'BUY',
    status: 'CLOSED',
    entryPrice: 502,
    currentPrice: null,
    exitPrice: 518,
    shares: 15,
    sl: 485,
    tp: 545,
    entryTime: '2026-03-12 10:15 ET',
    exitTime: '2026-03-15 11:42 ET',
    exitReason: 'TP1',
    conviction: 8,
    confidence: 0.76,
    consensus: 0.80,
    regime: 'BULL',
    pnl: 240,
    pnlPct: 3.19,
    teamVotes: [
      { team: 'Technical', direction: 'BULLISH', conviction: 7, reasoning: 'Golden cross formed. RSI 58 with room.' },
      { team: 'Sentiment', direction: 'BULLISH', conviction: 6, reasoning: 'Moderate Reddit mentions. P/C neutral.' },
      { team: 'Fundamental', direction: 'BULLISH', conviction: 8, reasoning: 'P/E 24 reasonable for 20% revenue growth. Reality Labs loss narrowing.' },
      { team: 'Macro', direction: 'BULLISH', conviction: 7, reasoning: 'Comm. services sector in favor.' },
      { team: 'Institutional', direction: 'BULLISH', conviction: 8, reasoning: 'Insider buying by Zuckerberg. Institution % stable.' },
      { team: 'News', direction: 'BULLISH', conviction: 9, reasoning: 'Llama 4 launch drove AI narrative. Threads user growth strong.' },
    ],
  },
  {
    id: 'T-037',
    symbol: 'AMZN',
    side: 'SHORT',
    status: 'CLOSED',
    entryPrice: 185,
    currentPrice: null,
    exitPrice: 188,
    shares: 25,
    sl: 192,
    tp: 170,
    entryTime: '2026-03-11 15:20 ET',
    exitTime: '2026-03-13 09:45 ET',
    exitReason: 'SL',
    conviction: 5,
    confidence: 0.52,
    consensus: 0.50,
    regime: 'BULL',
    pnl: -75,
    pnlPct: -1.62,
    teamVotes: [
      { team: 'Technical', direction: 'BEARISH', conviction: 5, reasoning: 'Below SMA20 but above SMA50. Mixed signals.' },
      { team: 'Sentiment', direction: 'BEARISH', conviction: 4, reasoning: 'Slightly negative Reddit tone. P/C elevated at 1.1.' },
      { team: 'Fundamental', direction: 'BULLISH', conviction: 6, reasoning: 'AWS growth reaccelerating. Cloud business undervalued.' },
      { team: 'Macro', direction: 'BEARISH', conviction: 5, reasoning: 'Consumer discretionary under pressure from rates.' },
      { team: 'Institutional', direction: 'BEARISH', conviction: 5, reasoning: 'Some institutional trimming. Short interest rising.' },
      { team: 'News', direction: 'BULLISH', conviction: 6, reasoning: 'Project Kuiper launch positive catalyst. EU probe manageable.' },
    ],
  },
];

function TradeEntry({ trade }: { trade: typeof journalEntries[0] }) {
  const [expanded, setExpanded] = useState(false);
  const isOpen = trade.status === 'OPEN';
  const isWin = trade.pnl > 0;

  return (
    <div className="glass-card overflow-hidden">
      {/* Header row */}
      <div
        className="px-5 py-4 flex items-center gap-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Status icon */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isOpen ? 'bg-blue-500/10 ring-1 ring-blue-500/20' :
          isWin ? 'bg-emerald-500/10 ring-1 ring-emerald-500/20' :
          'bg-red-500/10 ring-1 ring-red-500/20'
        }`}>
          {isOpen ? <Target size={14} className="text-blue-400" /> :
           isWin ? <CheckCircle size={14} className="text-emerald-400" /> :
           <XCircle size={14} className="text-red-400" />}
        </div>

        {/* Symbol + side */}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold">{trade.symbol}</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${
              trade.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20' : 'bg-red-500/10 text-red-400 ring-red-500/20'
            }`}>{trade.side === 'BUY' ? 'LONG' : 'SHORT'}</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              isOpen ? 'bg-blue-500/10 text-blue-400' : 'bg-white/[0.04] text-hive-muted'
            }`}>{trade.status}</span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-[10px] text-hive-muted">
            <span>{trade.id}</span>
            <span>{trade.entryTime}</span>
            <span>Conv. {trade.conviction}/10</span>
            <span>Conf. {(trade.confidence * 100).toFixed(0)}%</span>
            <span>Consensus {(trade.consensus * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Price info */}
        <div className="ml-auto flex items-center gap-6 shrink-0">
          <div className="text-right">
            <p className="text-[10px] text-hive-muted">Entry</p>
            <p className="text-sm font-mono">${trade.entryPrice}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-hive-muted">{isOpen ? 'Current' : 'Exit'}</p>
            <p className="text-sm font-mono">${isOpen ? trade.currentPrice : trade.exitPrice}</p>
          </div>
          {trade.exitReason && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              trade.exitReason === 'SL' ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'
            }`}>{trade.exitReason}</span>
          )}
          <div className="text-right w-24">
            <p className={`text-sm font-bold ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
              {isWin ? '+' : ''}${trade.pnl}
            </p>
            <p className={`text-[10px] ${isWin ? 'text-emerald-400/60' : 'text-red-400/60'}`}>
              {trade.pnlPct >= 0 ? '+' : ''}{trade.pnlPct}%
            </p>
          </div>
          <div className="text-hive-muted/30">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </div>
      </div>

      {/* Expanded: Agent vote breakdown */}
      {expanded && (
        <div className="px-5 py-4 border-t border-white/[0.06] bg-white/[0.01]">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={12} className="text-blue-400" />
            <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Agent Vote Breakdown</p>
            <span className="text-[10px] text-hive-muted">Regime: {trade.regime}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {trade.teamVotes.map((vote) => {
              const isBullish = vote.direction === 'BULLISH';
              return (
                <div key={vote.team} className="glass-card p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold">{vote.team}</span>
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        isBullish ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                      }`}>{vote.direction}</span>
                      <span className="text-[10px] text-hive-muted">{vote.conviction}/10</span>
                    </div>
                  </div>
                  <div className="h-1 bg-white/[0.04] rounded-full overflow-hidden mb-1.5">
                    <div className={`h-full rounded-full ${isBullish ? 'bg-emerald-500' : 'bg-red-500'}`}
                      style={{ width: `${vote.conviction * 10}%` }} />
                  </div>
                  <p className="text-[10px] text-hive-muted leading-relaxed">{vote.reasoning}</p>
                </div>
              );
            })}
          </div>

          {/* Trade levels */}
          <div className="mt-3 flex items-center gap-6 text-[10px]">
            <span className="text-blue-400">Entry ${trade.entryPrice}</span>
            <span className="text-red-400">SL ${trade.sl}</span>
            <span className="text-emerald-400">TP ${trade.tp}</span>
            <span className="text-hive-muted">{trade.shares} shares</span>
            {trade.exitTime && <span className="text-hive-muted">Closed: {trade.exitTime}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function JournalPage() {
  const openTrades = journalEntries.filter(t => t.status === 'OPEN');
  const closedTrades = journalEntries.filter(t => t.status === 'CLOSED');
  const wins = closedTrades.filter(t => t.pnl > 0).length;
  const losses = closedTrades.filter(t => t.pnl <= 0).length;

  return (
    <div className="slide-up space-y-6">
      <DemoBanner />
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Trade Journal</h1>
        <p className="text-sm text-hive-muted mt-1">
          Every trade with full decision context — which agents voted, why it entered, how it exited
        </p>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">Open Trades</p>
          <p className="text-xl font-bold text-blue-400">{openTrades.length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">Closed Trades</p>
          <p className="text-xl font-bold">{closedTrades.length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">Win Rate</p>
          <p className={`text-xl font-bold ${wins / (wins + losses) >= 0.5 ? 'text-emerald-400' : 'text-red-400'}`}>
            {closedTrades.length > 0 ? `${Math.round(wins / closedTrades.length * 100)}%` : '—'}
          </p>
        </div>
        <div className="glass-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-1">Record</p>
          <p className="text-xl font-bold">
            <span className="text-emerald-400">{wins}W</span>
            <span className="text-hive-muted mx-1">/</span>
            <span className="text-red-400">{losses}L</span>
          </p>
        </div>
      </div>

      {/* Open Trades */}
      {openTrades.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-blue-400 mb-3 flex items-center gap-1.5">
            <Target size={11} /> Open Positions
          </p>
          <div className="space-y-3">
            {openTrades.map((t) => <TradeEntry key={t.id} trade={t} />)}
          </div>
        </div>
      )}

      {/* Closed Trades */}
      {closedTrades.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-3 flex items-center gap-1.5">
            <BookOpen size={11} /> Closed Trades
          </p>
          <div className="space-y-3">
            {closedTrades.map((t) => <TradeEntry key={t.id} trade={t} />)}
          </div>
        </div>
      )}
    </div>
  );
}
