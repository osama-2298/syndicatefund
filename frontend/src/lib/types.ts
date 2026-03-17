// ── Centralized types ──
// Single source of truth for all API interfaces used across pages

export interface PipelineEvent {
  id: string;
  cycle_id: number | null;
  event_type: string;
  timestamp: string;
  stage: string;
  actor: string;
  title: string;
  detail: Record<string, any> | null;
  elapsed_ms: number | null;
}

export interface CycleData {
  id: number;
  started_at: string;
  completed_at: string | null;
  regime: string | null;
  coins_analyzed: number;
  signals_produced: number;
  orders_executed: number;
  duration_secs: number | null;
}

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

export interface Portfolio {
  cash: number;
  positions: Position[];
  total_value?: number;
  total_realized_pnl: number;
  total_unrealized_pnl?: number;
  total_position_value?: number;
}

export interface Position {
  symbol: string;
  side: string;
  entry_price: number;
  quantity: number;
  current_price: number;
  unrealized_pnl?: number;
  pnl_pct?: number;
}

export interface TradeEntry {
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  stop_loss: number;
  take_profit_1: number;
  conviction: number;
  confidence: number;
  risk_amount: number;
  pnl_pct: number;
  pnl_usd: number;
  exit_reason: string;
  holding_hours: number;
  exit_time: string;
  asset_tier: string;
}

export interface SignalItem {
  id: string;
  symbol: string;
  action: string;
  confidence: number;
  conviction: number | null;
  reasoning: string | null;
  outcome: string;
  created_at: string;
}

export interface AgentStats {
  streak_count: number;
  streak_type: string;
  avg_conviction: number | null;
  contrarian_rate: number | null;
}

export interface TeamPerf {
  [team: string]: {
    total_signals: number;
    signal_accuracy: number;
    correct: number;
    incorrect: number;
    pending: number;
    current_weight: number;
  };
}

export interface BoardDecision {
  id: string;
  decision_type: string;
  agent_id: string | null;
  team_id: string | null;
  reasoning: string | null;
  decided_by: string;
  created_at: string;
}

export interface BoardSession {
  session_id: string;
  decisions: BoardDecision[];
  created_at: string;
}

export interface CeoPost {
  id: string;
  post_type: string;
  title: string;
  content: string;
  summary: string | null;
  market_context: Record<string, any> | null;
  created_at: string;
}

export interface ResearchReport {
  id: string;
  researcher: string;
  report_type: string;
  title: string;
  summary: string;
  findings: Finding[] | Record<string, any> | null;
  recommendations: string[] | null;
  data_context: DataContext | null;
  created_at: string;
}

export interface Finding {
  severity?: string;
  label?: string;
  detail?: string;
  [key: string]: any;
}

export interface DataContext {
  period?: string;
  sample_size?: string | number;
  [key: string]: any;
}

export interface MoltbookPost {
  moltbook_post_id: string | null;
  title: string;
  content: string;
  submolt: string;
  posted_at: string;
}

export interface MoltbookInfo {
  profile_url: string;
  agent_name: string;
  posts: MoltbookPost[];
  total_posts: number;
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
