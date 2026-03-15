const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    next: { revalidate: 30 }, // Cache for 30 seconds
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Types matching the backend API responses
export interface AgentSummary {
  id: string;
  contributor_id: string | null;
  team_id: string | null;
  team_name: string | null;
  role: string;
  agent_class: string | null;
  model: string;
  provider: string;
  status: string;
  total_signals: number;
  correct_signals: number;
  accuracy: number;
  total_cost_usd: number;
  quarantine_signals_remaining: number;
  created_at: string;
}

export interface TeamSummary {
  id: string;
  name: string;
  discipline: string;
  status: string;
  weight: number;
  activation_mode: string;
  min_agents: number;
  is_system: boolean;
  created_by: string;
  created_at: string;
  agent_count: number;
  active_agent_count: number;
  data_keys: string[];
}

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

export interface Portfolio {
  cash: number;
  positions: Array<{
    symbol: string;
    side: string;
    entry_price: number;
    quantity: number;
    current_price: number;
    unrealized_pnl?: number;
    pnl_pct?: number;
  }>;
  total_value?: number;
  total_realized_pnl: number;
  total_unrealized_pnl?: number;
  total_position_value?: number;
}

export interface RegisterRequest {
  display_name: string;
  email?: string;
  api_key_anthropic?: string;
  api_key_openai?: string;
  api_key_google?: string;
  max_agents: number;
  preferred_model: string;
  cost_limit_usd?: number;
}

export interface RegisterResponse {
  contributor_id: string;
  bearer_token: string;
  agents_created: number;
  estimated_monthly_cost_usd: number;
  message: string;
}

// API functions
export const api = {
  getPortfolio: () => fetchAPI<Portfolio>('/api/v1/portfolio'),
  getAgents: () => fetchAPI<AgentSummary[]>('/api/v1/agents'),
  getTeams: () => fetchAPI<TeamSummary[]>('/api/v1/teams'),
  getCycles: (limit = 20) => fetchAPI<CycleSummary[]>(`/api/v1/cycles?limit=${limit}`),
  getCurrentCycle: () => fetchAPI<any>('/api/v1/cycles/current'),
  getHealth: () => fetchAPI<{ status: string }>('/health'),
  register: (data: RegisterRequest) =>
    fetchAPI<RegisterResponse>('/api/v1/contributors/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
