'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, Filter, Download, Check } from 'lucide-react';

// ── Types ──

export interface Column<T> {
  key: string;
  header: string;
  accessor: (row: T) => React.ReactNode;
  sortValue?: (row: T) => string | number;
  filterable?: boolean;
  align?: 'left' | 'right' | 'center';
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  pageSizeOptions?: number[];
  selectable?: boolean;
  exportable?: boolean;
  exportFilename?: string;
  onRowClick?: (row: T, index: number) => void;
  rowKey?: (row: T, index: number) => string;
  emptyMessage?: string;
}

// ── Component ──

export default function DataTable<T>({
  columns,
  data,
  pageSize: initialPageSize = 10,
  pageSizeOptions = [10, 25, 50, 100],
  selectable = false,
  exportable = false,
  exportFilename = 'export',
  onRowClick,
  rowKey,
  emptyMessage = 'No data available',
}: DataTableProps<T>) {
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  // Filter data
  const filtered = useMemo(() => {
    return data.filter((row) => {
      return Object.entries(filters).every(([key, filter]) => {
        if (!filter) return true;
        const col = columns.find((c) => c.key === key);
        if (!col) return true;
        const val = col.sortValue ? col.sortValue(row) : col.accessor(row);
        return String(val).toLowerCase().includes(filter.toLowerCase());
      });
    });
  }, [data, filters, columns]);

  // Sort data
  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    const col = columns.find((c) => c.key === sortCol);
    if (!col || !col.sortValue) return filtered;
    return [...filtered].sort((a, b) => {
      const av = col.sortValue!(a);
      const bv = col.sortValue!(b);
      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sortCol, sortDir, columns]);

  // Paginate
  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);

  // Reset page when data changes
  useEffect(() => { setPage(0); }, [filters, sortCol, sortDir, pageSize]);

  const toggleSort = useCallback((key: string) => {
    const col = columns.find((c) => c.key === key);
    if (!col?.sortValue) return;
    if (sortCol === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortCol(key);
      setSortDir('asc');
    }
  }, [sortCol, columns]);

  const toggleSelect = useCallback((idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selected.size === paged.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(paged.map((_, i) => page * pageSize + i)));
    }
  }, [paged, page, pageSize, selected]);

  const exportCSV = useCallback(() => {
    const headers = columns.map((c) => c.header);
    const rows = sorted.map((row) =>
      columns.map((c) => {
        const val = c.sortValue ? c.sortValue(row) : c.accessor(row);
        return `"${String(val).replace(/"/g, '""')}"`;
      })
    );
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${exportFilename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [sorted, columns, exportFilename]);

  const alignClass = (align?: string) =>
    align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left';

  return (
    <div className="glass-card overflow-hidden">
      {/* Toolbar */}
      <div className="px-4 py-2.5 border-b border-white/[0.06] flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-[10px] text-syn-muted">
          <span>{sorted.length} rows</span>
          {selected.size > 0 && (
            <span className="text-syn-accent">{selected.size} selected</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1 text-[10px] px-2 py-1 rounded transition-colors ${
              showFilters ? 'bg-syn-accent/10 text-syn-accent' : 'text-syn-muted hover:text-syn-text hover:bg-white/[0.04]'
            }`}
          >
            <Filter size={10} /> Filters
          </button>
          {exportable && (
            <button
              onClick={exportCSV}
              className="flex items-center gap-1 text-[10px] text-syn-muted hover:text-syn-text px-2 py-1 rounded hover:bg-white/[0.04] transition-colors"
            >
              <Download size={10} /> CSV
            </button>
          )}
        </div>
      </div>

      {/* Table wrapper for horizontal scroll */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            {/* Headers */}
            <tr className="border-b border-white/[0.06]">
              {selectable && (
                <th className="px-4 py-2.5 w-10">
                  <button onClick={toggleSelectAll} className="w-4 h-4 rounded border border-syn-border flex items-center justify-center hover:border-syn-accent transition-colors">
                    {selected.size === paged.length && paged.length > 0 && <Check size={10} className="text-syn-accent" />}
                  </button>
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-syn-muted ${alignClass(col.align)} ${col.sortValue ? 'cursor-pointer select-none hover:text-syn-text transition-colors' : ''}`}
                  onClick={() => col.sortValue && toggleSort(col.key)}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortValue && (
                      sortCol === col.key
                        ? (sortDir === 'asc' ? <ArrowUp size={10} /> : <ArrowDown size={10} />)
                        : <ArrowUpDown size={10} className="opacity-30" />
                    )}
                  </span>
                </th>
              ))}
            </tr>

            {/* Filter row */}
            {showFilters && (
              <tr className="border-b border-white/[0.06] bg-white/[0.01]">
                {selectable && <th className="px-4 py-1.5" />}
                {columns.map((col) => (
                  <th key={col.key} className="px-4 py-1.5">
                    {col.filterable ? (
                      <input
                        type="text"
                        value={filters[col.key] || ''}
                        onChange={(e) => setFilters((prev) => ({ ...prev, [col.key]: e.target.value }))}
                        placeholder={`Filter ${col.header.toLowerCase()}...`}
                        className="w-full bg-syn-elevated text-[10px] text-syn-text placeholder:text-syn-text-tertiary rounded px-2 py-1 outline-none border border-syn-border focus:border-syn-accent transition-colors"
                      />
                    ) : null}
                  </th>
                ))}
              </tr>
            )}
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} className="px-4 py-8 text-center text-sm text-syn-muted">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paged.map((row, i) => {
                const globalIdx = page * pageSize + i;
                const key = rowKey ? rowKey(row, globalIdx) : String(globalIdx);
                const isSelected = selected.has(globalIdx);
                return (
                  <tr
                    key={key}
                    onClick={() => onRowClick?.(row, globalIdx)}
                    className={`border-b border-white/[0.03] transition-colors ${
                      isSelected ? 'bg-syn-accent/5' : 'hover:bg-white/[0.02]'
                    } ${onRowClick ? 'cursor-pointer' : ''}`}
                  >
                    {selectable && (
                      <td className="px-4 py-3 w-10">
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleSelect(globalIdx); }}
                          className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                            isSelected ? 'border-syn-accent bg-syn-accent/20' : 'border-syn-border hover:border-syn-accent'
                          }`}
                        >
                          {isSelected && <Check size={10} className="text-syn-accent" />}
                        </button>
                      </td>
                    )}
                    {columns.map((col) => (
                      <td key={col.key} className={`px-4 py-3 text-sm ${alignClass(col.align)} ${col.className || ''}`}>
                        {col.accessor(row)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-4 py-2.5 border-t border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-syn-muted">Rows:</span>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
            className="bg-syn-elevated text-[10px] text-syn-text rounded px-2 py-1 border border-syn-border outline-none cursor-pointer"
          >
            {pageSizeOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-syn-muted">
            {sorted.length > 0 ? `${page * pageSize + 1}-${Math.min((page + 1) * pageSize, sorted.length)} of ${sorted.length}` : '0 of 0'}
          </span>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="p-1 rounded hover:bg-white/[0.04] disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-syn-muted"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="p-1 rounded hover:bg-white/[0.04] disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-syn-muted"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
