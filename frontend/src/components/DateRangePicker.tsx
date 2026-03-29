'use client';

import { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';

// ── Types ──

interface DateRange {
  start: string; // YYYY-MM-DD
  end: string;
}

interface Preset {
  label: string;
  getValue: () => DateRange;
}

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (range: DateRange) => void;
  presets?: Preset[];
}

// ── Default presets ──

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function ytdStart(): string {
  return `${new Date().getFullYear()}-01-01`;
}

const defaultPresets: Preset[] = [
  { label: 'Today', getValue: () => ({ start: today(), end: today() }) },
  { label: '7d', getValue: () => ({ start: daysAgo(7), end: today() }) },
  { label: '30d', getValue: () => ({ start: daysAgo(30), end: today() }) },
  { label: '90d', getValue: () => ({ start: daysAgo(90), end: today() }) },
  { label: 'YTD', getValue: () => ({ start: ytdStart(), end: today() }) },
  { label: 'All Time', getValue: () => ({ start: '2020-01-01', end: today() }) },
];

// ── Component ──

export default function DateRangePicker({
  startDate,
  endDate,
  onChange,
  presets = defaultPresets,
}: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Detect active preset
  useEffect(() => {
    const match = presets.find((p) => {
      const val = p.getValue();
      return val.start === startDate && val.end === endDate;
    });
    setActivePreset(match?.label ?? null);
  }, [startDate, endDate, presets]);

  // Close on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const displayLabel = activePreset || `${startDate} — ${endDate}`;

  return (
    <div ref={wrapperRef} className="relative inline-block">
      {/* Trigger */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 bg-syn-elevated border border-syn-border rounded-lg px-3 py-1.5 text-xs text-syn-text hover:border-syn-accent/40 transition-colors"
      >
        <Calendar size={12} className="text-syn-muted" />
        <span className="font-mono tabular-nums">{displayLabel}</span>
        <ChevronDown size={12} className={`text-syn-muted transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 bg-syn-surface border border-syn-border rounded-xl shadow-2xl p-3 min-w-[280px] drp-in">
          {/* Presets */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {presets.map((preset) => (
              <button
                key={preset.label}
                onClick={() => {
                  const val = preset.getValue();
                  onChange(val);
                  setOpen(false);
                }}
                className={`text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-md transition-colors ${
                  activePreset === preset.label
                    ? 'bg-syn-accent/15 text-syn-accent border border-syn-accent/20'
                    : 'text-syn-muted hover:text-syn-text hover:bg-white/[0.04] border border-transparent'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

          {/* Divider */}
          <div className="border-t border-syn-border mb-3" />

          {/* Custom range */}
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <label className="block text-[10px] font-bold uppercase tracking-widest text-syn-muted mb-1">From</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => onChange({ start: e.target.value, end: endDate })}
                className="w-full bg-syn-elevated text-xs text-syn-text rounded-md px-2 py-1.5 border border-syn-border outline-none focus:border-syn-accent transition-colors font-mono"
              />
            </div>
            <span className="text-syn-muted mt-4">—</span>
            <div className="flex-1">
              <label className="block text-[10px] font-bold uppercase tracking-widest text-syn-muted mb-1">To</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => onChange({ start: startDate, end: e.target.value })}
                className="w-full bg-syn-elevated text-xs text-syn-text rounded-md px-2 py-1.5 border border-syn-border outline-none focus:border-syn-accent transition-colors font-mono"
              />
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes drp-enter {
          from { opacity: 0; transform: translateY(-4px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .drp-in { animation: drp-enter 0.15s ease-out; }
      `}</style>
    </div>
  );
}
