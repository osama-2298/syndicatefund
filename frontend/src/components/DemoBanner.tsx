import { AlertTriangle } from 'lucide-react';

export function DemoBanner() {
  return (
    <div className="glass-card px-4 py-2.5 border-amber-500/20 bg-amber-500/5 flex items-center gap-2.5">
      <AlertTriangle size={13} className="text-amber-400 shrink-0" />
      <div>
        <span className="text-[10px] font-bold text-amber-400 tracking-wider">SIMULATED DATA</span>
        <span className="text-[10px] text-hive-muted ml-2">All figures shown are paper trading simulations for demonstration. Not real trading activity.</span>
      </div>
    </div>
  );
}

export function PaperTradingBadge() {
  return (
    <div className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg px-2.5 py-1">
      <span className="text-[10px] font-bold tracking-wider text-amber-400">PAPER</span>
    </div>
  );
}
