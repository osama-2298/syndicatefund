'use client';

import { useState } from 'react';
import { Menu, X } from 'lucide-react';

const navLinks = [
  { href: '/how-it-works', label: 'How It Works' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/activity', label: 'Activity' },
  { href: '/comms', label: 'Comms' },
  { href: '/agents', label: 'Agents' },
  { href: '/org', label: 'Org' },
  { href: '/blog', label: 'Blog' },
  { href: '/results', label: 'Results' },
  { href: '/research', label: 'Research' },
  { href: '/intelligence', label: 'Intel' },
  { href: '/polymarket', label: 'Polymarket' },
];

export default function ClientNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="border-b border-syn-border bg-syn-bg/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2">
            <img src="/hydra-icon.png" alt="Syndicate" className="h-9 w-9 object-contain" />
            <span className="text-xl font-bold text-white tracking-tight">SYNDICATE</span>
            <span className="text-sm font-medium text-syn-muted">.ai</span>
          </a>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <a key={link.href} href={link.href} className="text-sm text-syn-text-secondary hover:text-syn-text transition-colors">
                {link.label}
              </a>
            ))}
            <a href="/register" className="text-sm bg-syn-accent text-white px-4 py-1.5 rounded-lg font-medium hover:bg-syn-accent-hover transition-colors">
              Contribute
            </a>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-syn-surface transition-colors"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-syn-border bg-syn-bg px-4 py-4 space-y-2">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="block text-sm text-syn-text-secondary hover:text-syn-text py-2 transition-colors"
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
    </nav>
  );
}
