/**
 * Transforms raw pipeline events into plain English that anyone can understand.
 */

export interface HumanizedEvent {
  icon: string; // lucide icon name
  color: string;
  message: string;
}

export function humanizeEvent(event: {
  event_type: string;
  actor?: string;
  title?: string;
  detail?: Record<string, any> | null;
}): HumanizedEvent {
  const d = event.detail || {};

  switch (event.event_type) {
    case 'cycle_start':
      return { icon: 'Play', color: 'text-white/60', message: 'New analysis cycle started' };

    case 'cycle_end':
      return {
        icon: 'CheckCircle', color: 'text-emerald-400',
        message: `Cycle complete — analyzed ${d.coins_analyzed || '?'} coins, produced ${d.signals_produced || '?'} signals, executed ${d.orders_executed || 0} trades`,
      };

    case 'intel_gathered':
      return {
        icon: 'Search', color: 'text-blue-400',
        message: `Market intel collected from ${d.sources?.length || '?'} sources${d.fear_greed ? ` — Fear & Greed: ${d.fear_greed}/100` : ''}`,
      };

    case 'ceo_directive': {
      if (d.emergency_halt) return { icon: 'Shield', color: 'text-red-400', message: `CEO halted all trading — ${d.halt_reason || 'emergency'}` };
      const regime = (d.regime || '').toUpperCase();
      return {
        icon: 'Brain', color: 'text-amber-400',
        message: `CEO reads the market as ${regime}${d.risk_multiplier ? ` — risk level ${d.risk_multiplier}x` : ''}`,
      };
    }

    case 'coo_selection': {
      if (event.actor === 'Hot Coin Detector') {
        const sym = (d.symbol || '').replace('USDT', '');
        return { icon: 'Star', color: 'text-fuchsia-400', message: `Trending coin added: ${sym} — ${d.reason || 'high momentum'}` };
      }
      const coins = (d.coins || []).map((c: string) => c.replace('USDT', '')).join(', ');
      return { icon: 'Target', color: 'text-amber-400', message: `${d.coins?.length || '?'} coins selected for analysis: ${coins}` };
    }

    case 'cro_rules':
      return {
        icon: 'Shield', color: 'text-orange-400',
        message: `Risk limits set — max ${d.max_position_pct || '?'}% per trade, min ${Math.round((d.min_signal_confidence || 0) * 100)}% confidence required`,
      };

    case 'team_signal': {
      const team = d.team || 'Unknown';
      const action = d.action || '?';
      const sym = (d.symbol || '').replace('USDT', '');
      const conf = Math.round((d.confidence || 0) * 100);
      const verb = action === 'BUY' ? 'is bullish on' : action === 'SELL' || action === 'SHORT' ? 'is bearish on' : 'says hold';
      return { icon: 'Users', color: 'text-blue-400', message: `${team} team ${verb} ${sym} (${conf}% confidence)` };
    }

    case 'disagreement': {
      const sym = (d.symbol || '').replace('USDT', '');
      const pol = Math.round((d.polarization || 0) * 100);
      const nBull = (d.bullish_teams || []).length;
      const nBear = (d.bearish_teams || []).length;
      return {
        icon: 'Swords', color: 'text-red-400',
        message: `Teams split on ${sym} — ${nBull} bullish vs ${nBear} bearish (${pol}% disagreement)`,
      };
    }

    case 'aggregation_result': {
      const sym = (d.symbol || '').replace('USDT', '');
      const action = d.action || '?';
      const conf = Math.round((d.confidence || 0) * 100);
      if (action === 'HOLD' || conf === 0) {
        return { icon: 'Scale', color: 'text-violet-400', message: `${sym} — no clear signal, teams are undecided` };
      }
      const direction = action === 'BUY' ? 'Buy' : action === 'SELL' || action === 'SHORT' ? 'Sell' : action;
      return { icon: 'Scale', color: 'text-violet-400', message: `Final signal for ${sym}: ${direction} (${conf}% confidence)` };
    }

    case 'risk_check':
      return {
        icon: 'Shield', color: 'text-orange-400',
        message: `${d.passed || 0} of ${d.total_signals || '?'} signals passed risk checks`,
      };

    case 'pm_review':
      return {
        icon: 'BarChart3', color: 'text-cyan-400',
        message: `Portfolio manager approved ${d.orders_after || 0} trades${d.orders_before !== d.orders_after ? ` (blocked ${(d.orders_before || 0) - (d.orders_after || 0)} for portfolio balance)` : ''}`,
      };

    case 'verdict': {
      const sym = (d.symbol || '').replace('USDT', '');
      if (d.blocked) {
        return { icon: 'XCircle', color: 'text-white/40', message: `${sym} blocked — ${d.reason || 'risk rules'}` };
      }
      return { icon: 'CheckCircle', color: 'text-emerald-400', message: `${sym} approved for trading — ${d.action}` };
    }

    case 'trade_executed': {
      const sym = (d.symbol || '').replace('USDT', '');
      const side = d.side === 'BUY' ? 'Bought' : 'Sold';
      return {
        icon: 'DollarSign', color: 'text-emerald-400',
        message: `${side} ${sym} at $${(d.price || 0).toLocaleString()}`,
      };
    }

    case 'trade_closed': {
      const sym = (d.symbol || '').replace('USDT', '');
      const pnl = d.pnl_pct || 0;
      const pnlStr = pnl > 0 ? `+${(pnl * 100).toFixed(1)}% profit` : `${(pnl * 100).toFixed(1)}% loss`;
      return {
        icon: 'LogOut', color: pnl > 0 ? 'text-emerald-400' : 'text-red-400',
        message: `Closed ${sym} — ${pnlStr} ($${(d.pnl_usd || 0) >= 0 ? '+' : ''}${(d.pnl_usd || 0).toFixed(0)})`,
      };
    }

    case 'ceo_review':
      return { icon: 'Brain', color: 'text-amber-400', message: 'CEO reviewed cycle performance and adjusted team weights' };

    default:
      return { icon: 'Activity', color: 'text-white/40', message: event.title || event.event_type };
  }
}
