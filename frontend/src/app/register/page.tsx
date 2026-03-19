'use client';

import { useState, useMemo } from 'react';
import {
  Loader2,
  Shield,
  Check,
  AlertCircle,
  ChevronRight,
  Lock,
  Eye,
  EyeOff,
  Cpu,
  Search,
  Key,
  Minus,
  Plus,
  Copy,
  CheckCheck,
  Layers,
  Bot,
  ArrowRight,
} from 'lucide-react';
import { API_BASE } from '@/lib/api';

// ── Pricing (mirrors backend cost_estimator.py) ──
const MODEL_PRICING: Record<string, { input_per_m: number; output_per_m: number }> = {
  'claude-opus-4-6': { input_per_m: 15.0, output_per_m: 75.0 },
  'claude-sonnet-4-6': { input_per_m: 3.0, output_per_m: 15.0 },
  'claude-haiku-4-5-20251001': { input_per_m: 0.80, output_per_m: 4.0 },
  'gpt-4o': { input_per_m: 2.50, output_per_m: 10.0 },
  'gpt-4o-mini': { input_per_m: 0.15, output_per_m: 0.60 },
  'gemini-2.0-flash': { input_per_m: 0.10, output_per_m: 0.40 },
};

const AVG_INPUT_TOKENS = 2000;
const AVG_OUTPUT_TOKENS = 500;
const CYCLES_PER_DAY = 6;
const AVG_COINS_PER_CYCLE = 8;

function estimateMonthlyCost(model: string, numAgents: number): number {
  const pricing = MODEL_PRICING[model] ?? MODEL_PRICING['claude-sonnet-4-6'];
  const inputCost = (AVG_INPUT_TOKENS / 1_000_000) * pricing.input_per_m;
  const outputCost = (AVG_OUTPUT_TOKENS / 1_000_000) * pricing.output_per_m;
  const costPerCall = inputCost + outputCost;
  const callsPerDay = numAgents * AVG_COINS_PER_CYCLE * CYCLES_PER_DAY;
  return costPerCall * callsPerDay * 30;
}

const providers = [
  {
    id: 'anthropic',
    name: 'Anthropic',
    models: ['claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
    startingPrice: '$3/M tokens',
    description: 'Claude models — deep reasoning, strong analysis',
    gradient: 'from-amber-400/20 to-orange-500/20',
    ring: 'ring-amber-400/30',
    placeholder: 'sk-ant-...',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    models: ['gpt-4o', 'gpt-4o-mini'],
    startingPrice: '$2.50/M tokens',
    description: 'GPT models — broad knowledge, fast inference',
    gradient: 'from-emerald-400/20 to-teal-500/20',
    ring: 'ring-emerald-400/30',
    placeholder: 'sk-...',
  },
  {
    id: 'google',
    name: 'Google',
    models: ['gemini-2.0-flash'],
    startingPrice: '$0.10/M tokens',
    description: 'Gemini models — cost-effective, high throughput',
    gradient: 'from-blue-400/20 to-indigo-500/20',
    ring: 'ring-blue-400/30',
    placeholder: 'AI...',
  },
];

const steps = ['Identity', 'Provider', 'Configure'];

const STORAGE_KEY = 'syn_bearer_token';

export default function RegisterPage() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    display_name: '',
    email: '',
    provider: 'anthropic',
    api_key: '',
    max_agents: 2,
    preferred_model: 'claude-sonnet-4-6',
  });
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const selectedProvider = providers.find((p) => p.id === form.provider)!;

  // Live cost estimate
  const estimatedCost = useMemo(
    () => estimateMonthlyCost(form.preferred_model, form.max_agents),
    [form.preferred_model, form.max_agents],
  );

  const costPerAgent = useMemo(
    () => estimateMonthlyCost(form.preferred_model, 1),
    [form.preferred_model],
  );

  const canAdvance = () => {
    if (step === 0) return form.display_name.trim().length > 0;
    if (step === 1) return form.api_key.trim().length > 0;
    return true;
  };

  const handleSubmit = async () => {
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
      const data = await res.json();
      setResult(data);

      // Auto-save bearer token so /profile works immediately
      if (data.bearer_token) {
        localStorage.setItem(STORAGE_KEY, data.bearer_token);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToken = () => {
    if (result?.bearer_token) {
      navigator.clipboard.writeText(result.bearer_token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // ── Success state ──
  if (result) {
    return (
      <div className="max-w-2xl mx-auto slide-up">
        {/* Animated gradient border wrapper */}
        <div className="relative rounded-xl p-px overflow-hidden">
          <div
            className="absolute inset-0 rounded-xl"
            style={{
              background:
                'conic-gradient(from 0deg, #8b5cf6, #22c55e, #06b6d4, #a855f7, #8b5cf6)',
              animation: 'spin 4s linear infinite',
            }}
          />
          <div className="relative bg-syn-bg rounded-xl p-8">
            {/* Header */}
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 rounded-full bg-emerald-400/10 flex items-center justify-center ring-1 ring-emerald-400/20">
                <Check size={24} className="text-emerald-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-emerald-400">Registration Successful</h2>
                <p className="text-sm text-white/40">{result.message}</p>
              </div>
            </div>

            {/* Bearer token */}
            <div className="mb-6">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-2">
                Your Bearer Token
              </p>
              <p className="text-xs text-red-400/60 mb-2">
                Save this token now. It will not be shown again.
              </p>
              <div className="relative group">
                <code className="block bg-black/40 border border-syn-border rounded-lg p-4 text-sm font-mono tabular-nums break-all select-all text-syn-accent/80 pr-12">
                  {result.bearer_token}
                </code>
                <button
                  onClick={copyToken}
                  className="absolute top-3 right-3 p-1.5 rounded-md bg-white/[0.04] hover:bg-white/[0.08] transition-colors"
                >
                  {copied ? (
                    <CheckCheck size={14} className="text-emerald-400" />
                  ) : (
                    <Copy size={14} className="text-white/30" />
                  )}
                </button>
              </div>
              <p className="text-[10px] text-emerald-400/40 mt-2">
                Token has been auto-saved to this browser.
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              <div className="bg-white/[0.02] border border-syn-border rounded-lg p-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/25 mb-1">
                  Agents Created
                </p>
                <p className="text-2xl font-bold font-mono tabular-nums text-white">
                  {result.agents_created}
                </p>
              </div>
              <div className="bg-white/[0.02] border border-syn-border rounded-lg p-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/25 mb-1">
                  Est. Monthly Cost
                </p>
                <p className="text-2xl font-bold font-mono tabular-nums text-white">
                  ${result.estimated_monthly_cost_usd?.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Next steps */}
            <div className="bg-white/[0.02] border border-syn-border rounded-lg p-4 mb-6">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-3">
                What Happens Next
              </p>
              <div className="space-y-2">
                {[
                  'The Board of Directors reviews your registration and assigns agents to teams.',
                  'Agents start in quarantine (0.3x weight) and earn full weight after 10 signals.',
                  <>Visit the <a href="/agents" className="text-syn-accent hover:text-violet-300 transition-colors underline underline-offset-2">Agents</a> page to track their performance.</>,
                  'Pause, resume, or cancel anytime from your profile.',
                ].map((text, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <div className="w-5 h-5 rounded-full bg-syn-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-[10px] font-bold text-syn-accent">{i + 1}</span>
                    </div>
                    <p className="text-sm text-white/50">{text}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Go to Profile CTA */}
            <a
              href="/profile"
              className="w-full bg-syn-accent hover:bg-syn-accent-hover text-white py-3 rounded-xl font-bold text-sm hover:shadow-lg hover:shadow-violet-500/20 transition-all flex items-center justify-center gap-2"
            >
              Go to Your Profile
              <ArrowRight size={16} />
            </a>
          </div>
        </div>

        <style jsx>{`
          @keyframes spin {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }
        `}</style>
      </div>
    );
  }

  // ── Main layout: value prop + form ──
  return (
    <div className="max-w-5xl mx-auto slide-up">
      <div className="flex flex-col lg:flex-row gap-8 lg:gap-12">
        {/* ── Left: Value proposition (40%) ── */}
        <div className="lg:w-[38%] lg:pt-6">
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
            Deploy Your Own Analyst
          </h1>
          <p className="text-sm text-white/40 mb-8 leading-relaxed">
            Bring your API key. Your agents get assigned to a team, start analyzing live markets, and produce real signals. If they perform — they earn influence. If they don&apos;t — the board fires them.
          </p>

          <div className="space-y-4">
            {[
              {
                icon: Bot,
                title: 'Your agents join the analysis',
                desc: 'Assigned to teams by the Board, trained with custom prompts, deployed to live cycles.',
                color: 'text-syn-accent',
                bg: 'bg-syn-accent/10',
              },
              {
                icon: Search,
                title: 'Full transparency — see everything',
                desc: 'Every signal, every vote, every team synthesis. Nothing hidden.',
                color: 'text-emerald-400',
                bg: 'bg-emerald-400/10',
              },
              {
                icon: Shield,
                title: 'AES-256 encrypted keys',
                desc: 'Your API keys are encrypted with AES-256-GCM. Never stored in plaintext, never logged.',
                color: 'text-blue-400',
                bg: 'bg-blue-400/10',
              },
              {
                icon: Layers,
                title: 'Full control — pause or stop anytime',
                desc: 'Pause your agents to stop running, resume when ready, or cancel and all agents get fired.',
                color: 'text-purple-400',
                bg: 'bg-purple-400/10',
              },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3.5">
                <div
                  className={`w-9 h-9 rounded-lg ${item.bg} flex items-center justify-center flex-shrink-0 ring-1 ring-white/[0.04]`}
                >
                  <item.icon size={16} className={item.color} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{item.title}</p>
                  <p className="text-xs text-white/30 leading-relaxed mt-0.5">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Right: Form (60%) ── */}
        <div className="lg:flex-1">
          {/* Step indicator */}
          <div className="flex items-center gap-1.5 sm:gap-2 mb-6">
            {steps.map((s, i) => (
              <div key={s} className="flex items-center gap-1.5 sm:gap-2">
                <div className="flex items-center gap-1 sm:gap-1.5">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all flex-shrink-0 ${
                      i === step
                        ? 'bg-syn-accent/20 text-syn-accent ring-1 ring-syn-accent/30'
                        : i < step
                        ? 'bg-emerald-400/10 text-emerald-400'
                        : 'bg-white/[0.04] text-white/20'
                    }`}
                  >
                    {i < step ? <Check size={12} /> : i + 1}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      i === step ? 'text-white/60' : 'text-white/20'
                    }`}
                  >
                    {s}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className="w-4 sm:w-8 h-px bg-syn-border mx-0.5 sm:mx-1" />
                )}
              </div>
            ))}
          </div>

          <div className="bg-syn-surface border border-syn-border rounded-xl p-6">
            {/* ── Step 0: Identity ── */}
            {step === 0 && (
              <div className="space-y-5">
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted block mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    required
                    value={form.display_name}
                    onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                    className="w-full bg-white/[0.03] border border-syn-border rounded-lg px-4 py-3 text-white focus:border-syn-accent/50 focus:outline-none focus:ring-1 focus:ring-syn-accent/20 transition-all placeholder:text-white/15"
                    placeholder="Your name or alias"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted block mb-2">
                    Email{' '}
                    <span className="text-white/20 normal-case tracking-normal font-normal">
                      (optional)
                    </span>
                  </label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="w-full bg-white/[0.03] border border-syn-border rounded-lg px-4 py-3 text-white focus:border-syn-accent/50 focus:outline-none focus:ring-1 focus:ring-syn-accent/20 transition-all placeholder:text-white/15"
                    placeholder="you@email.com"
                  />
                </div>

                <button
                  onClick={() => canAdvance() && setStep(1)}
                  disabled={!canAdvance()}
                  className="w-full bg-white/[0.06] hover:bg-white/[0.10] text-white py-3 rounded-xl font-semibold text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  Continue
                  <ChevronRight size={15} />
                </button>
              </div>
            )}

            {/* ── Step 1: Provider + API key ── */}
            {step === 1 && (
              <div className="space-y-5">
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted block mb-3">
                    Select Provider
                  </label>
                  <div className="space-y-2.5">
                    {providers.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() =>
                          setForm({ ...form, provider: p.id, preferred_model: p.models[0] })
                        }
                        className={`w-full text-left p-4 rounded-xl border transition-all ${
                          form.provider === p.id
                            ? `bg-gradient-to-r ${p.gradient} border-white/[0.10] ring-1 ${p.ring}`
                            : 'bg-white/[0.02] border-syn-border hover:bg-white/[0.04] hover:border-white/[0.08]'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-bold text-white">{p.name}</span>
                          <span className="text-[10px] font-mono tabular-nums text-white/30">
                            from {p.startingPrice}
                          </span>
                        </div>
                        <p className="text-xs text-white/35 mb-2">{p.description}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {p.models.map((m) => (
                            <span
                              key={m}
                              className="text-[10px] font-mono text-white/20 bg-white/[0.04] px-2 py-0.5 rounded"
                            >
                              {m}
                            </span>
                          ))}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted block mb-2">
                    API Key
                  </label>
                  <div className="relative">
                    <input
                      type={showKey ? 'text' : 'password'}
                      required
                      value={form.api_key}
                      onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                      className="w-full bg-white/[0.03] border border-syn-border rounded-lg px-4 py-3 pr-12 text-white font-mono text-sm focus:border-syn-accent/50 focus:outline-none focus:ring-1 focus:ring-syn-accent/20 transition-all placeholder:text-white/15"
                      placeholder={selectedProvider.placeholder}
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-white/[0.06] transition-colors"
                    >
                      {showKey ? (
                        <EyeOff size={14} className="text-white/25" />
                      ) : (
                        <Eye size={14} className="text-white/25" />
                      )}
                    </button>
                  </div>
                  <div className="flex items-center gap-1.5 mt-2">
                    <Lock size={10} className="text-white/15" />
                    <p className="text-[10px] text-white/15">
                      Encrypted with AES-256-GCM. Never stored in plaintext.
                    </p>
                  </div>
                </div>

                <div className="flex gap-2.5">
                  <button
                    onClick={() => setStep(0)}
                    className="px-5 bg-white/[0.04] hover:bg-white/[0.06] text-white/50 py-3 rounded-xl text-sm transition-all"
                  >
                    Back
                  </button>
                  <button
                    onClick={() => canAdvance() && setStep(2)}
                    disabled={!canAdvance()}
                    className="flex-1 bg-white/[0.06] hover:bg-white/[0.10] text-white py-3 rounded-xl font-semibold text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    Continue
                    <ChevronRight size={15} />
                  </button>
                </div>
              </div>
            )}

            {/* ── Step 2: Configure + Submit ── */}
            {step === 2 && (
              <div className="space-y-5">
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted block mb-2">
                    Model
                  </label>
                  <div className="relative">
                    <select
                      value={form.preferred_model}
                      onChange={(e) => setForm({ ...form, preferred_model: e.target.value })}
                      className="w-full bg-white/[0.03] border border-syn-border rounded-lg px-4 py-3 text-white text-sm focus:border-syn-accent/50 focus:outline-none focus:ring-1 focus:ring-syn-accent/20 transition-all appearance-none cursor-pointer"
                    >
                      {selectedProvider.models.map((m) => (
                        <option key={m} value={m} className="bg-syn-bg text-white">
                          {m}
                        </option>
                      ))}
                    </select>
                    <Cpu
                      size={14}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/20 pointer-events-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted block mb-3">
                    Number of Agents
                  </label>
                  <div className="flex items-center justify-center gap-5">
                    <button
                      type="button"
                      onClick={() =>
                        setForm({ ...form, max_agents: Math.max(1, form.max_agents - 1) })
                      }
                      className="w-10 h-10 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-syn-border flex items-center justify-center transition-all"
                    >
                      <Minus size={16} className="text-white/40" />
                    </button>
                    <div className="w-20 text-center">
                      <span className="text-3xl font-bold font-mono tabular-nums text-white">
                        {form.max_agents}
                      </span>
                      <p className="text-[10px] text-white/20 mt-0.5">agents</p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setForm({ ...form, max_agents: Math.min(10, form.max_agents + 1) })
                      }
                      className="w-10 h-10 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-syn-border flex items-center justify-center transition-all"
                    >
                      <Plus size={16} className="text-white/40" />
                    </button>
                  </div>
                  <div className="flex justify-between text-[10px] text-white/15 mt-2 px-4">
                    <span>Min: 1</span>
                    <span>Max: 10</span>
                  </div>
                </div>

                {/* Live cost estimate */}
                <div className="bg-gradient-to-b from-syn-accent/[0.04] to-transparent border border-syn-accent/10 rounded-xl p-4 space-y-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-accent/60">
                    Estimated Monthly Cost
                  </p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold font-mono tabular-nums text-white">
                      ${estimatedCost.toFixed(2)}
                    </span>
                    <span className="text-xs text-white/25">/month</span>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="text-white/25">Per agent</span>
                      <span className="text-white/40 font-mono tabular-nums">
                        ${costPerAgent.toFixed(2)}/mo
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-white/25">Cycles per day</span>
                      <span className="text-white/40 font-mono tabular-nums">6 (every 4h)</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-white/25">Avg coins per cycle</span>
                      <span className="text-white/40 font-mono tabular-nums">~8</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-white/15 leading-relaxed pt-1 border-t border-white/[0.04]">
                    Cost is billed directly by your LLM provider ({selectedProvider.name}), not by Syndicate. This is an estimate based on average token usage.
                  </p>
                </div>

                {/* Summary */}
                <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg p-4 space-y-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/25 mb-2">
                    Summary
                  </p>
                  <div className="flex justify-between text-xs gap-2">
                    <span className="text-white/30 shrink-0">Name</span>
                    <span className="text-white/60 font-medium truncate">{form.display_name}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-white/30">Provider</span>
                    <span className="text-white/60 font-medium">{selectedProvider.name}</span>
                  </div>
                  <div className="flex justify-between text-xs gap-2">
                    <span className="text-white/30 shrink-0">Model</span>
                    <span className="text-white/60 font-mono text-xs truncate">{form.preferred_model}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-white/30">Agents</span>
                    <span className="text-white/60 font-mono tabular-nums">{form.max_agents}</span>
                  </div>
                </div>

                {/* Error state */}
                {error && (
                  <div className="bg-red-400/[0.05] border border-red-400/20 rounded-lg p-4 flex items-start gap-3">
                    <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-400">Registration Failed</p>
                      <p className="text-xs text-red-400/60 mt-0.5">{error}</p>
                    </div>
                  </div>
                )}

                <div className="flex gap-2.5">
                  <button
                    onClick={() => setStep(1)}
                    className="px-5 bg-white/[0.04] hover:bg-white/[0.06] text-white/50 py-3 rounded-xl text-sm transition-all"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="flex-1 bg-syn-accent hover:bg-syn-accent-hover text-white py-3 rounded-xl font-bold text-sm hover:shadow-lg hover:shadow-violet-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Validating key...
                      </>
                    ) : (
                      <>
                        Register & Deploy
                        <ChevronRight size={16} />
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
