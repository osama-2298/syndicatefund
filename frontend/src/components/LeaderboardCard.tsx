'use client';

import { useEffect, useState } from 'react';
import { Trophy, Flame, Snowflake, ArrowRight } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface LeaderboardEntry {
  agent_id: string;
  role: string;
  agent_class: string | null;
  team_name: string | null;
  accuracy: number;
  total_signals: number;
  streak_count: number;
  streak_type: string;
}

const AGENT_NAMES: Record<string, string> = {
  TechnicalTrendAgent: 'Aria Chen',
  TechnicalSignalAgent: 'Leo Tanaka',
  TechnicalTimingAgent: 'Priya Sharma',
  SocialSentimentAgent: 'Dante Morales',
  MarketSentimentAgent: 'Zara Obi',
  SmartMoneySentimentAgent: 'Felix Strand',
  ValuationAgent: 'Mina Petrova',
  CyclePositionAgent: 'Ravi Anand',
  CryptoMacroAgent: 'Ingrid Holm',
  ExternalMacroAgent: 'Tariq Nasseri',
  NetworkHealthAgent: 'Yuki Sato',
  CapitalFlowAgent: 'Emeka Osei',
};

const MEDALS = ['text-amber-400', 'text-gray-300', 'text-amber-700'];

export default function LeaderboardCard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/leaderboard`)
      .then(r => r.json())
      .then(data => setEntries(Array.isArray(data) ? data.slice(0, 5) : []))
      .catch(() => {});
  }, []);

  if (entries.length === 0) {
    return (
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center gap-2">
          <Trophy size={14} className="text-hive-accent" />
          <h2 className="text-sm font-semibold">Top Agents</h2>
        </div>
        <div className="px-5 py-6 text-center">
          <p className="text-xs text-hive-muted">Rankings appear after agents produce 5+ signals.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Trophy size={14} className="text-hive-accent" />
          <h2 className="text-sm font-semibold">Top Agents</h2>
        </div>
        <a href="/results" className="text-xs text-hive-accent hover:text-amber-300 transition-colors flex items-center gap-1">
          Full rankings <ArrowRight size={12} />
        </a>
      </div>
      <div className="divide-y divide-white/[0.03]">
        {entries.map((entry, i) => {
          const name = AGENT_NAMES[entry.agent_class || ''] || entry.role;
          const accuracyPct = entry.accuracy * 100;
          return (
            <div key={entry.agent_id} className="px-5 py-3 hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold w-5 text-center ${MEDALS[i] || 'text-hive-muted'}`}>
                    {i + 1}
                  </span>
                  <a href={`/agents/${entry.agent_id}`} className="text-sm font-semibold hover:text-hive-accent transition-colors">
                    {name}
                  </a>
                  {entry.team_name && (
                    <span className="text-[10px] text-hive-muted capitalize">{entry.team_name}</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {entry.streak_count >= 3 && (
                    <span className="flex items-center gap-0.5">
                      {entry.streak_type === 'win' ? (
                        <Flame size={12} className="text-amber-400" />
                      ) : (
                        <Snowflake size={12} className="text-blue-400" />
                      )}
                      <span className="text-[10px] font-bold">{entry.streak_count}</span>
                    </span>
                  )}
                  <span className={`text-sm font-bold ${accuracyPct >= 60 ? 'text-emerald-400' : accuracyPct >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
                    {accuracyPct.toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-7">
                <div className="flex-1 h-1 bg-white/[0.04] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${accuracyPct >= 60 ? 'bg-emerald-500' : accuracyPct >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(100, accuracyPct)}%` }}
                  />
                </div>
                <span className="text-[10px] text-hive-muted shrink-0">{entry.total_signals} signals</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
