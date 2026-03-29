'use client';

import { useState } from 'react';

// ── Tree Components ────────────────────────────────────────────────────

function StatusDot({ color }: { color: string }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${color} flex-shrink-0`} />;
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-3.5 h-3.5 text-hive-muted transition-transform duration-150 ${open ? 'rotate-90' : ''}`}
      fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function Node({
  label,
  subtitle,
  badge,
  badgeColor,
  children,
  defaultOpen = false,
  right,
}: {
  label: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
  children?: React.ReactNode;
  defaultOpen?: boolean;
  right?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const hasChildren = !!children;

  return (
    <div className="relative">
      <button
        onClick={() => hasChildren && setOpen(!open)}
        className={`w-full flex items-center gap-2 py-1.5 px-2 rounded transition-colors text-left
          ${hasChildren ? 'hover:bg-hive-border/20 cursor-pointer' : 'cursor-default'}`}
      >
        <span className="w-4 flex-shrink-0 flex items-center justify-center">
          {hasChildren ? <Chevron open={open} /> : <span className="w-1.5 h-1.5 rounded-full bg-hive-border" />}
        </span>
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className="text-sm font-medium">{label}</span>
          {badge && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${badgeColor || 'bg-hive-border text-hive-muted'}`}>
              {badge}
            </span>
          )}
          {subtitle && <span className="text-xs text-hive-muted truncate hidden md:inline">{subtitle}</span>}
        </div>
        {right && <div className="flex-shrink-0">{right}</div>}
      </button>
      {open && hasChildren && (
        <div className="ml-4 pl-4 border-l border-hive-border/30">
          {children}
        </div>
      )}
    </div>
  );
}

function Leaf({
  label,
  sublabel,
  dotColor,
  right,
}: {
  label: string;
  sublabel?: string;
  dotColor?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2 py-1.5 px-2">
      <span className="w-4 flex-shrink-0 flex items-center justify-center">
        {dotColor ? <StatusDot color={dotColor} /> : <span className="w-1.5 h-1.5 rounded-full bg-hive-border" />}
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-sm">{label}</span>
        {sublabel && <span className="text-xs text-hive-muted ml-2">{sublabel}</span>}
      </div>
      {right && <div className="flex-shrink-0 text-xs text-hive-muted">{right}</div>}
    </div>
  );
}

// ── Team Data ──────────────────────────────────────────────────────────

const teams = [
  {
    name: 'Technical',
    badge: 'SYSTEM',
    badgeColor: 'bg-blue-500/20 text-blue-400',
    weight: 1.2,
    manager: 'Oscar Brennan',
    agents: [
      { name: 'Lena Karlsson', role: 'StockTrendAgent', dot: 'bg-blue-400' },
      { name: 'David Osei', role: 'StockSignalAgent', dot: 'bg-blue-400' },
      { name: 'Mika Tanaka', role: 'StockTimingAgent', dot: 'bg-blue-400' },
    ],
  },
  {
    name: 'Sentiment',
    badge: 'SYSTEM',
    badgeColor: 'bg-purple-500/20 text-purple-400',
    weight: 1.0,
    manager: 'Yara Haddad',
    agents: [
      { name: 'Priya Sharma', role: 'StockSocialAgent', dot: 'bg-purple-400' },
      { name: 'Alexei Volkov', role: 'StockMarketSentimentAgent', dot: 'bg-purple-400' },
      { name: 'Sofia Reyes', role: 'StockSmartMoneyAgent', dot: 'bg-purple-400' },
    ],
  },
  {
    name: 'Fundamental',
    badge: 'SYSTEM',
    badgeColor: 'bg-emerald-500/20 text-emerald-400',
    weight: 1.3,
    manager: 'Isaac Thornton',
    agents: [
      { name: 'Henrik Larsen', role: 'StockValuationAgent', dot: 'bg-emerald-400' },
      { name: 'Amara Obi', role: 'StockEarningsAgent', dot: 'bg-emerald-400' },
      { name: 'Lucas Weber', role: 'StockQualityAgent', dot: 'bg-emerald-400' },
    ],
  },
  {
    name: 'Macro',
    badge: 'SYSTEM',
    badgeColor: 'bg-orange-500/20 text-orange-400',
    weight: 1.0,
    manager: 'Zara Kimathi',
    agents: [
      { name: 'Fatima Al-Rashid', role: 'StockUSReportsAgent', dot: 'bg-orange-400' },
      { name: 'Jin Park', role: 'StockRatesDollarAgent', dot: 'bg-orange-400' },
      { name: 'Camille Dubois', role: 'StockSectorRotationAgent', dot: 'bg-orange-400' },
    ],
  },
  {
    name: 'Institutional',
    badge: 'SYSTEM',
    badgeColor: 'bg-cyan-500/20 text-cyan-400',
    weight: 1.1,
    manager: 'Adrian Walsh',
    agents: [
      { name: 'Nikolai Petrov', role: 'StockOwnershipAgent', dot: 'bg-cyan-400' },
      { name: 'Mei Chen', role: 'StockFlowAgent', dot: 'bg-cyan-400' },
    ],
  },
  {
    name: 'News',
    badge: 'SYSTEM',
    badgeColor: 'bg-pink-500/20 text-pink-400',
    weight: 0.9,
    manager: 'Victor Okafor',
    agents: [
      { name: 'Raphael Moreno', role: 'StockNewsAgent', dot: 'bg-pink-400' },
      { name: 'Nadia Chen', role: 'StockNewsImpactAgent', dot: 'bg-pink-400' },
    ],
  },
];

// ── Page ───────────────────────────────────────────────────────────────

export default function StockOrgPage() {
  return (
    <div className="slide-up max-w-3xl mx-auto py-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Stock Organization</h1>
        <p className="text-hive-muted text-sm">
          6 teams, 16 agents. Click to expand.
        </p>
      </div>

      <div className="bg-hive-card border border-hive-border rounded-xl p-3">
        <Node
          label="Marcus Blackwell — Stock CEO"
          subtitle="Strategic direction for equities"
          badge="EXECUTIVE"
          badgeColor="bg-blue-500/20 text-blue-400"
          defaultOpen={true}
        >
          <Node label="Elena Vasquez — Stock COO" subtitle="Stock selection from S&P 500">
            <Leaf label="Selects which stocks to analyze each cycle from S&P 500 based on volume, momentum, and CEO strategy" />
            <Leaf label="Filters by market cap, average volume, and sector diversification requirements" />
          </Node>

          <Node label="Tobias Richter — Stock CRO" subtitle="Risk management (lower vol = larger positions)">
            <Leaf label="Sets position limits calibrated for stock volatility (smaller % moves vs crypto)" />
            <Node label="James Hartley — Risk Manager" subtitle="Enforces CRO rules on all stock trades">
              <Leaf label="Position sizing (quarter-Kelly, max 5% per position)" />
              <Leaf label="Portfolio-level drawdown halt at -10%" />
              <Leaf label="Sector concentration limits (max 25% per sector)" />
              <Leaf label="Short exposure cap (max 30% of portfolio)" />
            </Node>
          </Node>

          <Node label="Analysis Division" subtitle="6 teams, 16 agents" defaultOpen={true}>
            {teams.map((team) => (
              <Node
                key={team.name}
                label={`${team.name} Team`}
                badge={team.badge}
                badgeColor={team.badgeColor}
                right={<span className="text-xs text-hive-muted">{team.weight.toFixed(1)}x</span>}
              >
                <Leaf
                  label={`${team.manager} — ${team.name} Manager`}
                  sublabel="Synthesizes agent signals"
                  dotColor="bg-amber-400"
                />
                {team.agents.map((agent) => (
                  <Leaf
                    key={agent.name}
                    label={`${agent.name} — ${agent.role}`}
                    dotColor={agent.dot}
                  />
                ))}
              </Node>
            ))}
          </Node>

          <Node label="Diana Frost — Head of Portfolio" subtitle="11 GICS sector allocation">
            <Leaf label="Technology sector" />
            <Leaf label="Health Care sector" />
            <Leaf label="Financials sector" />
            <Leaf label="Consumer Discretionary sector" />
            <Leaf label="Communication Services sector" />
            <Leaf label="Industrials sector" />
            <Leaf label="Consumer Staples sector" />
            <Leaf label="Energy sector" />
            <Leaf label="Utilities sector" />
            <Leaf label="Real Estate sector" />
            <Leaf label="Materials sector" />
          </Node>

          <Node label="Kai Nakamura — Head of Execution" subtitle="Market hours aware paper trader">
            <Leaf label="Paper Trader" sublabel="Executes during market hours (9:30-16:00 ET)" />
            <Leaf label="Trade Monitor" sublabel="SL / TP / trailing stops" />
            <Leaf label="Trade Ledger" sublabel="P&L tracking and calibration" />
            <Leaf label="Market Hours Guard" sublabel="Blocks execution outside trading hours" />
          </Node>

          <Node label="Soren Lindqvist — Signal Aggregator" subtitle="Bayesian + earnings blackout filter">
            <Leaf label="Bayesian log-odds combination (6 teams)" />
            <Leaf label="Macro gate / Technical gate" />
            <Leaf label="Earnings blackout filter" sublabel="No new positions 3 days before earnings" />
            <Leaf label="Sector correlation check" />
            <Leaf label="Polarization detection" />
            <Leaf label="Close-call detection" />
          </Node>
        </Node>
      </div>
    </div>
  );
}
