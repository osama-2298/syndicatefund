'use client';

import {
  BarChart3, TrendingUp, MessageSquare, DollarSign, Globe,
  Building2, Newspaper, ArrowRight, Users, Database,
} from 'lucide-react';

const stockTeams = [
  {
    name: 'Technical',
    discipline: 'Price action, chart patterns, and technical indicators for equity markets',
    color: 'blue',
    weight: 1.2,
    agents: [
      { name: 'Lena Karlsson', role: 'StockTrendAgent', desc: 'Moving averages, ADX, Bollinger Bands on daily/weekly charts' },
      { name: 'David Osei', role: 'StockSignalAgent', desc: 'RSI, MACD, Stochastic crossover signals for entry/exit' },
      { name: 'Mika Tanaka', role: 'StockTimingAgent', desc: 'Volume profile, VWAP, and options flow timing' },
      { name: 'Oscar Brennan', role: 'Team Manager', desc: 'Synthesizes technical signals into unified team output' },
    ],
    dataSources: ['Daily OHLCV', 'Weekly charts', 'Volume profile', 'Options chain', 'Moving averages'],
    icon: TrendingUp,
  },
  {
    name: 'Sentiment',
    discipline: 'Social sentiment, market psychology, and smart money positioning',
    color: 'purple',
    weight: 1.0,
    agents: [
      { name: 'Priya Sharma', role: 'StockSocialAgent', desc: 'Reddit (WSB, stocks), Twitter/X fintwit sentiment' },
      { name: 'Alexei Volkov', role: 'StockMarketSentimentAgent', desc: 'Put/call ratios, VIX term structure, AAII survey' },
      { name: 'Sofia Reyes', role: 'StockSmartMoneyAgent', desc: 'Dark pool activity, unusual options flow, insider trades' },
      { name: 'Yara Haddad', role: 'Team Manager', desc: 'Synthesizes sentiment signals into unified team output' },
    ],
    dataSources: ['Reddit API', 'Twitter/X', 'CBOE options data', 'AAII survey', 'Dark pool feeds'],
    icon: MessageSquare,
  },
  {
    name: 'Fundamental',
    discipline: 'Company valuations, earnings quality, and financial health',
    color: 'green',
    weight: 1.3,
    agents: [
      { name: 'Henrik Larsen', role: 'StockValuationAgent', desc: 'P/E, P/S, DCF models, PEG ratios vs sector peers' },
      { name: 'Amara Obi', role: 'StockEarningsAgent', desc: 'EPS trends, revenue growth, earnings surprise history' },
      { name: 'Lucas Weber', role: 'StockQualityAgent', desc: 'ROIC, debt/equity, free cash flow yield, Piotroski F-score' },
      { name: 'Isaac Thornton', role: 'Team Manager', desc: 'Synthesizes fundamental signals into unified team output' },
    ],
    dataSources: ['SEC filings', 'Earnings transcripts', 'Financial ratios', 'Analyst estimates', 'Balance sheets'],
    icon: DollarSign,
  },
  {
    name: 'Macro',
    discipline: 'Macroeconomic factors, rates, dollar, and sector rotation',
    color: 'orange',
    weight: 1.0,
    agents: [
      { name: 'Fatima Al-Rashid', role: 'StockUSReportsAgent', desc: 'CPI, PPI, jobs, GDP, ISM, retail sales impact' },
      { name: 'Jin Park', role: 'StockRatesDollarAgent', desc: 'Fed funds rate, yield curve, DXY, bond market signals' },
      { name: 'Camille Dubois', role: 'StockSectorRotationAgent', desc: 'Business cycle positioning, sector relative strength' },
      { name: 'Zara Kimathi', role: 'Team Manager', desc: 'Synthesizes macro signals into unified team output' },
    ],
    dataSources: ['FRED data', 'Fed minutes', 'BLS reports', 'Treasury yields', 'Sector ETFs'],
    icon: Globe,
  },
  {
    name: 'Institutional',
    discipline: 'Institutional ownership changes and capital flow analysis',
    color: 'cyan',
    weight: 1.1,
    agents: [
      { name: 'Nikolai Petrov', role: 'StockOwnershipAgent', desc: '13F filings, institutional holder changes, hedge fund positions' },
      { name: 'Mei Chen', role: 'StockFlowAgent', desc: 'ETF flows, fund inflows/outflows, margin debt levels' },
      { name: 'Adrian Walsh', role: 'Team Manager', desc: 'Synthesizes institutional signals into unified team output' },
    ],
    dataSources: ['13F filings', 'ETF flow data', 'Margin statistics', 'Fund holdings', 'Insider transactions'],
    icon: Building2,
  },
  {
    name: 'News',
    discipline: 'Breaking news analysis and event-driven impact assessment',
    color: 'pink',
    weight: 0.9,
    agents: [
      { name: 'Raphael Moreno', role: 'StockNewsAgent', desc: 'Real-time news feeds, SEC filings, press releases' },
      { name: 'Nadia Chen', role: 'StockNewsImpactAgent', desc: 'Event classification, historical impact analysis, catalyst scoring' },
      { name: 'Victor Okafor', role: 'Team Manager', desc: 'Synthesizes news signals into unified team output' },
    ],
    dataSources: ['News APIs', 'SEC EDGAR', 'Press releases', 'Earnings calendars', 'Analyst upgrades'],
    icon: Newspaper,
  },
];

const teamColorMap: Record<string, { bg: string; text: string; ring: string; border: string; barBg: string }> = {
  blue:   { bg: 'bg-blue-500/10', text: 'text-blue-400', ring: 'ring-blue-500/20', border: 'border-blue-500/20', barBg: 'bg-blue-500' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-400', ring: 'ring-purple-500/20', border: 'border-purple-500/20', barBg: 'bg-purple-500' },
  green:  { bg: 'bg-emerald-500/10', text: 'text-emerald-400', ring: 'ring-emerald-500/20', border: 'border-emerald-500/20', barBg: 'bg-emerald-500' },
  orange: { bg: 'bg-orange-500/10', text: 'text-orange-400', ring: 'ring-orange-500/20', border: 'border-orange-500/20', barBg: 'bg-orange-500' },
  cyan:   { bg: 'bg-cyan-500/10', text: 'text-cyan-400', ring: 'ring-cyan-500/20', border: 'border-cyan-500/20', barBg: 'bg-cyan-500' },
  pink:   { bg: 'bg-pink-500/10', text: 'text-pink-400', ring: 'ring-pink-500/20', border: 'border-pink-500/20', barBg: 'bg-pink-500' },
};

export default function StockTeamsPage() {
  return (
    <div className="slide-up space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Stock Analysis Teams</h1>
        <p className="text-sm text-hive-muted mt-1">6 specialized teams with 16 agents analyzing equities</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {stockTeams.map((team) => {
          const colors = teamColorMap[team.color];
          const Icon = team.icon;
          return (
            <div key={team.name} className={`glass-card overflow-hidden border-l-2 ${colors.border}`}>
              {/* Header */}
              <div className="px-5 py-4 border-b border-white/[0.06]">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${colors.bg}`}>
                      <Icon size={18} className={colors.text} />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold">{team.name}</h3>
                      <p className="text-xs text-hive-muted mt-0.5">{team.discipline}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${colors.bg} ${colors.text} ring-1 ring-inset ${colors.ring}`}>
                      {team.agents.length} AGENTS
                    </span>
                  </div>
                </div>
              </div>

              {/* Agents List */}
              <div className="px-5 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted mb-2">Agents</p>
                <div className="space-y-2">
                  {team.agents.map((agent) => (
                    <div key={agent.name} className="flex items-start gap-2 py-1">
                      <span className={`mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0 ${
                        agent.role === 'Team Manager' ? 'bg-amber-400' : colors.barBg
                      }`} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{agent.name}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                            agent.role === 'Team Manager'
                              ? 'bg-amber-500/10 text-amber-400'
                              : 'bg-white/[0.04] text-hive-muted'
                          }`}>{agent.role}</span>
                        </div>
                        <p className="text-xs text-hive-muted mt-0.5">{agent.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Data Sources + Weight */}
              <div className="px-5 py-3 border-t border-white/[0.06]">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <Database size={10} className="text-hive-muted" />
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-hive-muted">Data Sources</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-hive-muted">Weight</span>
                    <div className="w-16 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${colors.barBg}`}
                        style={{ width: `${Math.min(team.weight * 50, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-bold">{team.weight.toFixed(1)}x</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {team.dataSources.map((src) => (
                    <span key={src} className="text-[10px] bg-white/[0.04] text-hive-muted px-1.5 py-0.5 rounded">
                      {src}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
