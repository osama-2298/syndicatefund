'use client';

import { useState } from 'react';
import { UserPlus, Shield, Check, AlertCircle, ChevronRight, Lock } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function RegisterPage() {
  const [form, setForm] = useState({
    display_name: '',
    email: '',
    provider: 'anthropic',
    api_key: '',
    max_agents: 2,
    preferred_model: 'claude-sonnet-4-6',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const models: Record<string, string[]> = {
    anthropic: ['claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
    openai: ['gpt-4o', 'gpt-4o-mini'],
    google: ['gemini-2.0-flash'],
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    const body: any = {
      display_name: form.display_name,
      email: form.email || undefined,
      max_agents: form.max_agents,
      preferred_model: form.preferred_model,
    };

    if (form.provider === 'anthropic') body.api_key_anthropic = form.api_key;
    else if (form.provider === 'openai') body.api_key_openai = form.api_key;
    else body.api_key_google = form.api_key;

    try {
      const res = await fetch(`${API_BASE}/api/v1/contributors/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }

      setResult(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="slide-up max-w-xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="glass-card p-2.5">
            <UserPlus size={18} className="text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Contribute to Syndicate</h1>
            <p className="text-sm text-white/40 mt-1">Add your API key to expand the hive with new agents</p>
          </div>
        </div>
      </div>

      {result ? (
        /* Success State */
        <div className="glass-card p-6 space-y-5 border-emerald-500/20">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-10 w-10 rounded-full bg-emerald-500/10 ring-1 ring-inset ring-emerald-500/20">
              <Check size={20} className="text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-emerald-400">Registration Successful</h2>
              <p className="text-xs text-white/40">{result.message}</p>
            </div>
          </div>

          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 mb-2">Your Bearer Token</p>
            <p className="text-[10px] text-white/30 mb-1.5">Save this token — it will not be shown again</p>
            <code className="block bg-white/[0.03] border border-white/[0.06] rounded-lg p-3 text-sm font-mono break-all select-all text-amber-400/80">
              {result.bearer_token}
            </code>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-4">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30">Agents Created</p>
              <p className="mt-1 text-2xl font-bold tracking-tight">{result.agents_created}</p>
            </div>
            <div className="glass-card p-4">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-white/30">Est. Monthly Cost</p>
              <p className="mt-1 text-2xl font-bold tracking-tight">${result.estimated_monthly_cost_usd.toFixed(2)}</p>
            </div>
          </div>

          <p className="text-sm text-white/40">
            The Board of Directors will assign your agents to teams shortly.
            Check the <a href="/agents" className="text-amber-400/80 hover:text-amber-300 transition-colors">Agents</a> page to see their status.
          </p>
        </div>
      ) : (
        /* Registration Form */
        <form onSubmit={handleSubmit} className="glass-card p-6 space-y-6">
          {/* Display Name */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 block mb-2">Display Name</label>
            <input
              type="text"
              required
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-4 py-2.5 text-white focus:border-amber-400/50 focus:outline-none focus:ring-1 focus:ring-amber-400/20 transition-all placeholder:text-white/20"
              placeholder="Your name or alias"
            />
          </div>

          {/* Email */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 block mb-2">
              Email <span className="text-white/20 normal-case tracking-normal">(optional)</span>
            </label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-4 py-2.5 text-white focus:border-amber-400/50 focus:outline-none focus:ring-1 focus:ring-amber-400/20 transition-all placeholder:text-white/20"
              placeholder="you@email.com"
            />
          </div>

          {/* Provider */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 block mb-2">API Provider</label>
            <div className="grid grid-cols-3 gap-2">
              {(['anthropic', 'openai', 'google'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setForm({ ...form, provider: p, preferred_model: models[p][0] })}
                  className={`py-2.5 rounded-lg text-sm font-semibold transition-all ${
                    form.provider === p
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-black shadow-lg shadow-amber-500/10'
                      : 'bg-white/[0.04] text-white/40 ring-1 ring-white/[0.06] hover:bg-white/[0.06] hover:text-white/60'
                  }`}
                >
                  {p === 'anthropic' ? 'Anthropic' : p === 'openai' ? 'OpenAI' : 'Google'}
                </button>
              ))}
            </div>
          </div>

          {/* API Key */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 block mb-2">API Key</label>
            <input
              type="password"
              required
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-4 py-2.5 text-white font-mono text-sm focus:border-amber-400/50 focus:outline-none focus:ring-1 focus:ring-amber-400/20 transition-all placeholder:text-white/20"
              placeholder={form.provider === 'anthropic' ? 'sk-ant-...' : form.provider === 'openai' ? 'sk-...' : 'AI...'}
            />
            <div className="flex items-center gap-1.5 mt-2">
              <Lock size={10} className="text-white/20" />
              <p className="text-[10px] text-white/20">Encrypted with AES-256-GCM. Never stored in plaintext.</p>
            </div>
          </div>

          {/* Model */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60 block mb-2">Model</label>
            <select
              value={form.preferred_model}
              onChange={(e) => setForm({ ...form, preferred_model: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-4 py-2.5 text-white focus:border-amber-400/50 focus:outline-none focus:ring-1 focus:ring-amber-400/20 transition-all"
            >
              {models[form.provider].map((m) => (
                <option key={m} value={m} className="bg-[#0a0a0f] text-white">{m}</option>
              ))}
            </select>
          </div>

          {/* Agent Count */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400/60">Number of Agents</label>
              <span className="text-sm font-bold text-white">{form.max_agents}</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={form.max_agents}
              onChange={(e) => setForm({ ...form, max_agents: parseInt(e.target.value) })}
              className="w-full accent-amber-500"
            />
            <div className="flex justify-between text-[10px] text-white/20 mt-1">
              <span>1</span>
              <span>5</span>
              <span>10</span>
            </div>
          </div>

          {/* Error State */}
          {error && (
            <div className="glass-card p-3 border-red-500/20 bg-red-500/[0.04] flex items-start gap-2.5">
              <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-amber-500 to-orange-500 text-black py-3 rounded-xl font-bold hover:shadow-lg hover:shadow-amber-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Shield size={16} className="animate-spin" />
                Registering...
              </>
            ) : (
              <>
                Register & Contribute
                <ChevronRight size={16} />
              </>
            )}
          </button>
        </form>
      )}
    </div>
  );
}
