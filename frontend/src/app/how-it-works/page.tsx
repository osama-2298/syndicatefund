'use client';

import { useRef, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import {
  Crown, Users, Shield, Zap, Target,
  TrendingUp, ArrowRight, ChevronDown,
  Filter, RefreshCw, BarChart3, Eye,
  Radio, CheckCircle, XCircle,
  Activity, Layers, Clock, Brain,
} from 'lucide-react';

/* ─── Animation Primitives ─── */

function FadeIn({
  children,
  className = '',
  delay = 0,
  y = 30,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function Stagger({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });
  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
      variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

const ease = [0.22, 1, 0.36, 1] as [number, number, number, number];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease } },
};

/* ─── Data ─── */

const PIPELINE = [
  { icon: Crown, label: 'CEO', sub: 'Regime' },
  { icon: Target, label: 'COO', sub: 'Select Coins' },
  { icon: Shield, label: 'CRO', sub: 'Set Risk' },
  { icon: Users, label: '5 Teams', sub: '12 Agents' },
  { icon: Zap, label: 'Fusion', sub: 'Bayesian' },
  { icon: Filter, label: 'Risk Gate', sub: 'Filter' },
  { icon: BarChart3, label: 'Execute', sub: 'Trade' },
  { icon: RefreshCw, label: 'Monitor', sub: 'SL / TP' },
];

const TEAMS = [
  {
    name: 'Technical',
    count: 3,
    gradient: 'from-blue-500 to-cyan-500',
    border: 'hover:border-blue-500/30',
    members: ['Lena Karlsson \u00b7 Trend 1D', 'David Osei \u00b7 Signal 4H', 'Mika Tanaka \u00b7 Timing 1H'],
    sources: 'Price candles, volume, 29+ indicators (RSI, MACD, Bollinger, Ichimoku...)',
    manager: 'Oscar Brennan',
    output: 'BULLISH 7/10',
  },
  {
    name: 'Sentiment',
    count: 3,
    gradient: 'from-purple-500 to-pink-500',
    border: 'hover:border-purple-500/30',
    members: ['Priya Sharma \u00b7 Social', 'Alexei Volkov \u00b7 Market', 'Sofia Reyes \u00b7 Smart Money'],
    sources: 'Reddit, Fear & Greed Index, whale wallet tracking',
    manager: 'Yara Haddad',
    output: 'BEARISH 4/10',
  },
  {
    name: 'Fundamental',
    count: 2,
    gradient: 'from-yellow-500 to-amber-500',
    border: 'hover:border-amber-500/30',
    members: ['Henrik Larsen \u00b7 Valuation', 'Amara Obi \u00b7 Cycle Position'],
    sources: 'CoinGecko, CoinPaprika, tokenomics, NVT ratio',
    manager: 'Isaac Thornton',
    output: 'NEUTRAL 5/10',
  },
  {
    name: 'Macro',
    count: 2,
    gradient: 'from-cyan-500 to-teal-500',
    border: 'hover:border-cyan-500/30',
    members: ['Lucas Weber \u00b7 Crypto Macro', 'Fatima Al-Rashid \u00b7 External Macro'],
    sources: 'Fed rates, DXY, BTC dominance, Polymarket',
    manager: 'Zara Kimathi',
    output: 'BULLISH 6/10',
  },
  {
    name: 'On-Chain',
    count: 2,
    gradient: 'from-emerald-500 to-green-500',
    border: 'hover:border-emerald-500/30',
    members: ['Jin Park \u00b7 Network Health', 'Camille Dubois \u00b7 Capital Flow'],
    sources: 'Blockchain data, DeFiLlama, exchange inflow/outflow',
    manager: 'Nikolai Petrov',
    output: 'BULLISH 6/10',
  },
];

const COINS = ['BTC', 'ETH', 'SOL', 'AAVE', 'LINK', 'DOT', 'AVAX', 'ADA', 'DOGE', 'UNI', 'MATIC', 'ATOM'];
const SELECTED = new Set(['BTC', 'ETH', 'SOL', 'AAVE', 'LINK', 'DOT', 'AVAX', 'ADA']);

/* ─── Animated Pipeline Diagram ─── */

const DN = [
  { id: 'ceo', x: 60, y: 170, label: 'CEO', sub: 'Regime', color: '#f59e0b', letter: 'CE', delay: 0 },
  { id: 'coo', x: 165, y: 170, label: 'COO', sub: 'Coins', color: '#06b6d4', letter: 'CO', delay: 0.45 },
  { id: 'cro', x: 270, y: 170, label: 'CRO', sub: 'Risk', color: '#ef4444', letter: 'CR', delay: 0.9 },
  { id: 'tech', x: 440, y: 42, label: 'Technical', sub: '3 agents', color: '#3b82f6', letter: 'Te', delay: 1.5 },
  { id: 'sent', x: 440, y: 106, label: 'Sentiment', sub: '3 agents', color: '#a855f7', letter: 'Se', delay: 1.5 },
  { id: 'fund', x: 440, y: 170, label: 'Fundamental', sub: '2 agents', color: '#eab308', letter: 'Fu', delay: 1.5 },
  { id: 'macro', x: 440, y: 234, label: 'Macro', sub: '2 agents', color: '#22d3ee', letter: 'Ma', delay: 1.5 },
  { id: 'chain', x: 440, y: 298, label: 'On-Chain', sub: '2 agents', color: '#10b981', letter: 'On', delay: 1.5 },
  { id: 'agg', x: 610, y: 170, label: 'Fusion', sub: 'Bayesian', color: '#10b981', letter: '\u03A3', delay: 2.2 },
  { id: 'risk', x: 740, y: 170, label: 'Risk Gate', sub: 'Filter', color: '#f97316', letter: 'Ri', delay: 2.65 },
  { id: 'exec', x: 875, y: 170, label: 'Execute', sub: 'Trade', color: '#22c55e', letter: 'Ex', delay: 3.1 },
  { id: 'mon', x: 1010, y: 170, label: 'Monitor', sub: 'SL/TP', color: '#14b8a6', letter: 'Mo', delay: 3.55 },
];

const DE = [
  { from: 'ceo', to: 'coo', t0: 0.01, t1: 0.09 },
  { from: 'coo', to: 'cro', t0: 0.09, t1: 0.17 },
  { from: 'cro', to: 'tech', t0: 0.20, t1: 0.34 },
  { from: 'cro', to: 'sent', t0: 0.20, t1: 0.34 },
  { from: 'cro', to: 'fund', t0: 0.20, t1: 0.34 },
  { from: 'cro', to: 'macro', t0: 0.20, t1: 0.34 },
  { from: 'cro', to: 'chain', t0: 0.20, t1: 0.34 },
  { from: 'tech', to: 'agg', t0: 0.37, t1: 0.50 },
  { from: 'sent', to: 'agg', t0: 0.37, t1: 0.50 },
  { from: 'fund', to: 'agg', t0: 0.37, t1: 0.50 },
  { from: 'macro', to: 'agg', t0: 0.37, t1: 0.50 },
  { from: 'chain', to: 'agg', t0: 0.37, t1: 0.50 },
  { from: 'agg', to: 'risk', t0: 0.53, t1: 0.62 },
  { from: 'risk', to: 'exec', t0: 0.64, t1: 0.74 },
  { from: 'exec', to: 'mon', t0: 0.76, t1: 0.88 },
];

const DN_MAP = Object.fromEntries(DN.map(n => [n.id, n]));

// Compute when each node activates — derived from edge timing, not hardcoded.
// A node lights up when the first particle arrives at it (t1 of incoming edges).
// Origin nodes (no incoming edges) light up when their first outgoing edge starts.
const NODE_ACTIVATE: Record<string, number> = {};
for (const node of DN) {
  const incoming = DE.filter(e => e.to === node.id);
  if (incoming.length > 0) {
    NODE_ACTIVATE[node.id] = Math.min(...incoming.map(e => e.t1));
  } else {
    const outgoing = DE.filter(e => e.from === node.id);
    NODE_ACTIVATE[node.id] = outgoing.length > 0 ? Math.min(...outgoing.map(e => e.t0)) : 0;
  }
}
// CEO=0.01, COO=0.09, CRO=0.17, Teams=0.34, Agg=0.50, Risk=0.62, Exec=0.74, Mon=0.88

/* ─── Desktop Pipeline (SVG with RAF-animated flowing dots) ─── */

function PipelineDiagram() {
  const dotsRef = useRef<SVGGElement>(null);
  const edgesRef = useRef<SVGGElement>(null);
  const burstsRef = useRef<SVGGElement>(null);
  const ringsRef = useRef<SVGGElement>(null);
  const glowsRef = useRef<SVGGElement>(null);
  const R = 22;
  const TRAILS = 3;

  useEffect(() => {
    let raf: number;
    const start = performance.now();
    const DUR = 8000;
    const BURST_DUR = 0.07; // duration of burst effect (fraction of cycle)

    const tick = (now: number) => {
      const t = ((now - start) % DUR) / DUR;
      const dots = dotsRef.current;
      const edges = edgesRef.current;
      const bursts = burstsRef.current;
      const rings = ringsRef.current;
      const glows = glowsRef.current;
      if (!dots || !edges || !bursts || !rings || !glows) {
        raf = requestAnimationFrame(tick);
        return;
      }

      // Animate edge glow — edges light up when data flows through
      for (let i = 0; i < DE.length; i++) {
        const { t0, t1 } = DE[i];
        const edgeLine = edges.children[i] as SVGLineElement;
        if (!edgeLine) continue;
        const active = t >= t0 && t <= t1;
        edgeLine.setAttribute('stroke-opacity', active ? '0.35' : '0.06');
        edgeLine.setAttribute('stroke-width', active ? '2' : '1');
      }

      // Animate nodes — burst + ring + glow all synced to particle arrival
      for (let n = 0; n < DN.length; n++) {
        const node = DN[n];
        const burst = bursts.children[n] as SVGCircleElement;
        const ring = rings.children[n] as SVGCircleElement;
        const glow = glows.children[n] as SVGCircleElement;
        if (!burst || !ring || !glow) continue;

        const activateT = NODE_ACTIVATE[node.id] || 0;
        const dt = t - activateT;
        // Wrap-around: also check if we're just past the end of the cycle
        const dtWrapped = dt < 0 ? dt + 1 : dt;

        if (dtWrapped >= 0 && dtWrapped < BURST_DUR) {
          // Burst expanding ring
          const p = dtWrapped / BURST_DUR;
          burst.setAttribute('r', String(R + 14 + p * 22));
          burst.setAttribute('opacity', String(0.5 * (1 - p)));

          // Ring brightens on impact
          const ringBright = 1 - p * 0.7;
          ring.setAttribute('stroke-opacity', String(ringBright));
          ring.setAttribute('stroke-width', String(1.5 + (1 - p) * 1.5));

          // Outer glow flares
          glow.setAttribute('opacity', String(0.5 * (1 - p)));
        } else {
          burst.setAttribute('opacity', '0');

          // Gentle ambient pulse for ring (not completely dark)
          const idle = 0.25 + 0.05 * Math.sin(now / 800 + n);
          ring.setAttribute('stroke-opacity', String(idle));
          ring.setAttribute('stroke-width', '1.5');
          glow.setAttribute('opacity', '0');
        }
      }

      // Animate trailing particles (TRAILS per edge)
      for (let i = 0; i < DE.length; i++) {
        const { from, to, t0, t1 } = DE[i];
        const a = DN_MAP[from], b = DN_MAP[to];

        for (let tr = 0; tr < TRAILS; tr++) {
          const circle = dots.children[i * TRAILS + tr] as SVGCircleElement;
          if (!circle) continue;
          const offset = tr * 0.02;
          const adjustedT = t - offset;

          if (adjustedT < t0 || adjustedT > t1) {
            circle.setAttribute('opacity', '0');
          } else {
            const p = (adjustedT - t0) / (t1 - t0);
            circle.setAttribute('cx', String(a.x + (b.x - a.x) * p));
            circle.setAttribute('cy', String(a.y + (b.y - a.y) * p));
            const fade = p < 0.1 ? p / 0.1 : p > 0.88 ? (1 - p) / 0.12 : 1;
            const trailFade = 1 - tr * 0.3;
            circle.setAttribute('opacity', String(Math.max(0, fade * 0.9 * trailFade)));
          }
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <FadeIn delay={0.6} className="w-full max-w-5xl mx-auto mt-8 mb-2 hidden md:block">
      <svg viewBox="0 0 1070 360" className="w-full h-auto" role="img" aria-label="Syndicate pipeline flow diagram">
        <defs>
          {/* Intense glow for lead particles */}
          <filter id="dg" x="-300%" y="-300%" width="700%" height="700%">
            <feGaussianBlur stdDeviation="8" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          {/* Softer glow for trail particles */}
          <filter id="dg-trail" x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          {/* Node burst flash */}
          <filter id="burst-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="6" />
          </filter>
          {/* Ambient node glow */}
          <filter id="node-ambient" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="12" />
          </filter>
        </defs>

        {/* Connection lines — glow dynamically via RAF */}
        <g ref={edgesRef}>
          {DE.map(({ from, to }, i) => (
            <line key={`e${i}`}
              x1={DN_MAP[from].x} y1={DN_MAP[from].y}
              x2={DN_MAP[to].x} y2={DN_MAP[to].y}
              className="pipe-edge"
              stroke="#8b5cf6" strokeOpacity="0.06" strokeWidth="1"
            />
          ))}
        </g>

        {/* Static base edges (always visible, subtle) */}
        {DE.map(({ from, to }, i) => (
          <line key={`base${i}`}
            x1={DN_MAP[from].x} y1={DN_MAP[from].y}
            x2={DN_MAP[to].x} y2={DN_MAP[to].y}
            stroke="rgba(139,92,246,0.04)" strokeWidth="1" strokeDasharray="4 6"
            className="pipe-edge"
          />
        ))}

        {/* Loop arc (Monitor → CEO) */}
        <path
          d={`M ${DN_MAP.mon.x} ${170 + R + 8} Q ${(DN_MAP.mon.x + DN_MAP.ceo.x) / 2} ${170 + R + 70} ${DN_MAP.ceo.x} ${170 + R + 8}`}
          fill="none" stroke="rgba(139,92,246,0.08)" strokeWidth="1" strokeDasharray="4 4"
        />
        <text x={(DN_MAP.mon.x + DN_MAP.ceo.x) / 2} y={170 + R + 58}
          textAnchor="middle" fill="rgba(139,92,246,0.25)" fontSize="8"
          style={{ fontFamily: 'system-ui, sans-serif' }}>
          ↻ repeat every 4 hours
        </text>

        {/* Node burst flashes (animated via RAF) */}
        <g ref={burstsRef}>
          {DN.map((node) => (
            <circle key={`burst-${node.id}`}
              cx={node.x} cy={node.y} r={R}
              fill={node.color} opacity="0"
              filter="url(#burst-glow)"
            />
          ))}
        </g>

        {/* Flowing comet trails (TRAILS particles per edge, animated via RAF) */}
        <g ref={dotsRef}>
          {DE.flatMap((edge, i) => {
            const fromNode = DN_MAP[edge.from];
            return Array.from({ length: TRAILS }, (_, tr) => (
              <circle key={`d${i}-${tr}`}
                r={tr === 0 ? 4 : 3 - tr * 0.5}
                fill={tr === 0 ? '#c4b5fd' : '#8b5cf6'}
                opacity="0"
                filter={tr === 0 ? 'url(#dg)' : 'url(#dg-trail)'}
              />
            ));
          })}
        </g>

        {/* Ambient glow halos behind nodes */}
        {DN.map((node) => (
          <circle key={`ambient-${node.id}`}
            cx={node.x} cy={node.y} r={R + 20}
            fill={node.color} opacity="0.04"
            filter="url(#node-ambient)"
          />
        ))}

        {/* Node rings (RAF-driven brightness) */}
        <g ref={ringsRef}>
          {DN.map((node) => (
            <circle key={`ring-${node.id}`}
              cx={node.x} cy={node.y} r={R}
              fill="none" stroke={node.color} strokeWidth="1.5" strokeOpacity="0.25"
            />
          ))}
        </g>

        {/* Node outer glows (RAF-driven) */}
        <g ref={glowsRef}>
          {DN.map((node) => (
            <circle key={`glow-${node.id}`}
              cx={node.x} cy={node.y} r={R + 8}
              fill="none" stroke={node.color} strokeWidth="0.5" opacity="0"
            />
          ))}
        </g>

        {/* Nodes (backgrounds + labels, drawn last on top) */}
        {DN.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r={R} fill="#0f0f13" />
            <text x={node.x} y={node.y + 1} textAnchor="middle" dominantBaseline="middle"
              fill="#fafafa" fontSize="10" fontWeight="700"
              style={{ fontFamily: 'system-ui, sans-serif' }}>
              {node.letter}
            </text>
            <text x={node.x} y={node.y + R + 14} textAnchor="middle"
              fill="#a1a1aa" fontSize="9" fontWeight="600"
              style={{ fontFamily: 'system-ui, sans-serif' }}>
              {node.label}
            </text>
            <text x={node.x} y={node.y + R + 25} textAnchor="middle"
              fill="#52525b" fontSize="7.5"
              style={{ fontFamily: 'system-ui, sans-serif' }}>
              {node.sub}
            </text>
          </g>
        ))}
      </svg>
    </FadeIn>
  );
}

/* ─── Mobile Pipeline (animated vertical flow) ─── */

const MOBILE_STAGES = [
  { label: 'CEO', sub: 'Regime', color: '#f59e0b', letter: 'CE' },
  { label: 'COO', sub: 'Coins', color: '#06b6d4', letter: 'CO' },
  { label: 'CRO', sub: 'Risk', color: '#ef4444', letter: 'CR' },
];

const MOBILE_TEAMS = [
  { label: 'Tech', color: '#3b82f6', letter: 'Te' },
  { label: 'Sent', color: '#a855f7', letter: 'Se' },
  { label: 'Fund', color: '#eab308', letter: 'Fu' },
  { label: 'Macro', color: '#22d3ee', letter: 'Ma' },
  { label: 'Chain', color: '#10b981', letter: 'On' },
];

const MOBILE_POST = [
  { label: 'Fusion', sub: 'Bayesian', color: '#10b981', letter: 'Σ' },
  { label: 'Risk', sub: 'Filter', color: '#f97316', letter: 'Ri' },
  { label: 'Execute', sub: 'Trade', color: '#22c55e', letter: 'Ex' },
  { label: 'Monitor', sub: 'SL/TP', color: '#14b8a6', letter: 'Mo' },
];

function MobilePipeline() {
  return (
    <FadeIn delay={0.6} className="md:hidden mt-8 mb-2 w-full max-w-sm mx-auto">
      <div className="relative flex flex-col items-center">
        {/* Executives: vertical */}
        {MOBILE_STAGES.map((stage, i) => (
          <div key={stage.label} className="flex flex-col items-center">
            <MobileNode {...stage} delay={i * 0.7} />
            <div className="w-px h-5 mobile-connector" />
          </div>
        ))}

        {/* Fan-out label */}
        <div className="text-[9px] font-bold uppercase tracking-[0.2em] text-white/15 my-1">5 teams · 12 agents</div>

        {/* Teams: horizontal row */}
        <div className="flex items-center justify-center gap-3 my-2">
          {MOBILE_TEAMS.map((team, i) => (
            <MobileNode key={team.label} {...team} sub="" delay={2.1 + i * 0.1} size={36} fontSize={8} />
          ))}
        </div>

        {/* Converge label */}
        <div className="w-px h-5 mobile-connector" />

        {/* Post-analysis: vertical */}
        {MOBILE_POST.map((stage, i) => (
          <div key={stage.label} className="flex flex-col items-center">
            <MobileNode {...stage} delay={3.1 + i * 0.5} />
            {i < MOBILE_POST.length - 1 && <div className="w-px h-5 mobile-connector" />}
          </div>
        ))}

        {/* Loop indicator */}
        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-white/15">
          <RefreshCw size={10} />
          <span>repeat every 4h</span>
        </div>
      </div>
    </FadeIn>
  );
}

function MobileNode({
  label, sub, color, letter, delay, size = 44, fontSize = 10,
}: {
  label: string; sub?: string; color: string; letter: string; delay: number; size?: number; fontSize?: number;
}) {
  // Parse hex color to rgba for glow
  const r = parseInt(color.slice(1, 3), 16);
  const g = parseInt(color.slice(3, 5), 16);
  const b = parseInt(color.slice(5, 7), 16);
  const glowColor = `rgba(${r},${g},${b},0.45)`;

  return (
    <div className="flex flex-col items-center">
      <div
        className="rounded-full flex items-center justify-center mobile-node"
        style={{
          width: size,
          height: size,
          border: `1.5px solid ${color}`,
          background: '#0f0f13',
          animationDelay: `${delay}s`,
          '--glow-color': glowColor,
        } as React.CSSProperties}
      >
        <span className="font-bold text-white/90" style={{ fontSize }}>{letter}</span>
      </div>
      <span className="text-[9px] font-semibold text-white/50 mt-1">{label}</span>
      {sub && <span className="text-[8px] text-white/25">{sub}</span>}
    </div>
  );
}

/* ─── Page ─── */

export default function HowItWorksPage() {
  return (
    <div className="-mt-8 -mx-4 sm:-mx-6 lg:-mx-8">
      <style jsx global>{`
        @keyframes nodeTravel {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          6% { opacity: 1; transform: scale(1.15); }
          14% { opacity: 0.4; transform: scale(1); }
        }
        @keyframes lineShimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes regimeCycle0 {
          0%, 28% { opacity: 1; transform: scale(1.05); }
          33%, 100% { opacity: 0.3; transform: scale(1); }
        }
        @keyframes regimeCycle1 {
          0%, 32% { opacity: 0.3; transform: scale(1); }
          33%, 61% { opacity: 1; transform: scale(1.05); }
          66%, 100% { opacity: 0.3; transform: scale(1); }
        }
        @keyframes regimeCycle2 {
          0%, 65% { opacity: 0.3; transform: scale(1); }
          66%, 94% { opacity: 1; transform: scale(1.05); }
          100% { opacity: 0.3; transform: scale(1); }
        }
        @keyframes barGrow {
          from { transform: scaleX(0); }
          to { transform: scaleX(1); }
        }
        @keyframes pulseGlow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); }
          50% { box-shadow: 0 0 40px 8px rgba(139, 92, 246, 0.12); }
        }
        @keyframes gridPulse {
          0%, 100% { opacity: 0.015; }
          50% { opacity: 0.03; }
        }
        .pipe-edge {
          stroke-dasharray: 8 6;
          animation: pipeEdgeFlow 1.2s linear infinite;
        }
        @keyframes pipeEdgeFlow {
          to { stroke-dashoffset: -14; }
        }
        .pipe-ring {
          animation: pipeRingWave 5.5s ease-in-out infinite;
        }
        @keyframes pipeRingWave {
          0%, 100% { stroke-opacity: 0.25; }
          5% { stroke-opacity: 1; }
          8% { stroke-opacity: 0.8; }
          18% { stroke-opacity: 0.25; }
        }
        .pipe-glow {
          animation: pipeGlowWave 5.5s ease-in-out infinite;
        }
        @keyframes pipeGlowWave {
          0%, 100% { opacity: 0; }
          5% { opacity: 0.5; }
          8% { opacity: 0.35; }
          18% { opacity: 0; }
        }
        .mobile-node {
          animation: mobileNodePulse 5.5s ease-in-out infinite;
          transition: box-shadow 0.3s ease;
        }
        @keyframes mobileNodePulse {
          0%, 100% { opacity: 0.35; box-shadow: 0 0 0 0 transparent; transform: scale(1); }
          6% { opacity: 1; box-shadow: 0 0 24px 6px var(--glow-color, rgba(139,92,246,0.4)); transform: scale(1.08); }
          10% { opacity: 0.9; box-shadow: 0 0 12px 3px var(--glow-color, rgba(139,92,246,0.2)); transform: scale(1.02); }
          22% { opacity: 0.35; box-shadow: 0 0 0 0 transparent; transform: scale(1); }
        }
        .mobile-connector {
          background: linear-gradient(to bottom, rgba(139,92,246,0.2), rgba(139,92,246,0.05));
          position: relative;
          overflow: visible;
        }
        .mobile-connector::after {
          content: '';
          position: absolute;
          left: -1.5px;
          width: 4px;
          height: 4px;
          border-radius: 50%;
          background: #8b5cf6;
          box-shadow: 0 0 8px 2px rgba(139,92,246,0.5);
          animation: mobileParticle 2.5s ease-in-out infinite;
        }
        @keyframes mobileParticle {
          0%, 100% { top: 0; opacity: 0; }
          10% { opacity: 0.8; }
          90% { opacity: 0.8; }
          95% { top: 100%; opacity: 0; }
        }
      `}</style>

      {/* ═══════════════════════════════════════════════
          HERO
      ═══════════════════════════════════════════════ */}
      <section className="relative flex flex-col items-center text-center px-6 pt-16 sm:pt-20 pb-8 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[900px] h-[600px] bg-violet-500/[0.08] rounded-full blur-[140px]" />
          <div className="absolute bottom-[5%] right-[10%] w-[400px] h-[400px] bg-cyan-500/[0.06] rounded-full blur-[100px]" />
          <div className="absolute top-[15%] left-[5%] w-[350px] h-[350px] bg-amber-500/[0.04] rounded-full blur-[100px]" />
          <div className="absolute top-[50%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-purple-600/[0.04] rounded-full blur-[120px]" />
        </div>
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
          animation: 'gridPulse 5s ease-in-out infinite',
        }} />

        <div className="relative z-10 max-w-4xl">
          <FadeIn delay={0.1}>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-syn-surface ring-1 ring-syn-border mb-8">
              <Clock size={12} className="text-syn-accent" />
              <span className="text-xs font-medium text-syn-text-secondary">Every 4 hours, autonomously</span>
            </div>
          </FadeIn>

          <FadeIn delay={0.25}>
            <h1 className="text-4xl sm:text-5xl lg:text-7xl font-black tracking-tight leading-[1.08] mb-6">
              Inside the{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-purple-300">
                Machine
              </span>
            </h1>
          </FadeIn>

          <FadeIn delay={0.4}>
            <div className="w-24 h-[2px] mx-auto mb-6 rounded-full" style={{
              background: 'linear-gradient(90deg, transparent, #8b5cf6, transparent)',
              backgroundSize: '200% 100%',
              animation: 'lineShimmer 3s linear infinite',
            }} />
          </FadeIn>

          <FadeIn delay={0.5}>
            <p className="text-lg sm:text-xl text-syn-muted max-w-2xl mx-auto leading-relaxed">
              A CEO reads the market. A COO picks coins. 12 agents analyze them in parallel.
              They argue. Math decides who&apos;s right. If the signal survives every gate — the fund trades.
              <br className="hidden sm:block" />
              <span className="text-syn-text-secondary font-medium">No humans involved. Here&apos;s how.</span>
            </p>
          </FadeIn>
        </div>

        {/* Animated pipeline diagram — desktop: horizontal SVG, mobile: vertical flow */}
        <div className="relative z-10 w-full">
          <PipelineDiagram />
          <MobilePipeline />
        </div>

        <div className="mt-6 animate-bounce">
          <ChevronDown size={20} className="text-syn-text-tertiary" />
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          STAGES 1-3: THE EXECUTIVES
      ═══════════════════════════════════════════════ */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <FadeIn className="text-center mb-16">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Stages 1 &mdash; 3</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">The executives set the stage.</h2>
          <p className="text-syn-muted mt-3 max-w-2xl mx-auto">
            Before any analysis begins, three C-suite agents assess the macro environment,
            choose which coins to analyze, and set risk guardrails for the entire cycle.
          </p>
        </FadeIn>

        <Stagger className="grid md:grid-cols-3 gap-6">
          {/* ── CEO ── */}
          <motion.div variants={fadeUp} className="bg-syn-surface border border-syn-border rounded-xl p-6 hover:border-amber-500/20 transition-all duration-300">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-xs font-bold">MB</div>
              <div>
                <p className="text-sm font-bold text-syn-text">Marcus Blackwell</p>
                <p className="text-[10px] text-syn-muted">Chief Executive Officer</p>
              </div>
            </div>
            <p className="text-sm text-syn-text-secondary leading-relaxed mb-5">
              Reads BTC dominance, volatility, Fear & Greed Index, and macro trends. Classifies the market regime and issues a strategic directive to the entire organization.
            </p>
            <div className="space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Market Regime</p>
              <div className="flex gap-2">
                {[
                  { label: 'BULL', cls: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20', anim: 'regimeCycle0' },
                  { label: 'BEAR', cls: 'text-red-400 bg-red-400/10 ring-red-400/20', anim: 'regimeCycle1' },
                  { label: 'RANGING', cls: 'text-amber-400 bg-amber-400/10 ring-amber-400/20', anim: 'regimeCycle2' },
                ].map((r) => (
                  <span
                    key={r.label}
                    className={`text-[10px] font-bold px-2.5 py-1 rounded ring-1 ring-inset ${r.cls}`}
                    style={{ animation: `${r.anim} 6s ease-in-out infinite` }}
                  >
                    {r.label}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>

          {/* ── COO ── */}
          <motion.div variants={fadeUp} className="bg-syn-surface border border-syn-border rounded-xl p-6 hover:border-cyan-500/20 transition-all duration-300">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-white text-xs font-bold">EV</div>
              <div>
                <p className="text-sm font-bold text-syn-text">Elena Vasquez</p>
                <p className="text-[10px] text-syn-muted">Chief Operating Officer</p>
              </div>
            </div>
            <p className="text-sm text-syn-text-secondary leading-relaxed mb-5">
              Scans the crypto market and selects which coins deserve analysis this cycle. Filters by volume, volatility, and opportunity based on the CEO&apos;s regime assessment.
            </p>
            <div className="space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Coin Selection</p>
              <div className="flex flex-wrap gap-1.5">
                {COINS.map((coin) => (
                  <span
                    key={coin}
                    className={`text-[10px] font-mono font-bold px-2 py-1 rounded transition-all duration-500 ${
                      SELECTED.has(coin)
                        ? 'text-cyan-400 bg-cyan-400/10 ring-1 ring-inset ring-cyan-400/30'
                        : 'text-syn-text-tertiary bg-syn-bg/50 line-through opacity-40'
                    }`}
                  >
                    {coin}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>

          {/* ── CRO ── */}
          <motion.div variants={fadeUp} className="bg-syn-surface border border-syn-border rounded-xl p-6 hover:border-red-500/20 transition-all duration-300">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-400 to-rose-500 flex items-center justify-center text-white text-xs font-bold">TR</div>
              <div>
                <p className="text-sm font-bold text-syn-text">Tobias Richter</p>
                <p className="text-[10px] text-syn-muted">Chief Risk Officer</p>
              </div>
            </div>
            <p className="text-sm text-syn-text-secondary leading-relaxed mb-5">
              Sets dynamic risk limits for the cycle: max position sizes, confidence thresholds, sector concentration limits. Adapts to the current regime.
            </p>
            <div className="space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">Risk Limits</p>
              {[
                { label: 'Max Position', value: '6%', pct: 24 },
                { label: 'Min Confidence', value: '0.60', pct: 60 },
                { label: 'Risk Multiplier', value: '0.85', pct: 85 },
              ].map((p) => (
                <div key={p.label} className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-[10px] text-syn-text-tertiary">{p.label}</span>
                    <span className="text-[10px] font-mono font-bold text-red-400">{p.value}</span>
                  </div>
                  <div className="h-1 rounded-full bg-syn-bg overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-red-500 to-rose-400 origin-left"
                      style={{ width: `${p.pct}%`, animation: 'barGrow 1.5s ease-out forwards' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </Stagger>
      </section>

      {/* ═══════════════════════════════════════════════
          STAGE 4: THE TEAMS
      ═══════════════════════════════════════════════ */}
      <section className="relative border-t border-syn-border bg-syn-surface/20 py-24 px-6">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[500px] bg-violet-500/[0.03] rounded-full blur-[140px]" />
        </div>

        <div className="relative z-10 max-w-6xl mx-auto">
          <FadeIn className="text-center mb-16">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Stage 4 &mdash; The Core</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">5 teams. 12 agents. In parallel.</h2>
            <p className="text-syn-muted mt-3 max-w-2xl mx-auto">
              For every selected coin, all five teams run their analysis independently and simultaneously.
              Each team has specialized agents who only see their discipline&apos;s data &mdash; then the team manager synthesizes a single verdict.
            </p>
          </FadeIn>

          <Stagger className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {TEAMS.map((team) => (
              <motion.div
                key={team.name}
                variants={fadeUp}
                className={`bg-syn-surface border border-syn-border rounded-xl p-5 ${team.border} transition-all duration-300 group`}
              >
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${team.gradient} flex items-center justify-center text-white text-xs font-bold mb-4 opacity-80 group-hover:opacity-100 transition-opacity`}>
                  {team.name[0]}
                </div>
                <h3 className="text-sm font-bold text-syn-text mb-1">{team.name}</h3>
                <p className="text-[10px] text-syn-muted mb-4">{team.count} agents &middot; Mgr: {team.manager}</p>

                <div className="space-y-1.5 mb-4">
                  {team.members.map((m) => (
                    <p key={m} className="text-[10px] text-syn-text-secondary leading-snug">{m}</p>
                  ))}
                </div>

                <p className="text-[10px] text-syn-text-tertiary mb-4 leading-relaxed">{team.sources}</p>

                <div className="pt-3 border-t border-syn-border">
                  <p className="text-[10px] text-syn-muted mb-1">Sample output</p>
                  <p className="text-xs font-mono font-bold text-syn-text">{team.output}</p>
                </div>
              </motion.div>
            ))}
          </Stagger>

          <FadeIn delay={0.3} className="text-center mt-10">
            <p className="text-xs text-syn-text-tertiary max-w-lg mx-auto">
              Each team only sees data relevant to their discipline. Technical agents never see Reddit sentiment.
              Macro agents never see price candles. This prevents data leakage and forces genuine multi-perspective analysis.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          STAGES 5-6: FUSION & RISK GATE
      ═══════════════════════════════════════════════ */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <FadeIn className="text-center mb-16">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Stages 5 &mdash; 6</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Math decides. Risk filters.</h2>
          <p className="text-syn-muted mt-3 max-w-2xl mx-auto">
            No voting. No averaging. Each team&apos;s signal gets weighted by their historical accuracy using Bayesian log-odds.
            Then the risk manager kills anything that doesn&apos;t pass.
          </p>
        </FadeIn>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Signal Fusion */}
          <FadeIn>
            <div className="bg-syn-surface border border-syn-border rounded-xl p-6 h-full">
              <div className="flex items-center gap-2 mb-6">
                <Zap size={16} className="text-emerald-400" />
                <h3 className="text-sm font-bold text-syn-text">Bayesian Signal Fusion</h3>
              </div>

              <div className="space-y-3 mb-6">
                {[
                  { team: 'Technical', color: 'bg-blue-500', pct: 70, signal: 'BUY', conf: '7/10' },
                  { team: 'Sentiment', color: 'bg-purple-500', pct: 40, signal: 'SELL', conf: '4/10' },
                  { team: 'Fundamental', color: 'bg-amber-500', pct: 50, signal: 'HOLD', conf: '5/10' },
                  { team: 'Macro', color: 'bg-cyan-500', pct: 60, signal: 'BUY', conf: '6/10' },
                  { team: 'On-Chain', color: 'bg-emerald-500', pct: 65, signal: 'BUY', conf: '6/10' },
                ].map((s) => (
                  <div key={s.team}>
                    <div className="flex justify-between mb-1">
                      <span className="text-[10px] text-syn-text-secondary">{s.team}</span>
                      <span className="text-[10px] font-mono text-syn-muted">{s.signal} {s.conf}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-syn-bg overflow-hidden">
                      <div
                        className={`h-full rounded-full ${s.color} opacity-70 origin-left`}
                        style={{ width: `${s.pct}%`, animation: 'barGrow 1.2s ease-out forwards' }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-3 py-3 border-t border-syn-border">
                <div className="flex-1 h-[1px] bg-gradient-to-r from-transparent to-syn-border" />
                <Zap size={14} className="text-syn-accent" />
                <div className="flex-1 h-[1px] bg-gradient-to-l from-transparent to-syn-border" />
              </div>

              <div className="mt-3 p-3 rounded-lg bg-syn-bg border border-syn-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400 mb-1">Aggregated Signal</p>
                    <p className="text-lg font-bold font-mono text-syn-text">BUY @ 64%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-syn-muted">Consensus</p>
                    <p className="text-sm font-bold font-mono text-syn-text">3 / 5</p>
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>

          {/* Risk Gate */}
          <FadeIn delay={0.15}>
            <div className="bg-syn-surface border border-syn-border rounded-xl p-6 h-full">
              <div className="flex items-center gap-2 mb-6">
                <Shield size={16} className="text-orange-400" />
                <h3 className="text-sm font-bold text-syn-text">Risk Gate</h3>
              </div>

              <p className="text-sm text-syn-text-secondary leading-relaxed mb-6">
                The Risk Manager enforces the CRO&apos;s rules. Even a strong signal gets killed if it violates risk limits.
              </p>

              <div className="space-y-3">
                {[
                  { check: 'Confidence \u2265 0.60', pass: true, detail: '64% \u003E 60% threshold' },
                  { check: 'Position \u2264 6% portfolio', pass: true, detail: '$7,200 = 7.2% \u2014 adjusted down to $6,000' },
                  { check: 'Sector concentration', pass: true, detail: 'L1 sector at 18% (limit: 25%)' },
                  { check: 'Drawdown check', pass: true, detail: 'Portfolio -2.1% (limit: -10%)' },
                  { check: 'Correlation filter', pass: false, detail: 'AVAX corr 0.92 with SOL \u2014 blocked' },
                ].map((item) => (
                  <div key={item.check} className={`flex items-start gap-3 p-3 rounded-lg ${item.pass ? 'bg-emerald-500/5' : 'bg-red-500/5'}`}>
                    {item.pass
                      ? <CheckCircle size={14} className="text-emerald-400 mt-0.5 shrink-0" />
                      : <XCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
                    }
                    <div>
                      <p className={`text-xs font-medium ${item.pass ? 'text-syn-text' : 'text-red-400'}`}>{item.check}</p>
                      <p className="text-[10px] text-syn-muted mt-0.5">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          STAGE 7: EXECUTION
      ═══════════════════════════════════════════════ */}
      <section className="relative border-t border-syn-border bg-syn-surface/20 py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <FadeIn>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Stage 7</p>
              <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">If it survives &mdash;<br />the fund trades.</h2>
              <p className="text-syn-muted leading-relaxed mb-6">
                Signals that pass every gate get turned into trade orders. The Portfolio Manager allocates by sector,
                the Paper Trader calculates entry, stop loss, and take profit levels using ATR-based math, then executes.
              </p>
              <div className="space-y-3">
                {[
                  { icon: Layers, text: 'Portfolio Manager allocates position size by sector and risk budget' },
                  { icon: Activity, text: 'ATR-based stop loss and take profit calculation (1.5\u00d7 ATR SL, 3\u00d7 ATR TP)' },
                  { icon: BarChart3, text: 'Paper trade execution with full audit trail to the database' },
                ].map((item) => (
                  <div key={item.text} className="flex items-start gap-3">
                    <item.icon size={14} className="text-syn-accent mt-1 shrink-0" />
                    <p className="text-sm text-syn-text-secondary">{item.text}</p>
                  </div>
                ))}
              </div>
            </FadeIn>

            {/* Trade card */}
            <FadeIn delay={0.15}>
              <div className="bg-syn-bg border border-syn-border rounded-xl overflow-hidden" style={{ animation: 'pulseGlow 4s ease-in-out infinite' }}>
                <div className="flex items-center justify-between px-5 py-3 border-b border-syn-border">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-xs font-bold text-emerald-400">BUY</span>
                  </div>
                  <span className="text-[10px] font-mono text-syn-muted">2024-03-15 08:00 UTC</span>
                </div>

                <div className="p-5 space-y-4">
                  <div>
                    <p className="text-2xl font-black font-mono text-syn-text">BTC / USDT</p>
                    <p className="text-xs text-syn-muted mt-1">Confidence 64% &middot; Consensus 3/5 teams</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-syn-surface">
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Entry</p>
                      <p className="text-sm font-bold font-mono text-syn-text">$73,459.00</p>
                    </div>
                    <div className="p-3 rounded-lg bg-syn-surface">
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-1">Position</p>
                      <p className="text-sm font-bold font-mono text-syn-text">0.082 BTC</p>
                      <p className="text-[10px] text-syn-text-tertiary">$6,000 (6.0%)</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/10">
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-red-400 mb-1">Stop Loss</p>
                      <p className="text-xs font-bold font-mono text-red-400">$71,824</p>
                      <p className="text-[10px] text-red-400/60">-2.2%</p>
                    </div>
                    <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400 mb-1">TP 1</p>
                      <p className="text-xs font-bold font-mono text-emerald-400">$76,418</p>
                      <p className="text-[10px] text-emerald-400/60">+4.0%</p>
                    </div>
                    <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400 mb-1">TP 2</p>
                      <p className="text-xs font-bold font-mono text-emerald-400">$79,100</p>
                      <p className="text-[10px] text-emerald-400/60">+7.7%</p>
                    </div>
                  </div>
                </div>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          STAGE 8: MONITOR & LOOP
      ═══════════════════════════════════════════════ */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Monitor card */}
          <FadeIn delay={0.1} className="order-2 md:order-1">
            <div className="bg-syn-surface border border-syn-border rounded-xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <Eye size={16} className="text-teal-400" />
                <h3 className="text-sm font-bold text-syn-text">Trade Monitor</h3>
                <span className="ml-auto relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
                </span>
              </div>

              <div className="space-y-3">
                {[
                  { coin: 'BTC', entry: '$73,459', current: '$74,892', pnl: '+1.95%', status: 'Trailing stop active' },
                  { coin: 'ETH', entry: '$3,847', current: '$3,812', pnl: '-0.91%', status: 'Monitoring SL at $3,752' },
                  { coin: 'SOL', entry: '$178.30', current: '$187.40', pnl: '+5.10%', status: 'TP1 hit \u2014 33% sold' },
                ].map((pos) => (
                  <div key={pos.coin} className="flex items-center gap-3 p-3 rounded-lg bg-syn-bg">
                    <span className="text-sm font-bold font-mono text-syn-text w-10">{pos.coin}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-syn-muted">{pos.entry}</span>
                        <ArrowRight size={10} className="text-syn-text-tertiary shrink-0" />
                        <span className="text-[10px] text-syn-text-secondary">{pos.current}</span>
                      </div>
                      <p className="text-[10px] text-syn-text-tertiary mt-0.5">{pos.status}</p>
                    </div>
                    <span className={`text-xs font-bold font-mono shrink-0 ${pos.pnl.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                      {pos.pnl}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t border-syn-border flex items-center gap-2">
                <RefreshCw size={12} className="text-syn-accent" />
                <p className="text-[10px] text-syn-muted">Next cycle in 2h 47m &mdash; monitoring continues between cycles</p>
              </div>
            </div>
          </FadeIn>

          {/* Text */}
          <FadeIn className="order-1 md:order-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">Stage 8</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">Watch. Adjust. Repeat.</h2>
            <p className="text-syn-muted leading-relaxed mb-6">
              Between cycles, the Trade Monitor watches every open position. Stop losses, take profits, and trailing stops
              execute automatically. When the next 4-hour window opens &mdash; the entire machine wakes up again.
            </p>
            <div className="space-y-3">
              {[
                'Stop losses trigger instantly on price breach',
                'TP1 sells 33%, activates trailing stop on the remainder',
                'TP2 closes the entire position',
                'CEO reviews all trades and publishes a cycle blog post',
                'Research team audits agent accuracy over rolling windows',
                'Board of Directors fires underperforming agents',
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-syn-accent mt-1.5 shrink-0" />
                  <p className="text-sm text-syn-text-secondary">{item}</p>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          BY THE NUMBERS
      ═══════════════════════════════════════════════ */}
      <section className="border-t border-syn-border bg-syn-surface/30">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <FadeIn className="text-center mb-14">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">By the Numbers</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Scale of the operation.</h2>
          </FadeIn>

          <Stagger className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { value: '12', label: 'AI Analysts', sub: 'across 5 disciplines' },
              { value: '11', label: 'Data Sources', sub: 'Binance, Reddit, CoinGecko...' },
              { value: '4h', label: 'Cycle Frequency', sub: '6 full cycles per day' },
              { value: '29+', label: 'Tech Indicators', sub: 'RSI, MACD, Ichimoku...' },
              { value: '5', label: 'Analysis Teams', sub: 'Tech, Sent, Fund, Macro, Chain' },
              { value: '3', label: 'Board Members', sub: 'Governance & accountability' },
              { value: '3', label: 'Researchers', sub: 'Auditing agent performance' },
              { value: '0', label: 'Humans', sub: 'Fully autonomous' },
            ].map((stat) => (
              <motion.div key={stat.label} variants={fadeUp} className="text-center p-4">
                <p className="text-3xl sm:text-4xl font-black tabular-nums text-syn-text font-mono">{stat.value}</p>
                <p className="text-xs font-bold text-syn-text-secondary mt-2">{stat.label}</p>
                <p className="text-[10px] text-syn-muted mt-0.5">{stat.sub}</p>
              </motion.div>
            ))}
          </Stagger>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          WHAT MAKES IT DIFFERENT
      ═══════════════════════════════════════════════ */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <FadeIn className="text-center mb-14">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60 mb-3">The Difference</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Not a bot. Not a dashboard.<br className="hidden sm:inline" /> A company that runs itself.
          </h2>
        </FadeIn>

        <Stagger className="grid md:grid-cols-2 gap-4">
          {[
            {
              icon: Brain,
              title: 'Multi-Agent Debate',
              desc: 'Agents disagree with each other. Technical says BUY, Sentiment says SELL. The aggregator weighs both by track record. Disagreement data is logged and analyzed.',
            },
            {
              icon: Radio,
              title: 'Full Transparency',
              desc: 'Every signal, every disagreement, every loss is visible. The CEO publishes blog posts explaining trades. The board publishes firing decisions. Nothing is hidden.',
            },
            {
              icon: TrendingUp,
              title: 'Self-Improving',
              desc: 'Research agents audit analyst performance on rolling windows. Signal decay detection. Meta-labels track which agents actually predicted profitable trades. Bad performers get fired.',
            },
            {
              icon: Eye,
              title: 'Deterministic Core',
              desc: 'The signal aggregator is pure math \u2014 Bayesian log-odds, not another LLM. No hallucination. No drift. The math is the same every time. Only the inputs change.',
            },
          ].map((item) => (
            <motion.div key={item.title} variants={fadeUp} className="bg-syn-surface border border-syn-border rounded-xl p-6 hover:bg-syn-elevated transition-all duration-300">
              <item.icon size={20} className="text-syn-accent mb-3" />
              <h3 className="text-sm font-bold text-syn-text mb-2">{item.title}</h3>
              <p className="text-sm text-syn-muted leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </Stagger>
      </section>

      {/* ═══════════════════════════════════════════════
          CTA
      ═══════════════════════════════════════════════ */}
      <section className="relative overflow-hidden border-t border-syn-border">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-violet-500/[0.06] rounded-full blur-[120px]" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-24 text-center">
          <FadeIn>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">See it in action.</h2>
            <p className="text-syn-muted mb-8 max-w-lg mx-auto">
              The dashboard shows live portfolio, trades, agent signals, disagreements,
              research reports, and the CEO&apos;s blog &mdash; all updated every cycle.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a href="/dashboard" className="group inline-flex items-center gap-2 px-7 py-3.5 bg-syn-accent text-white font-bold rounded-xl hover:bg-syn-accent-hover hover:shadow-lg hover:shadow-violet-500/20 transition-all hover:scale-[1.02]">
                Launch Dashboard <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
              </a>
              <a href="/org" className="inline-flex items-center gap-2 px-7 py-3.5 bg-syn-surface text-syn-text font-semibold rounded-xl ring-1 ring-syn-border hover:bg-syn-elevated transition-all">
                Meet the Team
              </a>
              <a href="/blog" className="text-sm text-syn-muted hover:text-syn-text-secondary transition-colors">
                Read the CEO&apos;s blog
              </a>
            </div>
          </FadeIn>
        </div>
      </section>
    </div>
  );
}
