'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { Menu, X, OctagonX, Search } from 'lucide-react';
import MarketSwitcher from './MarketSwitcher';
import CommandPalette from './CommandPalette';
import { AlertsBell } from './AlertsPanel';

export default function ClientNav() {
  const pathname = usePathname();
  const isStocks = pathname.startsWith('/stocks');
  const prefix = isStocks ? '/stocks' : '';
  const [mobileOpen, setMobileOpen] = useState(false);

  const accentHover = isStocks ? 'hover:text-blue-400' : 'hover:text-syn-text';
  const activeColor = isStocks ? 'text-blue-400' : 'text-syn-text';

  function isActive(path: string) {
    if (path === '/dashboard') return pathname === '/dashboard' || pathname === '/';
    if (path === '/stocks') return pathname === '/stocks';
    return pathname.startsWith(path);
  }

  const linkClass = (path: string) =>
    `text-sm transition-colors ${isActive(path) ? activeColor : `text-syn-text-secondary ${accentHover}`}`;

  const links = [
    { href: isStocks ? '/stocks' : '/dashboard', label: 'Dashboard' },
    { href: `${prefix}/teams`, label: 'Teams' },
    { href: `${prefix}/org`, label: 'Org' },
    ...(isStocks ? [
      { href: '/stocks/pnl', label: 'P&L' },
      { href: '/stocks/risk', label: 'Risk' },
      { href: '/stocks/journal', label: 'Journal' },
    ] : [
      { href: '/activity', label: 'Activity' },
      { href: '/comms', label: 'Comms' },
      { href: '/agents', label: 'Agents' },
      { href: '/cycles', label: 'Cycles' },
    ]),
    { href: `${prefix}/results`, label: 'Results' },
    { href: `${prefix}/compliance`, label: 'Compliance' },
    { href: '/blog', label: 'Blog' },
    { href: '/research', label: 'Research' },
    ...(isStocks ? [] : [
      { href: '/intelligence', label: 'Intel' },
      { href: '/polymarket', label: 'Polymarket' },
    ]),
  ];

  return (
    <nav className="border-b border-syn-border bg-syn-bg/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-4">
            <a href={isStocks ? '/stocks' : '/'} className="flex items-center gap-2">
              <img src="/hydra-icon.png" alt="Syndicate" className="h-9 w-9 object-contain" />
              <span className="text-xl font-bold text-white tracking-tight">SYNDICATE</span>
              <span className="text-sm font-medium text-syn-muted">.ai</span>
            </a>
            <div className="h-6 w-px bg-syn-border/50 mx-1 hidden md:block" />
            <div className="hidden md:block">
              <MarketSwitcher />
            </div>
          </div>

          {/* Desktop links */}
          <div className="hidden lg:flex items-center gap-5">
            {links.map((link) => (
              <a key={link.href} href={link.href} className={linkClass(link.href)}>
                {link.label}
              </a>
            ))}
            {/* Cmd+K search hint */}
            <button
              onClick={() => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true })); }}
              className="hidden xl:flex items-center gap-1.5 text-[10px] text-syn-muted hover:text-syn-text-secondary bg-syn-elevated px-2.5 py-1 rounded-lg border border-syn-border transition-colors"
              title="Search (Cmd+K)"
            >
              <Search size={11} />
              <span>Search</span>
              <kbd className="font-mono text-[9px] text-syn-text-tertiary ml-1">&#8984;K</kbd>
            </button>

            {/* Alerts bell */}
            <AlertsBell />

            <button
              onClick={() => { if (confirm('HALT ALL TRADING?\n\nThis will cancel all pending orders and prevent new trades until manually resumed.')) { alert('Trading halted. (Connect to API: POST /api/v1/trading/halt)'); } }}
              className="text-[10px] font-bold bg-red-600/80 hover:bg-red-500 text-white px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
              title="Emergency: halt all trading activity"
            >
              <OctagonX size={12} /> HALT
            </button>
            <a href="/register" className="text-sm bg-syn-accent text-white px-4 py-1.5 rounded-lg font-medium hover:bg-syn-accent-hover transition-colors">
              Contribute
            </a>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="lg:hidden p-2 rounded-lg hover:bg-syn-surface transition-colors"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="lg:hidden border-t border-syn-border bg-syn-bg px-4 py-4 space-y-1">
          <div className="mb-3">
            <MarketSwitcher />
          </div>
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive(link.href) ? `${activeColor} bg-white/[0.04]` : `text-syn-text-secondary ${accentHover}`
              }`}
            >
              {link.label}
            </a>
          ))}
          <a
            href="/register"
            onClick={() => setMobileOpen(false)}
            className="block text-sm bg-syn-accent text-white px-4 py-2 rounded-lg font-medium text-center hover:bg-syn-accent-hover transition-colors mt-2"
          >
            Contribute
          </a>
        </div>
      )}

      {/* Global command palette */}
      <CommandPalette />
    </nav>
  );
}
