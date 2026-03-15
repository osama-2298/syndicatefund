'use client';

import { useState } from 'react';

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
    <div className="max-w-xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Contribute to Hivemind</h1>
        <p className="text-hive-muted">
          Add your API key to contribute agents to the fund. More agents = more coins scanned, deeper analysis.
        </p>
      </div>

      {result ? (
        <div className="bg-hive-card border border-hive-green/30 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-hive-green text-xl">&#10003;</span>
            <h2 className="text-lg font-bold text-hive-green">Registration Successful</h2>
          </div>
          <p className="text-hive-muted">{result.message}</p>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-hive-muted mb-1">Your Bearer Token (save this!)</p>
              <code className="block bg-hive-bg border border-hive-border rounded p-3 text-sm break-all select-all">
                {result.bearer_token}
              </code>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-hive-muted">Agents Created</p>
                <p className="text-lg font-bold">{result.agents_created}</p>
              </div>
              <div>
                <p className="text-xs text-hive-muted">Est. Monthly Cost</p>
                <p className="text-lg font-bold">${result.estimated_monthly_cost_usd.toFixed(2)}</p>
              </div>
            </div>
          </div>
          <p className="text-sm text-hive-muted">
            The Board of Directors will assign your agents to teams shortly.
            Check the <a href="/agents" className="text-hive-accent hover:underline">Agents</a> page to see their status.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="bg-hive-card border border-hive-border rounded-xl p-6 space-y-5">
          {/* Display Name */}
          <div>
            <label className="block text-sm text-hive-muted mb-1.5">Display Name *</label>
            <input
              type="text"
              required
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="w-full bg-hive-bg border border-hive-border rounded-lg px-4 py-2.5 text-hive-text focus:border-hive-accent focus:outline-none transition-colors"
              placeholder="Your name or alias"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm text-hive-muted mb-1.5">Email (optional)</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full bg-hive-bg border border-hive-border rounded-lg px-4 py-2.5 text-hive-text focus:border-hive-accent focus:outline-none transition-colors"
              placeholder="you@email.com"
            />
          </div>

          {/* Provider */}
          <div>
            <label className="block text-sm text-hive-muted mb-1.5">API Provider *</label>
            <div className="grid grid-cols-3 gap-2">
              {(['anthropic', 'openai', 'google'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setForm({ ...form, provider: p, preferred_model: models[p][0] })}
                  className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                    form.provider === p
                      ? 'bg-hive-accent text-black'
                      : 'bg-hive-border text-hive-muted hover:text-hive-text'
                  }`}
                >
                  {p === 'anthropic' ? 'Anthropic' : p === 'openai' ? 'OpenAI' : 'Google'}
                </button>
              ))}
            </div>
          </div>

          {/* API Key */}
          <div>
            <label className="block text-sm text-hive-muted mb-1.5">API Key *</label>
            <input
              type="password"
              required
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              className="w-full bg-hive-bg border border-hive-border rounded-lg px-4 py-2.5 text-hive-text font-mono text-sm focus:border-hive-accent focus:outline-none transition-colors"
              placeholder={form.provider === 'anthropic' ? 'sk-ant-...' : form.provider === 'openai' ? 'sk-...' : 'AI...'}
            />
            <p className="text-xs text-hive-muted mt-1">Encrypted with AES-256-GCM. Never stored in plaintext.</p>
          </div>

          {/* Model */}
          <div>
            <label className="block text-sm text-hive-muted mb-1.5">Model</label>
            <select
              value={form.preferred_model}
              onChange={(e) => setForm({ ...form, preferred_model: e.target.value })}
              className="w-full bg-hive-bg border border-hive-border rounded-lg px-4 py-2.5 text-hive-text focus:border-hive-accent focus:outline-none transition-colors"
            >
              {models[form.provider].map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {/* Agent Count */}
          <div>
            <label className="block text-sm text-hive-muted mb-1.5">Number of Agents ({form.max_agents})</label>
            <input
              type="range"
              min={1}
              max={10}
              value={form.max_agents}
              onChange={(e) => setForm({ ...form, max_agents: parseInt(e.target.value) })}
              className="w-full accent-amber-500"
            />
            <div className="flex justify-between text-xs text-hive-muted">
              <span>1</span>
              <span>5</span>
              <span>10</span>
            </div>
          </div>

          {error && (
            <div className="bg-hive-red/10 border border-hive-red/30 rounded-lg p-3 text-sm text-hive-red">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-hive-accent text-black py-3 rounded-lg font-bold hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Registering...' : 'Register & Contribute'}
          </button>
        </form>
      )}
    </div>
  );
}
