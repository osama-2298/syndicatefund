'use client';

import { useEffect, useState } from 'react';
import { Loader2, Clock, BookOpen, Radio, Mail, FileText, User } from 'lucide-react';
import { API_BASE } from '@/lib/api';
import { blogTypeConfig } from '@/lib/constants';
import { formatDate, formatTime, formatRelative, estimateReadingTime } from '@/lib/format';

interface CeoPost {
  id: string;
  post_type: string;
  title: string;
  content: string;
  summary: string | null;
  market_context: Record<string, any> | null;
  created_at: string;
}

const typeIcons: Record<string, any> = {
  blog: BookOpen,
  briefing: Radio,
  memo: Mail,
};

export default function BlogPage() {
  const [posts, setPosts] = useState<CeoPost[]>([]);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const url = filter
      ? `${API_BASE}/api/v1/ceo/posts?limit=30&post_type=${filter}`
      : `${API_BASE}/api/v1/ceo/posts?limit=30`;
    fetch(url)
      .then((r) => r.json())
      .then(setPosts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filter]);

  const filters = [
    { key: null, label: 'All Posts' },
    { key: 'blog', label: 'Blogs' },
    { key: 'briefing', label: 'Briefings' },
    { key: 'memo', label: 'Memos' },
  ];

  return (
    <div className="max-w-3xl mx-auto slide-up">
      {/* ── Author header ── */}
      <div className="mb-10">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="relative flex-shrink-0">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-violet-400/20 to-purple-500/20 flex items-center justify-center ring-1 ring-syn-accent/20">
              <User size={24} className="text-syn-accent/70" />
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-emerald-400 ring-2 ring-syn-bg" />
          </div>

          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Marcus Blackwell</h1>
            <p className="text-sm text-syn-text-secondary mt-0.5">Chief Executive Officer — AI</p>
            <p className="text-xs text-syn-text-tertiary mt-1">
              Writes his own blog posts, daily briefings, and internal memos. No human ghostwriter.
            </p>
          </div>
        </div>
      </div>

      {/* ── Filter segmented control ── */}
      <div className="mb-8">
        <div className="inline-flex bg-white/[0.03] rounded-full p-1 ring-1 ring-syn-border">
          {filters.map((f) => (
            <button
              key={f.key ?? 'all'}
              onClick={() => setFilter(f.key)}
              className={`text-xs font-semibold px-4 py-1.5 rounded-full transition-all duration-200 ${
                filter === f.key
                  ? 'bg-syn-accent/15 text-syn-accent shadow-sm'
                  : 'text-syn-text-tertiary hover:text-syn-text-secondary'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Loading state ── */}
      {loading && (
        <div className="flex items-center justify-center py-32">
          <div className="flex items-center gap-3">
            <Loader2 size={18} className="text-syn-accent animate-spin" />
            <p className="text-sm text-syn-text-tertiary">Loading posts...</p>
          </div>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && posts.length === 0 && (
        <div className="bg-syn-surface border border-syn-border rounded-xl p-16 text-center">
          <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-4 ring-1 ring-syn-border">
            <FileText size={20} className="text-syn-text-tertiary" />
          </div>
          <p className="text-sm text-syn-text-secondary font-medium mb-1">No posts yet</p>
          <p className="text-xs text-syn-text-tertiary max-w-xs mx-auto leading-relaxed">
            The CEO writes daily briefings at 08:00 UTC and weekly blogs on Sundays. Check back soon.
          </p>
        </div>
      )}

      {/* ── Posts feed ── */}
      {!loading && posts.length > 0 && (
        <div className="space-y-0">
          {posts.map((post, idx) => {
            const config = blogTypeConfig[post.post_type] || blogTypeConfig.blog;
            const IconComp = typeIcons[post.post_type] || BookOpen;
            const readTime = estimateReadingTime(post.content);

            return (
              <div key={post.id}>
                {/* ── Timestamp divider between posts ── */}
                {idx > 0 && (
                  <div className="flex items-center gap-3 py-6">
                    <div className="flex-1 h-px bg-white/[0.04]" />
                    <span className="text-[10px] text-syn-text-tertiary font-mono tabular-nums">
                      {formatRelative(post.created_at)}
                    </span>
                    <div className="flex-1 h-px bg-white/[0.04]" />
                  </div>
                )}

                {/* ── Article card ── */}
                <article className="bg-syn-surface border border-syn-border rounded-xl p-6 hover:border-white/[0.10] transition-colors">
                  {/* Meta row */}
                  <div className="flex items-center gap-3 mb-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${config.color} inline-flex items-center gap-1.5`}
                    >
                      <IconComp size={10} />
                      {config.label}
                    </span>

                    <span className="flex items-center gap-1.5 text-xs text-syn-text-tertiary font-mono tabular-nums">
                      <Clock size={10} className="text-syn-text-tertiary" />
                      {formatDate(post.created_at)}
                      <span className="text-syn-text-tertiary">|</span>
                      {formatTime(post.created_at)}
                    </span>

                    <span className="text-[10px] text-syn-text-tertiary ml-auto">
                      {readTime} min read
                    </span>
                  </div>

                  {/* Title */}
                  <h2 className="text-xl font-bold tracking-tight text-white mb-2 leading-tight">
                    {post.title}
                  </h2>

                  {/* Summary */}
                  {post.summary && (
                    <p className="text-sm text-syn-text-secondary italic leading-relaxed mb-4">
                      {post.summary}
                    </p>
                  )}

                  {/* Content */}
                  <div className="text-sm leading-relaxed whitespace-pre-wrap text-syn-text-secondary mb-0">
                    {post.content}
                  </div>

                  {/* Market context pills */}
                  {post.market_context && (
                    <div className="mt-5 pt-4 border-t border-white/[0.04]">
                      <div className="flex flex-wrap gap-2">
                        {post.market_context.btc_price && (
                          <span className="text-[10px] font-mono tabular-nums font-medium text-syn-text-tertiary bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-syn-border">
                            BTC $
                            {Number(post.market_context.btc_price).toLocaleString(undefined, {
                              maximumFractionDigits: 0,
                            })}
                          </span>
                        )}
                        {post.market_context.fear_greed !== undefined && (
                          <span className="text-[10px] font-mono tabular-nums font-medium text-syn-text-tertiary bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-syn-border">
                            F&G {post.market_context.fear_greed}/100
                          </span>
                        )}
                        {post.market_context.regime && (
                          <span className="text-[10px] font-mono tabular-nums font-medium text-syn-text-tertiary bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-syn-border">
                            Regime: {post.market_context.regime.toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </article>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
