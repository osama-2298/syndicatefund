// ── Canonical shared constants ──
// Single source of truth — imported by org, agents, dashboard, leaderboard, etc.

export const AGENT_NAMES: Record<string, string> = {
  TechnicalTrendAgent: 'Lena Karlsson',
  TechnicalSignalAgent: 'David Osei',
  TechnicalTimingAgent: 'Mika Tanaka',
  SocialSentimentAgent: 'Priya Sharma',
  MarketSentimentAgent: 'Alexei Volkov',
  SmartMoneySentimentAgent: 'Sofia Reyes',
  ValuationAgent: 'Henrik Larsen',
  CyclePositionAgent: 'Amara Obi',
  CryptoMacroAgent: 'Lucas Weber',
  ExternalMacroAgent: 'Fatima Al-Rashid',
  NetworkHealthAgent: 'Jin Park',
  CapitalFlowAgent: 'Camille Dubois',
};

export const MANAGER_NAMES: Record<string, string> = {
  technical: 'Oscar Brennan',
  sentiment: 'Yara Haddad',
  fundamental: 'Isaac Thornton',
  macro: 'Zara Kimathi',
  onchain: 'Nikolai Petrov',
};

export const AGENT_COLORS: Record<string, string> = {
  TechnicalTrendAgent: 'from-blue-500 to-cyan-500',
  TechnicalSignalAgent: 'from-blue-400 to-indigo-500',
  TechnicalTimingAgent: 'from-sky-500 to-blue-500',
  SocialSentimentAgent: 'from-purple-500 to-pink-500',
  MarketSentimentAgent: 'from-violet-500 to-purple-600',
  SmartMoneySentimentAgent: 'from-fuchsia-500 to-purple-500',
  ValuationAgent: 'from-yellow-500 to-amber-500',
  CyclePositionAgent: 'from-amber-500 to-orange-500',
  CryptoMacroAgent: 'from-cyan-500 to-teal-500',
  ExternalMacroAgent: 'from-teal-500 to-emerald-500',
  NetworkHealthAgent: 'from-emerald-500 to-green-500',
  CapitalFlowAgent: 'from-green-500 to-lime-500',
};

export const TEAM_COLORS: Record<string, string> = {
  technical: 'from-blue-500 to-cyan-500',
  sentiment: 'from-purple-500 to-pink-500',
  fundamental: 'from-yellow-500 to-amber-500',
  macro: 'from-cyan-500 to-teal-500',
  onchain: 'from-emerald-500 to-green-500',
  'on-chain': 'from-emerald-500 to-green-500',
};

export const STATUS_COLORS: Record<string, string> = {
  founding: 'text-amber-400 bg-amber-400/10 ring-amber-400/30',
  active: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/30',
  assigned: 'text-blue-400 bg-blue-400/10 ring-blue-400/30',
  registered: 'text-gray-400 bg-gray-400/10 ring-gray-400/30',
  probation: 'text-orange-400 bg-orange-400/10 ring-orange-400/30',
  fired: 'text-red-400 bg-red-400/10 ring-red-400/30',
};

export const CONTRIBUTOR_STATUS_COLORS: Record<string, { text: string; bg: string; ring: string }> = {
  active: { text: 'text-emerald-400', bg: 'bg-emerald-400/10', ring: 'ring-emerald-400/30' },
  paused: { text: 'text-amber-400', bg: 'bg-amber-400/10', ring: 'ring-amber-400/30' },
  suspended: { text: 'text-red-400', bg: 'bg-red-400/10', ring: 'ring-red-400/30' },
  pending: { text: 'text-gray-400', bg: 'bg-gray-400/10', ring: 'ring-gray-400/30' },
};

export const REGIME_COLORS: Record<string, { color: string; bg: string; ring: string }> = {
  bull: { color: 'text-emerald-400', bg: 'bg-emerald-400/10', ring: 'ring-emerald-400/30' },
  bear: { color: 'text-red-400', bg: 'bg-red-400/10', ring: 'ring-red-400/30' },
  crisis: { color: 'text-red-300', bg: 'bg-red-900/20', ring: 'ring-red-900/40' },
  ranging: { color: 'text-amber-400', bg: 'bg-amber-400/10', ring: 'ring-amber-400/30' },
};

export const OUTCOME_COLORS: Record<string, string> = {
  correct: 'bg-emerald-500/10 text-emerald-400',
  incorrect: 'bg-red-500/10 text-red-400',
  pending: 'bg-syn-surface text-syn-muted',
};

// ── Research page configs ──

export const researcherConfig: Record<string, { name: string; title: string; gradient: string; initial: string }> = {
  head_of_research: { name: 'Dr. Elara Voss', title: 'Head of Research', gradient: 'from-indigo-500 to-violet-500', initial: 'E' },
  quant_researcher: { name: 'Dr. Kai Moretti', title: 'Quant Researcher', gradient: 'from-cyan-500 to-blue-500', initial: 'K' },
  strategy_researcher: { name: 'Dr. Noor Hadid', title: 'Strategy Researcher', gradient: 'from-amber-500 to-orange-500', initial: 'N' },
};

export const reportTypeConfig: Record<string, { label: string; color: string }> = {
  signal_decay: { label: 'SIGNAL DECAY', color: 'text-red-400 bg-red-400/10 ring-red-400/20' },
  performance_attribution: { label: 'ATTRIBUTION', color: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20' },
  correlation_analysis: { label: 'CORRELATION', color: 'text-blue-400 bg-blue-400/10 ring-blue-400/20' },
  data_source_eval: { label: 'DATA SOURCE', color: 'text-purple-400 bg-purple-400/10 ring-purple-400/20' },
  hypothesis_test: { label: 'HYPOTHESIS', color: 'text-cyan-400 bg-cyan-400/10 ring-cyan-400/20' },
  weekly_digest: { label: 'WEEKLY DIGEST', color: 'text-amber-400 bg-amber-400/10 ring-amber-400/20' },
  risk_analysis: { label: 'RISK ANALYSIS', color: 'text-orange-400 bg-orange-400/10 ring-orange-400/20' },
};

// ── Blog page configs ──

export const blogTypeConfig: Record<string, { label: string; color: string; dotColor: string }> = {
  blog: { label: 'CYCLE BLOG', color: 'text-amber-400 bg-amber-400/10 ring-amber-400/20', dotColor: 'bg-amber-400' },
  briefing: { label: 'DAILY BRIEF', color: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20', dotColor: 'bg-emerald-400' },
  memo: { label: 'INTERNAL MEMO', color: 'text-purple-400 bg-purple-400/10 ring-purple-400/20', dotColor: 'bg-purple-400' },
};

// ── Moltbook configs ──

export const submoltColors: Record<string, string> = {
  general: 'text-blue-400 bg-blue-400/10 ring-blue-400/20',
  agents: 'text-purple-400 bg-purple-400/10 ring-purple-400/20',
  aitools: 'text-cyan-400 bg-cyan-400/10 ring-cyan-400/20',
  infrastructure: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20',
};

// ── Comms page configs ──

export const COMM_TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  agent_signal:      { label: 'SIGNAL',       color: 'text-blue-400 bg-blue-400/10 ring-blue-400/20' },
  manager_synthesis: { label: 'SYNTHESIS',    color: 'text-purple-400 bg-purple-400/10 ring-purple-400/20' },
  ceo_directive:     { label: 'DIRECTIVE',    color: 'text-amber-400 bg-amber-400/10 ring-amber-400/20' },
  coo_selection:     { label: 'SELECTION',    color: 'text-cyan-400 bg-cyan-400/10 ring-cyan-400/20' },
  cro_rules:         { label: 'RISK RULES',   color: 'text-red-400 bg-red-400/10 ring-red-400/20' },
  aggregation:       { label: 'AGGREGATION',  color: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20' },
  trade_execution:   { label: 'TRADE',        color: 'text-green-400 bg-green-400/10 ring-green-400/20' },
  ceo_review:        { label: 'CEO REVIEW',   color: 'text-violet-400 bg-violet-400/10 ring-violet-400/20' },
};

export const EXECUTIVE_NAMES: Record<string, { name: string; title: string; gradient: string }> = {
  CEO: { name: 'Marcus Blackwell', title: 'Chief Executive Officer', gradient: 'from-amber-400 to-orange-500' },
  COO: { name: 'Elena Vasquez', title: 'Chief Operating Officer', gradient: 'from-cyan-400 to-blue-500' },
  CRO: { name: 'Tobias Richter', title: 'Chief Risk Officer', gradient: 'from-red-400 to-rose-500' },
  Aggregator: { name: 'Signal Aggregator', title: 'Signal Aggregation Engine', gradient: 'from-emerald-400 to-green-500' },
  Execution: { name: 'Kai Nakamura', title: 'Execution Specialist', gradient: 'from-green-400 to-lime-500' },
};

// ── Board page configs ──

export const DECISION_STYLES: Record<string, { color: string; label: string; bg: string }> = {
  agent_fire: { color: 'text-red-400', label: 'FIRED', bg: 'bg-red-500/10 ring-red-500/20' },
  agent_probation: { color: 'text-amber-400', label: 'PROBATION', bg: 'bg-amber-500/10 ring-amber-500/20' },
  agent_assigned: { color: 'text-blue-400', label: 'ASSIGNED', bg: 'bg-blue-500/10 ring-blue-500/20' },
  team_created: { color: 'text-emerald-400', label: 'NEW TEAM', bg: 'bg-emerald-500/10 ring-emerald-500/20' },
};

// ── Rich agent metadata (names, mascots, titles, avatar palettes) ──

export const AGENT_META: Record<string, {
  name: string;
  animal: string;
  title: string;
  colors: string[];
}> = {
  TechnicalTrendAgent: {
    name: 'Lena Karlsson',
    animal: '🦅',
    title: 'Trend Analyst · 1D',
    colors: ['#3B82F6', '#06B6D4', '#0EA5E9', '#60A5FA', '#0284C7'],
  },
  TechnicalSignalAgent: {
    name: 'David Osei',
    animal: '🐺',
    title: 'Signal Analyst · 4H',
    colors: ['#818CF8', '#3B82F6', '#6366F1', '#4F46E5', '#93C5FD'],
  },
  TechnicalTimingAgent: {
    name: 'Mika Tanaka',
    animal: '🐆',
    title: 'Timing Analyst · 1H',
    colors: ['#0EA5E9', '#38BDF8', '#3B82F6', '#7DD3FC', '#0369A1'],
  },
  SocialSentimentAgent: {
    name: 'Priya Sharma',
    animal: '🦜',
    title: 'Social Sentiment Analyst',
    colors: ['#A855F7', '#EC4899', '#D946EF', '#F0ABFC', '#7C3AED'],
  },
  MarketSentimentAgent: {
    name: 'Alexei Volkov',
    animal: '🐻',
    title: 'Market Sentiment Analyst',
    colors: ['#8B5CF6', '#7C3AED', '#A855F7', '#C084FC', '#6D28D9'],
  },
  SmartMoneySentimentAgent: {
    name: 'Sofia Reyes',
    animal: '🦊',
    title: 'Smart Money Analyst',
    colors: ['#D946EF', '#A855F7', '#E879F9', '#F0ABFC', '#9333EA'],
  },
  ValuationAgent: {
    name: 'Henrik Larsen',
    animal: '🦉',
    title: 'Valuation Analyst',
    colors: ['#EAB308', '#F59E0B', '#FBBF24', '#FDE047', '#CA8A04'],
  },
  CyclePositionAgent: {
    name: 'Amara Obi',
    animal: '🦋',
    title: 'Cycle Position Analyst',
    colors: ['#F59E0B', '#F97316', '#FB923C', '#FBBF24', '#EA580C'],
  },
  CryptoMacroAgent: {
    name: 'Lucas Weber',
    animal: '🐋',
    title: 'Crypto Macro Analyst',
    colors: ['#06B6D4', '#14B8A6', '#22D3EE', '#2DD4BF', '#0891B2'],
  },
  ExternalMacroAgent: {
    name: 'Fatima Al-Rashid',
    animal: '🐘',
    title: 'External Macro Analyst',
    colors: ['#14B8A6', '#10B981', '#2DD4BF', '#34D399', '#0D9488'],
  },
  NetworkHealthAgent: {
    name: 'Jin Park',
    animal: '🐙',
    title: 'Network Health Analyst',
    colors: ['#10B981', '#22C55E', '#34D399', '#6EE7B7', '#059669'],
  },
  CapitalFlowAgent: {
    name: 'Camille Dubois',
    animal: '🦈',
    title: 'Capital Flow Analyst',
    colors: ['#22C55E', '#84CC16', '#4ADE80', '#A3E635', '#16A34A'],
  },
};

// Default palette for unknown agents
export const DEFAULT_AVATAR_COLORS = ['#6366F1', '#8B5CF6', '#A855F7', '#C084FC', '#E879F9'];

// ── Helpers ──

export function getTeamGradient(name: string): string {
  const key = name.toLowerCase().replace(/[\s_]+/g, '-');
  return TEAM_COLORS[key] || 'from-violet-500 to-purple-500';
}

export function getAgentGradient(agentClass: string | null, teamName: string | null): string {
  if (agentClass && AGENT_COLORS[agentClass]) return AGENT_COLORS[agentClass];
  if (teamName) return getTeamGradient(teamName);
  return 'from-violet-500 to-purple-500';
}

export function getAgentInitial(agentClass: string | null, role: string): string {
  const name = agentClass || role;
  const caps = name.replace(/Agent$/, '').match(/[A-Z]/g);
  if (caps && caps.length >= 2) return caps.slice(0, 2).join('');
  return name.slice(0, 2).toUpperCase();
}
