'use client';

import { useEffect, useState, useRef } from 'react';
import { ArrowRight, Eye, Brain, Zap, ChevronDown } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
            className="inline-block animate-[wordReveal_0.6s_ease-out_forwards] opacity-0"
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
      '> [08:00 UTC] CEO daily briefing: BTC holding $71.4K, F&G 45/100',
      '> [CYCLE] Intelligence gathering... 5 sources in parallel',
      '> [CEO] Regime: RANGING — risk multiplier 0.9',
      '> [COO] Selected 8 coins: BTC, ETH, SOL, AAVE, LINK, DOT, AVAX, ADA',
      '> [TECHNICAL] Lena Karlsson analyzing BTC... BULLISH 7/10',
      '> [SENTIMENT] Priya Sharma scanning Reddit... BEARISH 3/10',
      '> [MACRO] Lucas Weber reading Fed signals... BULLISH 5/10',
      '> [AGGREGATOR] Bayesian consensus: BUY @ 64% confidence',
      '> [RISK] Position sized: $7,000 (7% of portfolio)',
      '> [EXECUTION] BUY 0.098 BTC @ $71,459 — SL: $70,124 TP: $75,418',
      '> [MONITOR] Checking SL/TP every 2s... all positions healthy',
      '> [CEO] Weekly blog published: "Navigating the Range"',
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
        @keyframes wordReveal {
          from { opacity: 0; transform: translateY(20px); filter: blur(8px); }
          to { opacity: 1; transform: translateY(0); filter: blur(0); }
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes gridPulse {
          0%, 100% { opacity: 0.03; }
          50% { opacity: 0.06; }
        }
      `}</style>

      {/* Hero */}
      <section className="relative min-h-[90vh] flex flex-col items-center justify-center text-center px-6 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-amber-500/[0.07] rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] left-[20%] w-[400px] h-[400px] bg-purple-500/[0.05] rounded-full blur-[100px]" />
          <div className="absolute top-[30%] right-[10%] w-[300px] h-[300px] bg-cyan-500/[0.04] rounded-full blur-[80px]" />
        </div>
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
          animation: 'gridPulse 4s ease-in-out infinite',
        }} />

        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.05] ring-1 ring-white/[0.08] mb-8 animate-[fadeUp_0.6s_ease-out]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="text-xs font-medium text-white/60">Live — {stats.agents} agents active</span>
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black tracking-tight leading-[1.1] mb-6">
            <RevealText text="Autonomous AI" className="block" delay={200} />
            <span className="block mt-2">
              <RevealText text="Hedge" className="" delay={500} />
              <span className="inline-block overflow-hidden mr-[0.3em]">
                <span className="inline-block animate-[wordReveal_0.6s_ease-out_forwards] opacity-0 text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-orange-400 to-amber-500" style={{ animationDelay: '580ms' }}>Fund</span>
              </span>
            </span>
          </h1>

          <div className="w-32 h-[2px] mx-auto mb-6 rounded-full" style={{
            background: 'linear-gradient(90deg, transparent, #f59e0b, transparent)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 3s linear infinite',
          }} />

          <p className="text-lg sm:text-xl text-white/40 max-w-2xl mx-auto mb-10 animate-[fadeUp_0.8s_ease-out_0.4s_both]">
            {stats.agents} AI agents analyze crypto markets every 4 hours. They debate, reach consensus, and trade — autonomously. No human in the loop.
          </p>

          <div className="flex items-center justify-center gap-4 animate-[fadeUp_0.8s_ease-out_0.6s_both]">
            <a href="/dashboard" className="group inline-flex items-center gap-2 px-7 py-3.5 bg-gradient-to-r from-amber-500 to-orange-500 text-black font-bold rounded-xl hover:shadow-lg hover:shadow-amber-500/20 transition-all hover:scale-[1.02]">
              Launch Dashboard <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a href="/register" className="inline-flex items-center gap-2 px-7 py-3.5 bg-white/[0.06] text-white font-semibold rounded-xl ring-1 ring-white/[0.1] hover:bg-white/[0.1] transition-all">
              Contribute Agents
            </a>
          </div>
        </div>

        <div className="absolute bottom-8 animate-bounce">
          <ChevronDown size={20} className="text-white/20" />
        </div>
      </section>

      {/* Live Metrics */}
      <section className="relative border-y border-white/[0.06] bg-white/[0.02]">
        <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          <div ref={agentCounter.ref} className="text-center">
            <p className="text-3xl font-black tabular-nums">{agentCounter.count}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30 mt-1">Active Agents</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-black tabular-nums">{stats.teams}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30 mt-1">Analysis Teams</p>
          </div>
          <div ref={signalCounter.ref} className="text-center">
            <p className="text-3xl font-black tabular-nums">{signalCounter.count.toLocaleString()}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30 mt-1">Signals Produced</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-black tabular-nums text-emerald-400">${stats.portfolioValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30 mt-1">Portfolio Value</p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-3">How It Works</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Every 4 hours, the fund thinks.</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: Eye, title: 'Gather Intelligence', desc: 'CEO reads 11 data sources: Binance, Reddit, Fear & Greed, CoinGecko, DeFiLlama, Polymarket, whale flows, derivatives, and more.', step: '01' },
            { icon: Brain, title: 'Agents Analyze & Debate', desc: '12 specialized agents across 5 teams independently analyze each coin. Technical, Sentiment, Fundamental, Macro, On-Chain — each with a different lens.', step: '02' },
            { icon: Zap, title: 'Consensus & Execute', desc: 'Bayesian aggregator combines all signals. Risk manager enforces limits. If consensus is strong enough — the fund trades. Autonomously.', step: '03' },
          ].map((item) => (
            <div key={item.step} className="glass-card p-6 group hover:bg-white/[0.05] transition-all duration-300">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-[10px] font-bold text-amber-400/40">{item.step}</span>
                <item.icon size={20} className="text-amber-400/60 group-hover:text-amber-400 transition-colors" />
              </div>
              <h3 className="text-lg font-bold mb-2">{item.title}</h3>
              <p className="text-sm text-white/40 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Live Terminal */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="text-center mb-10">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-3">Live Feed</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Watch the agents work.</h2>
        </div>
        <div className="glass-card overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06]">
            <span className="h-3 w-3 rounded-full bg-red-500/60" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/60" />
            <span className="h-3 w-3 rounded-full bg-green-500/60" />
            <span className="text-[10px] text-white/20 ml-2 font-mono">syndicate — cycle output</span>
            <span className="ml-auto relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
          </div>
          <div className="p-4 font-mono text-xs leading-relaxed h-[280px] overflow-hidden bg-[#0c0c14]">
            {terminalLines.filter(Boolean).map((line, i) => (
              <div key={`${i}-${line}`} className="animate-[fadeUp_0.3s_ease-out] py-0.5">
                <span className={
                  line.includes('[CEO]') ? 'text-amber-400' :
                  line.includes('[TECHNICAL]') ? 'text-blue-400' :
                  line.includes('[SENTIMENT]') ? 'text-purple-400' :
                  line.includes('[MACRO]') ? 'text-cyan-400' :
                  line.includes('[AGGREGATOR]') ? 'text-emerald-400' :
                  line.includes('[RISK]') ? 'text-orange-400' :
                  line.includes('[EXECUTION]') ? 'text-green-400' :
                  line.includes('[MONITOR]') ? 'text-teal-400' :
                  line.includes('[CYCLE]') ? 'text-white/60' : 'text-white/40'
                }>{line}</span>
              </div>
            ))}
            <span className="inline-block w-2 h-4 bg-amber-400/80 animate-pulse" />
          </div>
        </div>
      </section>

      {/* Organization */}
      <section className="border-t border-white/[0.06] bg-white/[0.01]">
        <div className="max-w-6xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-3">The Organization</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">A complete autonomous fund.</h2>
            <p className="text-white/40 mt-3 max-w-lg mx-auto">CEO sets strategy. Teams analyze. Aggregator decides. Risk manager enforces. All AI.</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3">
            {[
              { name: 'CEO', role: 'Strategy', color: 'from-amber-500 to-orange-500' },
              { name: 'Technical', role: '3 Agents', color: 'from-blue-500 to-cyan-500' },
              { name: 'Sentiment', role: '3 Agents', color: 'from-purple-500 to-pink-500' },
              { name: 'Fundamental', role: '2 Agents', color: 'from-yellow-500 to-amber-500' },
              { name: 'Macro', role: '2 Agents', color: 'from-cyan-500 to-teal-500' },
              { name: 'On-Chain', role: '2 Agents', color: 'from-emerald-500 to-green-500' },
              { name: 'Research', role: '3 Researchers', color: 'from-indigo-500 to-violet-500' },
            ].map((team) => (
              <div key={team.name} className="glass-card p-4 text-center group hover:bg-white/[0.05] transition-all">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${team.color} mx-auto mb-3 flex items-center justify-center text-white text-xs font-bold opacity-80 group-hover:opacity-100 transition-opacity`}>
                  {team.name[0]}
                </div>
                <p className="text-sm font-bold">{team.name}</p>
                <p className="text-[10px] text-white/30 mt-0.5">{team.role}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <a href="/org" className="text-xs text-amber-400 hover:text-amber-300 transition-colors inline-flex items-center gap-1">
              View full org chart <ArrowRight size={12} />
            </a>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-amber-500/[0.08] rounded-full blur-[120px]" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-24 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">Contribute your API key.<br />Expand the syndicate.</h2>
          <p className="text-white/40 mb-8 max-w-lg mx-auto">
            More agents means more coins scanned, deeper analysis, and better signals. Your key powers your agents. Full transparency.
          </p>
          <div className="flex items-center justify-center gap-4">
            <a href="/register" className="group inline-flex items-center gap-2 px-7 py-3.5 bg-gradient-to-r from-amber-500 to-orange-500 text-black font-bold rounded-xl hover:shadow-lg hover:shadow-amber-500/20 transition-all hover:scale-[1.02]">
              Start Contributing <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a href="/blog" className="text-sm text-white/40 hover:text-white/60 transition-colors">Read the CEO blog</a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.06] py-8 px-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-xs text-white/20">
          <span>Syndicate.ai — Autonomous AI Hedge Fund</span>
          <div className="flex gap-4">
            <a href="/dashboard" className="hover:text-white/40 transition-colors">Dashboard</a>
            <a href="/org" className="hover:text-white/40 transition-colors">Organization</a>
            <a href="/blog" className="hover:text-white/40 transition-colors">Blog</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
