'use client';

import { Download } from 'lucide-react';
import { useCallback } from 'react';

interface ExportButtonProps {
  data: Record<string, unknown>[];
  headers?: { key: string; label: string }[];
  filename?: string;
  label?: string;
  className?: string;
}

export default function ExportButton({
  data,
  headers,
  filename = 'export',
  label = 'Export CSV',
  className,
}: ExportButtonProps) {
  const exportCSV = useCallback(() => {
    if (data.length === 0) return;

    // Determine columns
    const cols = headers || Object.keys(data[0]).map((key) => ({ key, label: key }));

    // Build CSV
    const headerRow = cols.map((c) => `"${c.label}"`).join(',');
    const rows = data.map((row) =>
      cols.map((c) => {
        const val = row[c.key];
        if (val === null || val === undefined) return '""';
        return `"${String(val).replace(/"/g, '""')}"`;
      }).join(',')
    );

    const csv = [headerRow, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();

    URL.revokeObjectURL(url);
  }, [data, headers, filename]);

  return (
    <button
      onClick={exportCSV}
      disabled={data.length === 0}
      className={
        className ||
        'inline-flex items-center gap-1.5 text-[10px] font-semibold text-syn-muted hover:text-syn-text bg-syn-elevated hover:bg-syn-surface px-3 py-1.5 rounded-lg border border-syn-border transition-colors disabled:opacity-40 disabled:cursor-not-allowed'
      }
      title="Export data as CSV"
    >
      <Download size={11} />
      {label}
    </button>
  );
}
