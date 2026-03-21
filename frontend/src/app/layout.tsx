import { Inter, JetBrains_Mono } from 'next/font/google';
import ClientNav from '@/components/ClientNav';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' });

export const metadata = {
  title: 'Syndicate — AI Crypto Hedge Fund',
  description: 'Autonomous multi-agent crypto hedge fund. Zero humans.',
  icons: {
    icon: '/hydra-icon.png',
    apple: '/hydra-icon.png',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrains.variable} font-sans min-h-screen bg-syn-bg text-syn-text antialiased`}>
        <ClientNav />

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-syn-border py-8 px-6">
          <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center gap-3 sm:justify-between text-xs text-syn-text-tertiary">
            <span>Syndicate.ai — Autonomous AI Hedge Fund</span>
            <div className="flex flex-wrap gap-3 sm:gap-4">
              <a href="/how-it-works" className="hover:text-syn-text-secondary transition-colors">How It Works</a>
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
