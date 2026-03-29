'use client';

import { useState, useEffect, useCallback } from 'react';
import { Plus, X, ArrowUpDown, Eye, TrendingUp, TrendingDown, Minus } from 'lucide-react';

// ── Types ──

interface WatchlistItem {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  sparkline: number[];
}

// ── Demo price data ──

const demoData: Record<string, Omit<WatchlistItem, 'symbol'>> = {
  AAPL:  { name: 'Apple',     price: 178.50, change: 2.30,  changePct: 1.31,  sparkline: [172, 174, 173, 175, 176, 175, 177, 178] },
  NVDA:  { name: 'NVIDIA',    price: 912.50, change: 18.40, changePct: 2.06,  sparkline: [880, 885, 890, 895, 892, 900, 908, 912] },
  META:  { name: 'Meta',      price: 518.20, change: -3.80, changePct: -0.73, sparkline: [525, 522, 520, 518, 519, 517, 516, 518] },
  MSFT:  { name: 'Microsoft', price: 425.30, change: 5.10,  changePct: 1.21,  sparkline: [415, 418, 420, 419, 422, 424, 423, 425] },
  AMZN:  { name: 'Amazon',    price: 185.20, change: -1.20, changePct: -0.64, sparkline: [188, 187, 186, 185, 186, 184, 185, 185] },
  GOOGL: { name: 'Alphabet',  price: 155.80, change: 1.60,  changePct: 1.04,  sparkline: [152, 153, 154, 153, 155, 154, 155, 156] },
  TSLA:  { name: 'Tesla',     price: 248.90, change: -5.40, changePct: -2.12, sparkline: [260, 258, 255, 252, 250, 249, 248, 249] },
  AMD:   { name: 'AMD',       price: 165.40, change: 3.20,  changePct: 1.97,  sparkline: [158, 160, 161, 162, 163, 164, 165, 165] },
  JPM:   { name: 'JPMorgan',  price: 205.40, change: 1.80,  changePct: 0.88,  sparkline: [200, 201, 202, 203, 204, 204, 205, 205] },
  BTC:   { name: 'Bitcoin',   price: 68420,  change: 1250,  changePct: 1.86,  sparkline: [65000, 66000, 66500, 67000, 67500, 68000, 68200, 68400] },
  ETH:   { name: 'Ethereum',  price: 3580,   change: -45,   changePct: -1.24, sparkline: [3650, 3630, 3610, 3600, 3590, 3585, 3580, 3580] },
  SOL:   { name: 'Solana',    price: 142.50, change: 4.80,  changePct: 3.49,  sparkline: [132, 135, 137, 138, 140, 141, 142, 142] },
};

const allSymbols = Object.keys(demoData);
const defaultSymbols = ['NVDA', 'META', 'AAPL', 'MSFT', 'BTC'];

type SortKey = 'name' | 'price' | 'change';
type SortDir = 'asc' | 'desc';

// ── Sparkline SVG ──

function Sparkline({ data, positive }: { data: number[]; positive: boolean }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 60;
  const h = 20;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={w} height={h} className="shrink-0">
      <polyline
        points={points}
        fill="none"
        stroke={positive ? '#22c55e' : '#ef4444'}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ── Component ──

export default function Watchlist({ compact = false }: { compact?: boolean }) {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [addInput, setAddInput] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  // Load from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('syn-watchlist');
      if (stored) {
        setSymbols(JSON.parse(stored));
      } else {
        setSymbols(defaultSymbols);
      }
    } catch {
      setSymbols(defaultSymbols);
    }
  }, []);

  // Persist to localStorage
  useEffect(() => {
    if (symbols.length > 0) {
      localStorage.setItem('syn-watchlist', JSON.stringify(symbols));
    }
  }, [symbols]);

  const addSymbol = useCallback((sym: string) => {
    const upper = sym.toUpperCase().trim();
    if (upper && demoData[upper] && !symbols.includes(upper)) {
      setSymbols((prev) => [...prev, upper]);
    }
    setAddInput('');
    setShowAdd(false);
  }, [symbols]);

  const removeSymbol = useCallback((sym: string) => {
    setSymbols((prev) => prev.filter((s) => s !== sym));
  }, []);

  const toggleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }, [sortKey]);

  // Build sorted items
  const items: WatchlistItem[] = symbols
    .filter((s) => demoData[s])
    .map((s) => ({ symbol: s, ...demoData[s] }));

  items.sort((a, b) => {
    let cmp = 0;
    if (sortKey === 'name') cmp = a.symbol.localeCompare(b.symbol);
    else if (sortKey === 'price') cmp = a.price - b.price;
    else cmp = a.changePct - b.changePct;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const availableToAdd = allSymbols.filter(
    (s) => !symbols.includes(s) && (addInput === '' || s.toLowerCase().includes(addInput.toLowerCase()) || demoData[s].name.toLowerCase().includes(addInput.toLowerCase()))
  );

  return (
    <div className={`glass-card overflow-hidden ${compact ? '' : 'w-full'}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Eye size={14} className="text-blue-400" />
          <h3 className="text-sm font-semibold">Watchlist</h3>
          <span className="text-[10px] text-syn-muted">{items.length} symbols</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="p-1 rounded hover:bg-white/[0.06] transition-colors text-syn-muted hover:text-syn-text"
            title="Add symbol"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      {/* Add symbol dropdown */}
      {showAdd && (
        <div className="px-4 py-2 border-b border-white/[0.06] bg-white/[0.01]">
          <input
            autoFocus
            type="text"
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && availableToAdd.length > 0) addSymbol(availableToAdd[0]); if (e.key === 'Escape') setShowAdd(false); }}
            placeholder="Type ticker..."
            className="w-full bg-syn-elevated text-sm text-syn-text placeholder:text-syn-muted rounded px-3 py-1.5 outline-none border border-syn-border focus:border-syn-accent transition-colors"
          />
          {availableToAdd.length > 0 && (
            <div className="mt-1 max-h-28 overflow-y-auto space-y-0.5">
              {availableToAdd.slice(0, 6).map((sym) => (
                <button
                  key={sym}
                  onClick={() => addSymbol(sym)}
                  className="w-full text-left px-3 py-1.5 text-xs rounded hover:bg-white/[0.04] transition-colors flex items-center justify-between"
                >
                  <span className="font-semibold">{sym}</span>
                  <span className="text-syn-muted">{demoData[sym].name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Sort controls */}
      <div className="px-4 py-1.5 flex items-center gap-3 border-b border-white/[0.03] text-[10px] text-syn-muted">
        {(['name', 'price', 'change'] as SortKey[]).map((key) => (
          <button
            key={key}
            onClick={() => toggleSort(key)}
            className={`flex items-center gap-0.5 uppercase tracking-widest font-semibold transition-colors ${sortKey === key ? 'text-syn-text' : 'hover:text-syn-text-secondary'}`}
          >
            {key}
            {sortKey === key && (
              <ArrowUpDown size={8} className="opacity-60" />
            )}
          </button>
        ))}
      </div>

      {/* Watchlist items */}
      <div className="divide-y divide-white/[0.03]">
        {items.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-syn-muted">
            No symbols in watchlist. Click + to add.
          </div>
        ) : (
          items.map((item) => {
            const positive = item.changePct >= 0;
            return (
              <div
                key={item.symbol}
                className="px-4 py-2.5 flex items-center gap-3 hover:bg-white/[0.02] transition-colors group"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <a href={item.price > 1000 ? '/dashboard' : `/stocks/detail/${item.symbol}`} className="text-sm font-bold hover:text-blue-400 transition-colors">
                      {item.symbol}
                    </a>
                    {!compact && (
                      <span className="text-[10px] text-syn-muted truncate">{item.name}</span>
                    )}
                  </div>
                </div>

                {!compact && <Sparkline data={item.sparkline} positive={positive} />}

                <div className="text-right shrink-0">
                  <p className="text-sm font-mono tabular-nums">
                    {item.price >= 1000 ? `$${item.price.toLocaleString()}` : `$${item.price.toFixed(2)}`}
                  </p>
                  <p className={`text-[10px] font-semibold tabular-nums ${positive ? 'text-emerald-400' : 'text-red-400'}`}>
                    {positive ? '+' : ''}{item.changePct.toFixed(2)}%
                  </p>
                </div>

                <button
                  onClick={() => removeSymbol(item.symbol)}
                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-500/10 text-syn-muted hover:text-red-400 transition-all shrink-0"
                  title="Remove from watchlist"
                >
                  <X size={12} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
