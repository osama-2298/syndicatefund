import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Syndicate — AI Crypto Hedge Fund',
  description: 'Scalable multi-agent crypto analysis platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-hive-bg text-hive-text antialiased">
        <nav className="border-b border-hive-border bg-hive-card/50 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <a href="/" className="flex items-center gap-2">
                <span className="text-2xl font-bold text-gradient">SYNDICATE</span>
                <span className="text-xs text-hive-muted bg-hive-border px-2 py-0.5 rounded">.AI</span>
              </a>
              <div className="flex items-center gap-6">
                <a href="/dashboard" className="text-sm text-hive-muted hover:text-hive-text transition-colors">Dashboard</a>
                <a href="/activity" className="text-sm text-hive-muted hover:text-hive-text transition-colors">Activity</a>
                <a href="/agents" className="text-sm text-hive-muted hover:text-hive-text transition-colors">Agents</a>
                <a href="/org" className="text-sm text-hive-muted hover:text-hive-text transition-colors">Org</a>
                <a href="/blog" className="text-sm text-hive-muted hover:text-hive-text transition-colors">Blog</a>
                <a href="/research" className="text-sm text-hive-muted hover:text-hive-text transition-colors">Research</a>
                <a href="/results" className="text-sm text-hive-muted hover:text-hive-text transition-colors">Results</a>
                <a href="/register" className="text-sm bg-hive-accent text-black px-4 py-1.5 rounded-lg font-medium hover:bg-amber-400 transition-colors">
                  Contribute
                </a>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
