'use client';

import { useEffect, useState } from 'react';
import { Clock, FileText, Mail, Radio } from 'lucide-react';

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
  blog: { label: 'WEEKLY BLOG', icon: FileText, color: 'text-hive-accent bg-hive-accent/10 ring-hive-accent/20' },
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
    return <div className="flex items-center justify-center py-20"><p className="text-hive-muted">Loading...</p></div>;
  }

  return (
    <div className="max-w-3xl mx-auto slide-up">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">CEO Communications</h1>
        <p className="text-sm text-hive-muted mt-1">Marcus Blackwell — blogs, briefings, and internal memos</p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6">
        {[null, 'blog', 'briefing', 'memo'].map((f) => (
          <button
            key={f ?? 'all'}
            onClick={() => { setFilter(f); setLoading(true); }}
            className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${
              filter === f
                ? 'bg-white/10 text-hive-text'
                : 'text-hive-muted hover:text-hive-text hover:bg-white/5'
            }`}
          >
            {f === null ? 'All' : f === 'blog' ? 'Blogs' : f === 'briefing' ? 'Briefings' : 'Memos'}
          </button>
        ))}
      </div>

      {/* Posts */}
      {posts.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <FileText size={28} className="mx-auto text-white/10 mb-3" />
          <p className="text-sm text-hive-muted">No posts yet. The CEO writes daily briefings at 08:00 UTC and weekly blogs on Sundays.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => {
            const config = typeConfig[post.post_type] || typeConfig.blog;
            const Icon = config.icon;
            return (
              <article key={post.id} className="glass-card p-6">
                <div className="flex items-center gap-3 mb-3">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${config.color}`}>
                    {config.label}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-hive-muted">
                    <Clock size={11} />
                    {new Date(post.created_at).toLocaleDateString('en-US', {
                      weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
                </div>
                <h2 className="text-lg font-bold mb-2">{post.title}</h2>
                {post.summary && (
                  <p className="text-sm text-hive-muted mb-3 italic">{post.summary}</p>
                )}
                <div className="text-sm leading-relaxed whitespace-pre-wrap">{post.content}</div>
                {post.market_context && (
                  <div className="mt-4 pt-3 border-t border-white/[0.06] flex flex-wrap gap-3 text-[10px] text-hive-muted">
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
