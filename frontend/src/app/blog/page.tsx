'use client';

import { useEffect, useState } from 'react';
import { Clock, FileText, Mail, Radio, Newspaper } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CeoPost {
  id: string;
  post_type: string;
  title: string;
  content: string;
  summary: string | null;
  market_context: Record<string, any> | null;
  created_at: string;
}

const typeConfig: Record<string, { label: string; icon: any; color: string }> = {
  blog: { label: 'WEEKLY BLOG', icon: FileText, color: 'text-amber-400 bg-amber-400/10 ring-amber-400/20' },
  memo: { label: 'INTERNAL MEMO', icon: Mail, color: 'text-purple-400 bg-purple-400/10 ring-purple-400/20' },
  briefing: { label: 'DAILY BRIEF', icon: Radio, color: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20' },
};

export default function BlogPage() {
  const [posts, setPosts] = useState<CeoPost[]>([]);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const url = filter
      ? `${API_BASE}/api/v1/ceo/posts?limit=30&post_type=${filter}`
      : `${API_BASE}/api/v1/ceo/posts?limit=30`;
    fetch(url)
      .then(r => r.json())
      .then(setPosts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
          <p className="text-sm text-white/30">Loading posts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto slide-up">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2.5 mb-3">
          <Newspaper size={18} className="text-amber-400/60" />
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">CEO Communications</p>
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Marcus Blackwell</h1>
        <p className="text-sm text-white/40 mt-1">Blogs, briefings, and internal memos</p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { key: null, label: 'All' },
          { key: 'blog', label: 'Blogs' },
          { key: 'briefing', label: 'Briefings' },
          { key: 'memo', label: 'Memos' },
        ].map((f) => (
          <button
            key={f.key ?? 'all'}
            onClick={() => { setFilter(f.key); setLoading(true); }}
            className={`text-xs font-semibold px-3.5 py-1.5 rounded-full transition-colors ${
              filter === f.key
                ? 'bg-white/10 text-white'
                : 'text-white/30 hover:text-white/50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Posts */}
      {posts.length === 0 ? (
        <div className="glass-card p-16 text-center">
          <FileText size={28} className="mx-auto text-white/10 mb-3" />
          <p className="text-sm text-white/40">No posts yet</p>
          <p className="text-xs text-white/20 mt-1">The CEO writes daily briefings at 08:00 UTC and weekly blogs on Sundays.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => {
            const config = typeConfig[post.post_type] || typeConfig.blog;
            return (
              <article key={post.id} className="glass-card p-6">
                <div className="flex items-center gap-3 mb-3">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${config.color}`}>
                    {config.label}
                  </span>
                  <span className="flex items-center gap-1.5 text-xs text-white/30">
                    <Clock size={11} className="text-white/20" />
                    {new Date(post.created_at).toLocaleDateString('en-US', {
                      weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
                </div>
                <h2 className="text-lg font-bold tracking-tight mb-2">{post.title}</h2>
                {post.summary && (
                  <p className="text-sm text-white/40 mb-3 italic leading-relaxed">{post.summary}</p>
                )}
                <div className="text-sm leading-relaxed whitespace-pre-wrap text-white/70">{post.content}</div>
                {post.market_context && (
                  <div className="mt-4 pt-3 border-t border-white/[0.06] flex flex-wrap gap-4 text-[10px] text-white/20">
                    {post.market_context.btc_price && (
                      <span>BTC ${Number(post.market_context.btc_price).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    )}
                    {post.market_context.fear_greed && (
                      <span>F&G {post.market_context.fear_greed}</span>
                    )}
                    {post.market_context.regime && (
                      <span>Regime: {post.market_context.regime.toUpperCase()}</span>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
