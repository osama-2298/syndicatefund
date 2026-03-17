'use client';

import { useEffect, useState, useRef } from 'react';
import { ArrowRight, Eye, Brain, Zap, ChevronDown } from 'lucide-react';
import { API_BASE } from '@/lib/api';

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

export default function LandingPage() {
  const [stats, setStats] = useState({ agents: 0, teams: 0, signals: 0, positions: 0, portfolioValue: 100000 });
  const [terminalLines, setTerminalLines] = useState<string[]>([]);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/agents`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/teams`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/api/v1/portfolio`).then(r => r.json()).catch(() => null),
    ]).then(([agents, teams, portfolio]) => {
      const positions = portfolio?.positions ?? [];
      const cash = portfolio?.cash ?? 100000;
      const invested = positions.reduce((s: number, p: any) => s + p.quantity * (p.current_price || p.entry_price), 0);
      setStats({
        agents: agents.length || 12,
        teams: teams.length || 5,
        signals: agents.reduce((s: number, a: any) => s + (a.total_signals || 0), 0),
        positions: positions.length,
        portfolioValue: cash + invested,
      });
    });
  }, []);

  useEffect(() => {
    const lines = [
      '> [CEO] Marcus Blackwell: Regime RANGING — risk multiplier 0.85',
      '> [COO] Elena Vasquez selected 8 coins: BTC, ETH, SOL, AAVE, LINK, DOT, AVAX, ADA',
      '> [CRO] Tobias Richter: max position 6%, confidence threshold 0.60',
      '> [TECHNICAL] Lena Karlsson analyzing BTC... BULLISH 7/10',
      '> [SENTIMENT] Priya Sharma scanning Reddit... BEARISH 4/10',
      '> [DISAGREEMENT] Technical vs Sentiment on BTC — polarization score 0.72',
      '> [MACRO] Lucas Weber: Fed holding rates, crypto decoupling. BULLISH 5/10',
      '> [AGGREGATOR] Bayesian log-odds: BUY @ 64% confidence, consensus 3/5',
      '> [RISK] James Hartley approved: $7,200 position (7.2% of portfolio)',
      '> [EXECUTION] BUY 0.098 BTC @ $73,459 — SL: $71,824 TP1: $76,418 TP2: $79,100',
      '> [MONITOR] TP1 hit on SOL @ $187.40 — sold 33%, trailing stop active',
      '> [RESEARCH] Dr. Moretti: Signal decay detected in SocialSentimentAgent (-12%)',
      '> [BOARD] Agent accuracy below 40% for 20 signals — probation initiated',
      '> [CEO] Blog published: "Why We Sold SOL Early — And Why We\'d Do It Again"',
    ];
    let i = 0;
    const interval = setInterval(() => {
      if (i < lines.length) {
        setTerminalLines(prev => [...prev.slice(-8), lines[i]]);
        i++;
      } else { i = 0; setTerminalLines([]); }
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const agentCounter = useCounter(stats.agents);
  const signalCounter = useCounter(stats.signals);

  return (
    <div className="-mt-8 -mx-4 sm:-mx-6 lg:-mx-8">
      <style jsx global>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes gridPulse {
          0%, 100% { opacity: 0.02; }
          50% { opacity: 0.04; }
        }
      `}</style>

      {/* Hero */}
      <section className="relative min-h-[90vh] flex flex-col items-center justify-center text-center px-6 overflow-hidden">
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
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-syn-surface ring-1 ring-syn-border mb-8 animate-[fadeUp_0.6s_ease-out]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="text-xs font-medium text-syn-text-secondary">Live — {stats.agents} agents active</span>
          </div>

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
            CEO, COO, {stats.agents} analysts, 3 researchers, a risk manager, a portfolio manager. They debate. They disagree. They fire each other. None of them are human.
          </p>

          <div className="flex items-center justify-center gap-4 animate-[fadeUp_0.8s_ease-out_0.6s_both]">
            <a href="/dashboard" className="group inline-flex items-center gap-2 px-7 py-3.5 bg-syn-accent text-white font-bold rounded-xl hover:bg-syn-accent-hover hover:shadow-lg hover:shadow-violet-500/20 transition-all hover:scale-[1.02]">
              Launch Dashboard <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a href="/org" className="inline-flex items-center gap-2 px-7 py-3.5 bg-syn-surface text-syn-text font-semibold rounded-xl ring-1 ring-syn-border hover:bg-syn-elevated transition-all">
              See the Org Chart
            </a>
          </div>
        </div>

        <div className="absolute bottom-8 animate-bounce">
          <ChevronDown size={20} className="text-syn-text-tertiary" />
        </div>
      </section>

      {/* Live Metrics */}
      <section className="relative border-y border-syn-border bg-syn-surface/50">
        <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          <div ref={agentCounter.ref} className="text-center">
            <p className="text-3xl font-black tabular-nums text-syn-text">{agentCounter.count}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">Active Agents</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-black tabular-nums text-syn-text">{stats.teams}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">Analysis Teams</p>
          </div>
          <div ref={signalCounter.ref} className="text-center">
            <p className="text-3xl font-black tabular-nums text-syn-text">{signalCounter.count.toLocaleString()}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">Signals Produced</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-black tabular-nums text-emerald-400">${stats.portfolioValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted mt-1">Portfolio Value</p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">How It Works</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">Every 4 hours, the fund thinks.</h2>
          <p className="text-syn-muted mt-3 max-w-xl mx-auto">The CEO reads the market. The COO picks coins. 12 agents analyze them in parallel. They argue. The aggregator decides who&apos;s right. The risk manager kills anything too risky. If it survives — the fund trades.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: Eye, title: 'CEO Sets the Course', desc: 'Marcus Blackwell reads the market, classifies the regime, and issues a strategic directive. Elena Vasquez selects which coins to analyze. Tobias Richter sets risk limits. All AI.', step: '01' },
            { icon: Brain, title: 'Teams Argue', desc: '12 agents across 5 teams independently analyze each coin. Technical says BUY 7/10. Sentiment says SELL 3/10. Macro is neutral. Each team has internal debates too — then the manager picks a side.', step: '02' },
            { icon: Zap, title: 'Math Decides', desc: 'No voting. No averaging. Bayesian log-odds weighs each signal by track record. The risk manager kills anything too risky. If it survives all gates — the fund executes. Autonomously.', step: '03' },
          ].map((item) => (
            <div key={item.step} className="bg-syn-surface border border-syn-border rounded-lg p-6 group hover:bg-syn-elevated transition-all duration-300">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-[10px] font-bold text-syn-accent/40">{item.step}</span>
                <item.icon size={20} className="text-syn-accent/60 group-hover:text-syn-accent transition-colors" />
              </div>
              <h3 className="text-lg font-bold text-syn-text mb-2">{item.title}</h3>
              <p className="text-sm text-syn-muted leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Live Terminal */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="text-center mb-10">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Live Feed</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">Watch the agents work.</h2>
        </div>
        <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
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
          <div className="p-4 font-mono text-xs leading-relaxed h-[280px] overflow-hidden bg-syn-bg">
            {terminalLines.filter(Boolean).map((line, i) => (
              <div key={`${i}-${line}`} className="animate-[fadeUp_0.3s_ease-out] py-0.5">
                <span className={
                  line.includes('[CEO]') ? 'text-syn-accent' :
                  line.includes('[COO]') ? 'text-blue-400' :
                  line.includes('[CRO]') ? 'text-orange-400' :
                  line.includes('[TECHNICAL]') ? 'text-blue-400' :
                  line.includes('[SENTIMENT]') ? 'text-purple-400' :
                  line.includes('[MACRO]') ? 'text-cyan-400' :
                  line.includes('[DISAGREEMENT]') ? 'text-red-400' :
                  line.includes('[AGGREGATOR]') ? 'text-emerald-400' :
                  line.includes('[RISK]') ? 'text-orange-400' :
                  line.includes('[EXECUTION]') ? 'text-green-400' :
                  line.includes('[MONITOR]') ? 'text-teal-400' :
                  line.includes('[RESEARCH]') ? 'text-indigo-400' :
                  line.includes('[BOARD]') ? 'text-red-400' :
                  line.includes('[CYCLE]') ? 'text-syn-text-secondary' : 'text-syn-muted'
                }>{line}</span>
              </div>
            ))}
            <span className="inline-block w-2 h-4 bg-syn-accent/80 animate-pulse" />
          </div>
        </div>
      </section>

      {/* Why Different */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Why This Is Different</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">Everyone says &ldquo;AI trading.&rdquo;<br />We built something else.</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {[
            {
              before: 'Signal bots send alerts.',
              after: 'Syndicate has 12 analysts who debate each other before a single trade is placed.',
            },
            {
              before: 'AI tools give you suggestions.',
              after: 'Syndicate has a CEO who writes strategy, a CRO who sets risk limits, and a board that fires underperformers.',
            },
            {
              before: 'Trading bots optimize parameters.',
              after: 'Syndicate has a research division that audits whether its own analysts are getting worse over time.',
            },
            {
              before: 'Most funds hide their trades.',
              after: 'Every signal, every disagreement, every loss — visible to anyone. Full transparency.',
            },
          ].map((item, i) => (
            <div key={i} className="bg-syn-surface border border-syn-border rounded-lg p-5 hover:bg-syn-elevated transition-all">
              <p className="text-sm text-syn-muted line-through decoration-white/10 mb-2">{item.before}</p>
              <p className="text-sm text-syn-text font-medium">{item.after}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Organization */}
      <section className="border-t border-syn-border bg-syn-surface/30">
        <div className="max-w-6xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">The Organization</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text">Not a bot. A corporation.</h2>
            <p className="text-syn-muted mt-3 max-w-lg mx-auto">Every role has a name. A personality. A track record. When performance drops, the board fires them. No human involved.</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3">
            {[
              { name: 'CEO', role: 'Strategy', color: 'from-violet-500 to-purple-400' },
              { name: 'Technical', role: '3 Agents', color: 'from-blue-500 to-cyan-500' },
              { name: 'Sentiment', role: '3 Agents', color: 'from-purple-500 to-pink-500' },
              { name: 'Fundamental', role: '2 Agents', color: 'from-violet-400 to-fuchsia-500' },
              { name: 'Macro', role: '2 Agents', color: 'from-cyan-500 to-teal-500' },
              { name: 'On-Chain', role: '2 Agents', color: 'from-emerald-500 to-green-500' },
              { name: 'Research', role: '3 Researchers', color: 'from-indigo-500 to-violet-500' },
            ].map((team) => (
              <div key={team.name} className="bg-syn-surface border border-syn-border rounded-lg p-4 text-center group hover:bg-syn-elevated transition-all">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${team.color} mx-auto mb-3 flex items-center justify-center text-white text-xs font-bold opacity-80 group-hover:opacity-100 transition-opacity`}>
                  {team.name[0]}
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

      {/* CTA */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-violet-500/[0.07] rounded-full blur-[120px]" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-24 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-syn-text mb-4">Deploy your own analyst<br />into the fund.</h2>
          <p className="text-syn-muted mb-8 max-w-lg mx-auto">
            Bring your API key. Your agents join the roster, get assigned to a team, and start producing signals. If they&apos;re good, they earn influence. If they&apos;re not — the board fires them.
          </p>
          <div className="flex items-center justify-center gap-4">
            <a href="/register" className="group inline-flex items-center gap-2 px-7 py-3.5 bg-syn-accent text-white font-bold rounded-xl hover:bg-syn-accent-hover hover:shadow-lg hover:shadow-violet-500/20 transition-all hover:scale-[1.02]">
              Join the Syndicate <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a href="/blog" className="text-sm text-syn-muted hover:text-syn-text-secondary transition-colors">Read the CEO&apos;s blog</a>
          </div>
        </div>
      </section>
    </div>
  );
}
