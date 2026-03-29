'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, TrendingUp, LayoutDashboard, Users, Bot, X } from 'lucide-react';

// ── Searchable Items ──

interface SearchItem {
  id: string;
  label: string;
  category: 'Stocks' | 'Crypto' | 'Pages' | 'Agents' | 'Teams';
  href: string;
  description?: string;
}

const searchItems: SearchItem[] = [
  // Stocks
  { id: 'aapl', label: 'AAPL', category: 'Stocks', href: '/stocks/detail/AAPL', description: 'Apple Inc.' },
  { id: 'nvda', label: 'NVDA', category: 'Stocks', href: '/stocks/detail/NVDA', description: 'NVIDIA Corp.' },
  { id: 'meta', label: 'META', category: 'Stocks', href: '/stocks/detail/META', description: 'Meta Platforms' },
  { id: 'msft', label: 'MSFT', category: 'Stocks', href: '/stocks/detail/MSFT', description: 'Microsoft Corp.' },
  { id: 'amzn', label: 'AMZN', category: 'Stocks', href: '/stocks/detail/AMZN', description: 'Amazon.com' },
  { id: 'googl', label: 'GOOGL', category: 'Stocks', href: '/stocks/detail/GOOGL', description: 'Alphabet Inc.' },
  { id: 'tsla', label: 'TSLA', category: 'Stocks', href: '/stocks/detail/TSLA', description: 'Tesla Inc.' },
  { id: 'jpm', label: 'JPM', category: 'Stocks', href: '/stocks/detail/JPM', description: 'JPMorgan Chase' },
  { id: 'amd', label: 'AMD', category: 'Stocks', href: '/stocks/detail/AMD', description: 'Advanced Micro Devices' },

  // Crypto
  { id: 'btc', label: 'BTC', category: 'Crypto', href: '/dashboard', description: 'Bitcoin' },
  { id: 'eth', label: 'ETH', category: 'Crypto', href: '/dashboard', description: 'Ethereum' },
  { id: 'sol', label: 'SOL', category: 'Crypto', href: '/dashboard', description: 'Solana' },
  { id: 'avax', label: 'AVAX', category: 'Crypto', href: '/dashboard', description: 'Avalanche' },

  // Pages
  { id: 'pg-dashboard', label: 'Dashboard', category: 'Pages', href: '/stocks', description: 'Stock dashboard overview' },
  { id: 'pg-crypto-dash', label: 'Crypto Dashboard', category: 'Pages', href: '/dashboard', description: 'Crypto dashboard overview' },
  { id: 'pg-teams', label: 'Teams', category: 'Pages', href: '/stocks/teams', description: 'Agent team performance' },
  { id: 'pg-org', label: 'Organization', category: 'Pages', href: '/stocks/org', description: 'AI organizational structure' },
  { id: 'pg-pnl', label: 'P&L', category: 'Pages', href: '/stocks/pnl', description: 'Profit & loss dashboard' },
  { id: 'pg-risk', label: 'Risk Monitor', category: 'Pages', href: '/stocks/risk', description: 'Real-time risk monitoring' },
  { id: 'pg-journal', label: 'Trade Journal', category: 'Pages', href: '/stocks/journal', description: 'Trade decision history' },
  { id: 'pg-results', label: 'Results', category: 'Pages', href: '/stocks/results', description: 'Performance results' },
  { id: 'pg-compliance', label: 'Compliance', category: 'Pages', href: '/stocks/compliance', description: 'Regulatory compliance' },
  { id: 'pg-blog', label: 'Blog', category: 'Pages', href: '/blog', description: 'Research blog' },
  { id: 'pg-research', label: 'Research', category: 'Pages', href: '/research', description: 'Research papers' },

  // Agents
  { id: 'agent-technical', label: 'Technical Analyst', category: 'Agents', href: '/stocks/teams', description: 'Chart patterns, indicators, price action' },
  { id: 'agent-fundamental', label: 'Fundamental Analyst', category: 'Agents', href: '/stocks/teams', description: 'Earnings, valuation, growth metrics' },
  { id: 'agent-sentiment', label: 'Sentiment Analyst', category: 'Agents', href: '/stocks/teams', description: 'Social media, options flow, fear/greed' },
  { id: 'agent-macro', label: 'Macro Analyst', category: 'Agents', href: '/stocks/teams', description: 'Rates, sectors, economic indicators' },
  { id: 'agent-institutional', label: 'Institutional Flow', category: 'Agents', href: '/stocks/teams', description: 'Dark pool, 13F filings, insider trades' },
  { id: 'agent-news', label: 'News Analyst', category: 'Agents', href: '/stocks/teams', description: 'Breaking news, catalysts, events' },
  { id: 'agent-risk', label: 'Risk Manager', category: 'Agents', href: '/stocks/risk', description: 'Position sizing, VaR, exposure limits' },

  // Teams
  { id: 'team-alpha', label: 'Alpha Generation', category: 'Teams', href: '/stocks/teams', description: 'Signal generation and scoring' },
  { id: 'team-execution', label: 'Execution', category: 'Teams', href: '/stocks/teams', description: 'Trade execution and routing' },
  { id: 'team-risk', label: 'Risk Management', category: 'Teams', href: '/stocks/teams', description: 'Portfolio risk and compliance' },
];

const categoryIcons: Record<string, React.ReactNode> = {
  Stocks: <TrendingUp size={12} />,
  Crypto: <TrendingUp size={12} />,
  Pages: <LayoutDashboard size={12} />,
  Agents: <Bot size={12} />,
  Teams: <Users size={12} />,
};

const categoryColors: Record<string, string> = {
  Stocks: 'text-blue-400',
  Crypto: 'text-syn-accent',
  Pages: 'text-emerald-400',
  Agents: 'text-cyan-400',
  Teams: 'text-amber-400',
};

function fuzzyMatch(query: string, text: string): boolean {
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (t.includes(q)) return true;
  let qi = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) qi++;
  }
  return qi === q.length;
}

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Cmd+K listener
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setOpen(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Filter results
  const filtered = query.length === 0
    ? searchItems.slice(0, 12)
    : searchItems.filter(
        (item) =>
          fuzzyMatch(query, item.label) ||
          fuzzyMatch(query, item.description || '') ||
          fuzzyMatch(query, item.category)
      );

  // Group by category
  const grouped: Record<string, SearchItem[]> = {};
  filtered.forEach((item) => {
    if (!grouped[item.category]) grouped[item.category] = [];
    grouped[item.category].push(item);
  });

  // Flat list for keyboard nav
  const flatList = Object.values(grouped).flat();

  const navigate = useCallback((href: string) => {
    setOpen(false);
    window.location.href = href;
  }, []);

  // Keyboard navigation
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, flatList.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && flatList[selectedIndex]) {
      e.preventDefault();
      navigate(flatList[selectedIndex].href);
    }
  }

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  if (!open) return null;

  let flatIndex = -1;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={() => setOpen(false)}
      />

      {/* Modal */}
      <div className="relative w-full max-w-xl mx-4 bg-syn-surface border border-syn-border rounded-xl shadow-2xl overflow-hidden animate-scale-in">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-syn-border">
          <Search size={16} className="text-syn-muted shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Search tickers, pages, agents, teams..."
            className="flex-1 bg-transparent text-sm text-syn-text placeholder:text-syn-muted outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 text-[10px] text-syn-muted bg-syn-elevated px-2 py-0.5 rounded border border-syn-border font-mono">
            ESC
          </kbd>
          <button onClick={() => setOpen(false)} className="sm:hidden text-syn-muted hover:text-syn-text">
            <X size={16} />
          </button>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-80 overflow-y-auto py-2">
          {flatList.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-syn-muted">
              No results for &ldquo;{query}&rdquo;
            </div>
          ) : (
            Object.entries(grouped).map(([category, items]) => (
              <div key={category}>
                <div className="px-4 py-1.5 flex items-center gap-2">
                  <span className={categoryColors[category]}>{categoryIcons[category]}</span>
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-syn-muted">
                    {category}
                  </span>
                </div>
                {items.map((item) => {
                  flatIndex++;
                  const idx = flatIndex;
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={item.id}
                      data-index={idx}
                      onClick={() => navigate(item.href)}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`w-full text-left px-4 py-2 flex items-center gap-3 transition-colors ${
                        isSelected ? 'bg-syn-accent/10' : 'hover:bg-white/[0.02]'
                      }`}
                    >
                      <span className="text-sm font-semibold min-w-[60px]">{item.label}</span>
                      <span className="text-xs text-syn-muted truncate">{item.description}</span>
                      {isSelected && (
                        <span className="ml-auto text-[10px] text-syn-muted font-mono shrink-0">Enter &crarr;</span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-syn-border text-[10px] text-syn-muted">
          <span><kbd className="font-mono">&#8593;&#8595;</kbd> navigate</span>
          <span><kbd className="font-mono">Enter</kbd> select</span>
          <span><kbd className="font-mono">Esc</kbd> close</span>
        </div>
      </div>

      <style jsx>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scale-in {
          from { opacity: 0; transform: scale(0.96) translateY(-8px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
        .animate-fade-in { animation: fade-in 0.15s ease-out; }
        .animate-scale-in { animation: scale-in 0.2s ease-out; }
      `}</style>
    </div>
  );
}
