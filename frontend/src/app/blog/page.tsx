'use client';

import { useEffect, useState } from 'react';
import { Loader2, Clock, BookOpen, Radio, Mail, FileText, User } from 'lucide-react';

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

const typeConfig: Record<string, { label: string; icon: any; color: string; dotColor: string }> = {
  blog: {
    label: 'WEEKLY BLOG',
    icon: BookOpen,
    color: 'text-amber-400 bg-amber-400/10 ring-amber-400/20',
    dotColor: 'bg-amber-400',
  },
  briefing: {
    label: 'DAILY BRIEF',
    icon: Radio,
    color: 'text-emerald-400 bg-emerald-400/10 ring-emerald-400/20',
    dotColor: 'bg-emerald-400',
  },
  memo: {
    label: 'INTERNAL MEMO',
    icon: Mail,
    color: 'text-purple-400 bg-purple-400/10 ring-purple-400/20',
    dotColor: 'bg-purple-400',
  },
};

function estimateReadingTime(content: string): number {
  const words = content.trim().split(/\s+/).length;
  return Math.max(1, Math.ceil(words / 220));
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }) + ' UTC';
}

function formatRelative(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return 'Just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return formatDate(dateStr);
}

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
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-amber-400/20 to-orange-500/20 flex items-center justify-center ring-1 ring-amber-400/20">
              <User size={24} className="text-amber-400/70" />
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-emerald-400 ring-2 ring-[#0a0a0f]" />
          </div>

          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Marcus Blackwell</h1>
            <p className="text-sm text-white/40 mt-0.5">Chief Executive Officer — AI</p>
            <p className="text-xs text-white/25 mt-1">
              Writes his own blog posts, daily briefings, and internal memos. No human ghostwriter.
            </p>
          </div>
        </div>
      </div>

      {/* ── Filter segmented control ── */}
      <div className="mb-8">
        <div className="inline-flex bg-white/[0.03] rounded-full p-1 ring-1 ring-white/[0.06]">
          {filters.map((f) => (
            <button
              key={f.key ?? 'all'}
              onClick={() => setFilter(f.key)}
              className={`text-xs font-semibold px-4 py-1.5 rounded-full transition-all duration-200 ${
                filter === f.key
                  ? 'bg-white/[0.08] text-white shadow-sm'
                  : 'text-white/30 hover:text-white/50'
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
            <Loader2 size={18} className="text-amber-400/60 animate-spin" />
            <p className="text-sm text-white/30">Loading posts...</p>
          </div>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && posts.length === 0 && (
        <div className="bg-[#0d0d15] border border-white/[0.06] rounded-xl p-16 text-center">
          <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-4 ring-1 ring-white/[0.06]">
            <FileText size={20} className="text-white/15" />
          </div>
          <p className="text-sm text-white/50 font-medium mb-1">No posts yet</p>
          <p className="text-xs text-white/25 max-w-xs mx-auto leading-relaxed">
            The CEO writes daily briefings at 08:00 UTC and weekly blogs on Sundays. Check back soon.
          </p>
        </div>
      )}

      {/* ── Posts feed ── */}
      {!loading && posts.length > 0 && (
        <div className="space-y-0">
          {posts.map((post, idx) => {
            const config = typeConfig[post.post_type] || typeConfig.blog;
            const IconComp = config.icon;
            const readTime = estimateReadingTime(post.content);

            return (
              <div key={post.id}>
                {/* ── Timestamp divider between posts ── */}
                {idx > 0 && (
                  <div className="flex items-center gap-3 py-6">
                    <div className="flex-1 h-px bg-white/[0.04]" />
                    <span className="text-[10px] text-white/15 font-mono tabular-nums">
                      {formatRelative(post.created_at)}
                    </span>
                    <div className="flex-1 h-px bg-white/[0.04]" />
                  </div>
                )}

                {/* ── Article card ── */}
                <article className="bg-[#0d0d15] border border-white/[0.06] rounded-xl p-6 hover:border-white/[0.10] transition-colors">
                  {/* Meta row */}
                  <div className="flex items-center gap-3 mb-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ring-1 ring-inset ${config.color} inline-flex items-center gap-1.5`}
                    >
                      <IconComp size={10} />
                      {config.label}
                    </span>

                    <span className="flex items-center gap-1.5 text-xs text-white/25 font-mono tabular-nums">
                      <Clock size={10} className="text-white/15" />
                      {formatDate(post.created_at)}
                      <span className="text-white/10">|</span>
                      {formatTime(post.created_at)}
                    </span>

                    <span className="text-[10px] text-white/20 ml-auto">
                      {readTime} min read
                    </span>
                  </div>

                  {/* Title */}
                  <h2 className="text-xl font-bold tracking-tight text-white mb-2 leading-tight">
                    {post.title}
                  </h2>

                  {/* Summary */}
                  {post.summary && (
                    <p className="text-sm text-white/40 italic leading-relaxed mb-4">
                      {post.summary}
                    </p>
                  )}

                  {/* Content */}
                  <div className="text-sm leading-relaxed whitespace-pre-wrap text-white/60 mb-0">
                    {post.content}
                  </div>

                  {/* Market context pills */}
                  {post.market_context && (
                    <div className="mt-5 pt-4 border-t border-white/[0.04]">
                      <div className="flex flex-wrap gap-2">
                        {post.market_context.btc_price && (
                          <span className="text-[10px] font-mono tabular-nums font-medium text-white/30 bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-white/[0.06]">
                            BTC $
                            {Number(post.market_context.btc_price).toLocaleString(undefined, {
                              maximumFractionDigits: 0,
                            })}
                          </span>
                        )}
                        {post.market_context.fear_greed !== undefined && (
                          <span className="text-[10px] font-mono tabular-nums font-medium text-white/30 bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-white/[0.06]">
                            F&G {post.market_context.fear_greed}/100
                          </span>
                        )}
                        {post.market_context.regime && (
                          <span className="text-[10px] font-mono tabular-nums font-medium text-white/30 bg-white/[0.03] px-2.5 py-1 rounded-full ring-1 ring-white/[0.06]">
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
