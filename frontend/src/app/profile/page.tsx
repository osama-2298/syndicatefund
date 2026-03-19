'use client';

import { useState, useEffect } from 'react';
import {
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  LogOut,
  Pause,
  Play,
  XCircle,
  Bot,
  DollarSign,
  Shield,
  Users,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { ContributorProfile, AgentDetail } from '@/lib/types';
import { STATUS_COLORS, CONTRIBUTOR_STATUS_COLORS } from '@/lib/constants';

const STORAGE_KEY = 'syn_bearer_token';

export default function ProfilePage() {
  const [token, setToken] = useState('');
  const [tokenInput, setTokenInput] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [profile, setProfile] = useState<ContributorProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [cancelConfirm, setCancelConfirm] = useState('');
  const [showCancelPanel, setShowCancelPanel] = useState(false);

  // Auto-load from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      setToken(saved);
      loadProfile(saved);
    }
  }, []);

  async function loadProfile(bearerToken: string) {
    setLoading(true);
    setError('');
    try {
      const data = await api.getProfile(bearerToken);
      setProfile(data);
      setToken(bearerToken);
      localStorage.setItem(STORAGE_KEY, bearerToken);
    } catch {
      setError('Invalid or expired token');
      localStorage.removeItem(STORAGE_KEY);
      setToken('');
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY);
    setToken('');
    setTokenInput('');
    setProfile(null);
    setError('');
  }

  async function handlePause() {
    setActionLoading('pause');
    try {
      await api.pauseContribution(token);
      await loadProfile(token);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading('');
    }
  }

  async function handleResume() {
    setActionLoading('resume');
    try {
      await api.resumeContribution(token);
      await loadProfile(token);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading('');
    }
  }

  async function handleCancel() {
    if (cancelConfirm !== 'CANCEL') return;
    setActionLoading('cancel');
    try {
      await api.cancelContribution(token);
      handleLogout();
      setError('Contribution cancelled. All agents have been fired.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading('');
      setCancelConfirm('');
    }
  }

  // ── Token Entry State ──
  if (!profile) {
    return (
      <div className="max-w-md mx-auto mt-12 slide-up">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-syn-accent/10 flex items-center justify-center mx-auto mb-4 ring-1 ring-syn-accent/20">
            <Shield size={24} className="text-syn-accent" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Contributor Profile</h1>
          <p className="text-sm text-syn-muted">Enter your bearer token to view your profile and manage your contribution.</p>
        </div>

        <div className="bg-syn-surface border border-syn-border rounded-xl p-6">
          <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted block mb-2">
            Bearer Token
          </label>
          <div className="relative mb-4">
            <input
              type={showToken ? 'text' : 'password'}
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && tokenInput.trim() && loadProfile(tokenInput.trim())}
              className="w-full bg-white/[0.03] border border-syn-border rounded-lg px-4 py-3 pr-12 text-white font-mono text-sm focus:border-syn-accent/50 focus:outline-none focus:ring-1 focus:ring-syn-accent/20 transition-all placeholder:text-white/15"
              placeholder="hvm_..."
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-white/[0.06] transition-colors"
            >
              {showToken ? <EyeOff size={14} className="text-white/25" /> : <Eye size={14} className="text-white/25" />}
            </button>
          </div>

          {error && (
            <div className="bg-red-400/[0.05] border border-red-400/20 rounded-lg p-3 flex items-center gap-2 mb-4">
              <AlertCircle size={14} className="text-red-400 shrink-0" />
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}

          <button
            onClick={() => tokenInput.trim() && loadProfile(tokenInput.trim())}
            disabled={!tokenInput.trim() || loading}
            className="w-full bg-syn-accent hover:bg-syn-accent-hover text-white py-3 rounded-xl font-semibold text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : null}
            {loading ? 'Loading...' : 'View Profile'}
          </button>
        </div>

        <p className="text-center text-xs text-syn-muted mt-6">
          Don&apos;t have a token?{' '}
          <a href="/register" className="text-syn-accent hover:text-violet-300 transition-colors underline underline-offset-2">
            Register as a contributor
          </a>
        </p>
      </div>
    );
  }

  // ── Profile Dashboard State ──
  const statusColor = CONTRIBUTOR_STATUS_COLORS[profile.status] || CONTRIBUTOR_STATUS_COLORS.active;

  return (
    <div className="max-w-4xl mx-auto slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-white">{profile.display_name}</h1>
            <span className={`text-[10px] font-bold uppercase tracking-[0.15em] px-2.5 py-1 rounded-full ring-1 ${statusColor.text} ${statusColor.bg} ${statusColor.ring}`}>
              {profile.status}
            </span>
          </div>
          <p className="text-sm text-syn-muted">
            Member since {new Date(profile.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
            {profile.email && <span className="ml-2 text-white/20">({profile.email})</span>}
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-sm text-syn-muted hover:text-white transition-colors bg-white/[0.04] hover:bg-white/[0.06] px-4 py-2 rounded-lg self-start"
        >
          <LogOut size={14} />
          Logout
        </button>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { label: 'Total Agents', value: profile.agent_count, icon: Users },
          { label: 'Total Cost', value: `$${profile.total_cost_usd.toFixed(2)}`, icon: DollarSign },
          { label: 'Cost Limit', value: profile.cost_limit_usd ? `$${profile.cost_limit_usd.toFixed(2)}` : 'None', icon: Shield },
          { label: 'Status', value: profile.status.charAt(0).toUpperCase() + profile.status.slice(1), icon: Bot },
        ].map((stat) => (
          <div key={stat.label} className="bg-syn-surface border border-syn-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <stat.icon size={14} className="text-syn-muted" />
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted">{stat.label}</p>
            </div>
            <p className="text-xl font-bold font-mono tabular-nums text-white">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-400/[0.05] border border-red-400/20 rounded-lg p-3 flex items-center gap-2 mb-6">
          <AlertCircle size={14} className="text-red-400 shrink-0" />
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Agents list */}
      <div className="mb-8">
        <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-4">
          Your Agents ({profile.agents.length})
        </h2>
        {profile.agents.length === 0 ? (
          <div className="bg-syn-surface border border-syn-border rounded-xl p-8 text-center">
            <Bot size={32} className="text-syn-muted mx-auto mb-3" />
            <p className="text-sm text-syn-muted">No agents yet. The Board will assign them shortly.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {profile.agents.map((agent: AgentDetail) => {
              const agentStatusClass = STATUS_COLORS[agent.status] || STATUS_COLORS.registered;
              return (
                <a
                  key={agent.id}
                  href={`/agents/${agent.id}`}
                  className="block bg-syn-surface border border-syn-border rounded-xl p-4 hover:border-syn-accent/30 transition-all group"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-lg bg-syn-accent/10 flex items-center justify-center ring-1 ring-white/[0.04] shrink-0">
                        <Bot size={16} className="text-syn-accent" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-semibold text-white">{agent.role}</span>
                          <span className={`text-[9px] font-bold uppercase tracking-[0.15em] px-2 py-0.5 rounded-full ring-1 ${agentStatusClass}`}>
                            {agent.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-syn-muted mt-0.5">
                          {agent.team_name && <span>{agent.team_name}</span>}
                          <span className="text-white/10">|</span>
                          <span className="font-mono text-[11px]">{agent.model}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 sm:gap-6 text-right shrink-0">
                      <div>
                        <p className="text-[10px] text-syn-muted uppercase tracking-wider">Signals</p>
                        <p className="text-sm font-mono tabular-nums text-white">{agent.total_signals}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-syn-muted uppercase tracking-wider">Accuracy</p>
                        <p className="text-sm font-mono tabular-nums text-white">{agent.accuracy.toFixed(1)}%</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-syn-muted uppercase tracking-wider">Cost</p>
                        <p className="text-sm font-mono tabular-nums text-white">${agent.total_cost_usd.toFixed(2)}</p>
                      </div>
                      <ChevronRight size={16} className="text-white/10 group-hover:text-syn-accent transition-colors hidden sm:block" />
                    </div>
                  </div>
                </a>
              );
            })}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="bg-syn-surface border border-syn-border rounded-xl p-6">
        <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-syn-muted mb-4">
          Manage Contribution
        </h2>
        <div className="flex flex-col sm:flex-row gap-3">
          {profile.status === 'active' && (
            <button
              onClick={handlePause}
              disabled={!!actionLoading}
              className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20 hover:bg-amber-500/20 transition-all disabled:opacity-50"
            >
              {actionLoading === 'pause' ? <Loader2 size={14} className="animate-spin" /> : <Pause size={14} />}
              Pause Contribution
            </button>
          )}
          {profile.status === 'paused' && (
            <button
              onClick={handleResume}
              disabled={!!actionLoading}
              className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20 hover:bg-emerald-500/20 transition-all disabled:opacity-50"
            >
              {actionLoading === 'resume' ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              Resume Contribution
            </button>
          )}

          {/* Cancel section */}
          {(profile.status === 'active' || profile.status === 'paused') && (
            <div className="sm:ml-auto">
              {!showCancelPanel ? (
                <button
                  onClick={() => setShowCancelPanel(true)}
                  className="text-xs text-white/30 hover:text-red-400/70 transition-colors underline underline-offset-2"
                >
                  Cancel contribution...
                </button>
              ) : (
                <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4 space-y-3 max-w-sm">
                  <p className="text-xs font-semibold text-red-400 uppercase tracking-wider">This cannot be undone</p>
                  <ul className="text-xs text-white/50 space-y-1">
                    <li>All your agents will be permanently fired</li>
                    <li>Agents will be removed from their teams</li>
                    <li>Signal history is preserved (read-only)</li>
                  </ul>
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      value={cancelConfirm}
                      onChange={(e) => setCancelConfirm(e.target.value)}
                      placeholder='Type CANCEL'
                      className="bg-white/[0.03] border border-syn-border rounded-lg px-3 py-2 text-sm text-white font-mono w-32 focus:border-red-400/50 focus:outline-none focus:ring-1 focus:ring-red-400/20 transition-all placeholder:text-white/15"
                    />
                    <button
                      onClick={handleCancel}
                      disabled={cancelConfirm !== 'CANCEL' || !!actionLoading}
                      className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-red-500/10 text-red-400 ring-1 ring-red-500/20 hover:bg-red-500/20 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      {actionLoading === 'cancel' ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
                      Confirm
                    </button>
                  </div>
                  <button
                    onClick={() => { setShowCancelPanel(false); setCancelConfirm(''); }}
                    className="text-xs text-white/30 hover:text-white/50 transition-colors"
                  >
                    Nevermind
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
