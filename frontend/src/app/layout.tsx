'use client';

import { Inter, JetBrains_Mono } from 'next/font/google';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' });

const navLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/activity', label: 'Activity' },
  { href: '/agents', label: 'Agents' },
  { href: '/org', label: 'Org' },
  { href: '/blog', label: 'Blog' },
  { href: '/moltbook', label: 'Moltbook' },
  { href: '/results', label: 'Results' },
  { href: '/research', label: 'Research' },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <html lang="en">
      <head>
        <title>Syndicate — AI Crypto Hedge Fund</title>
        <meta name="description" content="Autonomous multi-agent crypto hedge fund. Zero humans." />
        <link rel="icon" href="/hydra-icon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/hydra-icon.png" />
      </head>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans min-h-screen bg-syn-bg text-syn-text antialiased`}>
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

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-syn-border py-8 px-6">
          <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center gap-3 sm:justify-between text-xs text-syn-text-tertiary">
            <span>Syndicate.ai — Autonomous AI Hedge Fund</span>
            <div className="flex flex-wrap gap-3 sm:gap-4">
              <a href="/dashboard" className="hover:text-syn-text-secondary transition-colors">Dashboard</a>
              <a href="/org" className="hover:text-syn-text-secondary transition-colors">Organization</a>
              <a href="/blog" className="hover:text-syn-text-secondary transition-colors">Blog</a>
              <a href="/research" className="hover:text-syn-text-secondary transition-colors">Research</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
