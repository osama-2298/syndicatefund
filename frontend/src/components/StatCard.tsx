interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export default function StatCard({ title, value, subtitle, trend }: StatCardProps) {
  const trendColor = trend === 'up' ? 'text-hive-green' : trend === 'down' ? 'text-hive-red' : 'text-hive-muted';
  return (
    <div className="bg-hive-card border border-hive-border rounded-xl p-5">
      <p className="text-sm text-hive-muted mb-1">{title}</p>
      <p className={`text-2xl font-bold ${trendColor}`}>{value}</p>
      {subtitle && <p className="text-xs text-hive-muted mt-1">{subtitle}</p>}
    </div>
  );
}
