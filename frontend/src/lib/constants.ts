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

export const REGIME_COLORS: Record<string, { color: string; bg: string; ring: string }> = {
  bull: { color: 'text-emerald-400', bg: 'bg-emerald-400/10', ring: 'ring-emerald-400/30' },
  bear: { color: 'text-red-400', bg: 'bg-red-400/10', ring: 'ring-red-400/30' },
  crisis: { color: 'text-red-300', bg: 'bg-red-900/20', ring: 'ring-red-900/40' },
  ranging: { color: 'text-amber-400', bg: 'bg-amber-400/10', ring: 'ring-amber-400/30' },
};

export function getTeamGradient(name: string): string {
  const key = name.toLowerCase().replace(/[\s_]+/g, '-');
  return TEAM_COLORS[key] || 'from-amber-500 to-orange-500';
}

export function getAgentGradient(agentClass: string | null, teamName: string | null): string {
  if (agentClass && AGENT_COLORS[agentClass]) return AGENT_COLORS[agentClass];
  if (teamName) return getTeamGradient(teamName);
  return 'from-amber-500 to-orange-500';
}

export function getAgentInitial(agentClass: string | null, role: string): string {
  const name = agentClass || role;
  const caps = name.replace(/Agent$/, '').match(/[A-Z]/g);
  if (caps && caps.length >= 2) return caps.slice(0, 2).join('');
  return name.slice(0, 2).toUpperCase();
}
