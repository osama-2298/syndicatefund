'use client';

interface LineChartProps {
  data: number[];
  labels?: string[];
  benchmarkData?: number[];
  benchmarkLabel?: string;
  height?: number;
  startValue?: number;
  showArea?: boolean;
  color?: string;
  benchmarkColor?: string;
}

export default function LineChart({
  data,
  labels,
  benchmarkData,
  benchmarkLabel = 'SPY',
  height = 160,
  startValue,
  showArea = true,
  color = '#22c55e',
  benchmarkColor = '#6b7280',
}: LineChartProps) {
  if (!data || data.length < 2) return null;

  const allValues = [...data, ...(benchmarkData || [])];
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const range = maxVal - minVal || 1;
  const padding = range * 0.05;
  const yMin = minVal - padding;
  const yMax = maxVal + padding;
  const yRange = yMax - yMin;

  const w = 500;
  const h = height;
  const marginBottom = labels ? 20 : 0;
  const chartH = h - marginBottom;

  const toX = (i: number) => (i / (data.length - 1)) * w;
  const toY = (v: number) => chartH - ((v - yMin) / yRange) * chartH;

  const mainPoints = data.map((v, i) => `${toX(i)},${toY(v)}`).join(' ');
  const areaPoints = `0,${chartH} ${mainPoints} ${w},${chartH}`;

  const benchPoints = benchmarkData
    ? benchmarkData.map((v, i) => `${toX(i)},${toY(v)}`).join(' ')
    : null;

  const baseY = startValue != null ? toY(startValue) : null;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height }} preserveAspectRatio="none">
      {/* Grid lines */}
      {[0.25, 0.5, 0.75].map((pct) => (
        <line
          key={pct}
          x1="0" y1={chartH * pct} x2={w} y2={chartH * pct}
          stroke="currentColor" strokeWidth="0.5" opacity="0.06"
        />
      ))}

      {/* Breakeven line */}
      {baseY != null && baseY > 0 && baseY < chartH && (
        <line x1="0" y1={baseY} x2={w} y2={baseY} stroke="#6b7280" strokeWidth="0.5" strokeDasharray="4,4" opacity="0.3" />
      )}

      {/* Area fill */}
      {showArea && (
        <polygon
          points={areaPoints}
          fill={color}
          opacity="0.08"
        />
      )}

      {/* Benchmark line */}
      {benchPoints && (
        <polyline
          points={benchPoints}
          fill="none"
          stroke={benchmarkColor}
          strokeWidth="1.5"
          strokeDasharray="4,3"
          opacity="0.5"
        />
      )}

      {/* Main line */}
      <polyline
        points={mainPoints}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* End dot */}
      <circle
        cx={toX(data.length - 1)}
        cy={toY(data[data.length - 1])}
        r="3"
        fill={color}
      />

      {/* Labels */}
      {labels && labels.length > 0 && (
        <>
          <text x="2" y={h - 2} fontSize="9" fill="#6b7280" opacity="0.6">{labels[0]}</text>
          <text x={w - 2} y={h - 2} fontSize="9" fill="#6b7280" opacity="0.6" textAnchor="end">{labels[labels.length - 1]}</text>
        </>
      )}
    </svg>
  );
}
