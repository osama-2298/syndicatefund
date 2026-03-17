import type {
  AgentSummary, TeamSummary, Portfolio,
  RegisterRequest, RegisterResponse, PipelineEvent,
  BoardSession, CeoPost, ResearchReport, MoltbookInfo,
  TeamPerf, SignalItem, AgentStats, TradeEntry,
} from './types';

export interface CycleSummary {
  id: number;
  started_at: string;
  completed_at: string | null;
  duration_secs: number | null;
  regime: string | null;
  coins_analyzed: number;
  signals_produced: number;
  orders_executed: number;
  portfolio_value: number | null;
  error: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    next: { revalidate: 30 },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Client-side fetch (no caching, for use in useEffect)
async function fetchClient<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export { API_BASE };

export const api = {
  getPortfolio: () => fetchAPI<Portfolio>('/api/v1/portfolio'),
  getAgents: () => fetchAPI<AgentSummary[]>('/api/v1/agents'),
  getAgent: (id: string) => fetchClient<AgentSummary>(`/api/v1/agents/${id}`),
  getAgentSignals: (id: string, limit = 20) => fetchClient<SignalItem[]>(`/api/v1/agents/${id}/signals?limit=${limit}`),
  getAgentStats: (id: string) => fetchClient<AgentStats>(`/api/v1/agents/${id}/stats`),
  getTeams: () => fetchAPI<TeamSummary[]>('/api/v1/teams'),
  getCycles: (limit = 20) => fetchAPI<CycleSummary[]>(`/api/v1/cycles?limit=${limit}`),
  getCurrentCycle: () => fetchAPI<any>('/api/v1/cycles/current'),
  getEvents: (params?: { limit?: number; event_type?: string; cycle_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.event_type) qs.set('event_type', params.event_type);
    if (params?.cycle_id) qs.set('cycle_id', params.cycle_id);
    return fetchClient<PipelineEvent[]>(`/api/v1/events?${qs}`);
  },
  getLiveEvents: () => fetchClient<PipelineEvent[]>('/api/v1/events/live'),
  getTeamPerformance: () => fetchClient<TeamPerf>('/api/v1/portfolio/team-performance'),
  getTrades: () => fetchClient<TradeEntry[]>('/api/v1/portfolio/trades'),
  getBoardSessions: (limit = 20) => fetchClient<BoardSession[]>(`/api/v1/board/sessions?limit=${limit}`),
  getCeoPosts: (params?: { limit?: number; post_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.post_type) qs.set('post_type', params.post_type);
    return fetchClient<CeoPost[]>(`/api/v1/ceo/posts?${qs}`);
  },
  getMoltbookPosts: (limit = 50) => fetchClient<MoltbookInfo>(`/api/v1/moltbook/posts?limit=${limit}`),
  getResearchReports: (params?: { limit?: number; report_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.report_type) qs.set('report_type', params.report_type);
    return fetchClient<ResearchReport[]>(`/api/v1/research/reports?${qs}`);
  },
  getHealth: () => fetchAPI<{ status: string }>('/health'),
  register: (data: RegisterRequest) =>
    fetchClient<RegisterResponse>('/api/v1/contributors/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
