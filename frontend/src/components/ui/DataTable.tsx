import { type ReactNode } from 'react';

export interface Column<T> {
  key: string;
  label: string;
  align?: 'left' | 'right' | 'center';
  render: (row: T, index: number) => ReactNode;
}

export default function DataTable<T>({
  columns,
  data,
  header,
  emptyIcon,
  emptyMessage,
}: {
  columns: Column<T>[];
  data: T[];
  header?: ReactNode;
  emptyIcon?: ReactNode;
  emptyMessage?: string;
}) {
  return (
    <div className="bg-syn-surface border border-syn-border rounded-lg overflow-hidden">
      {header && (
        <div className="px-4 py-3 border-b border-syn-border flex items-center justify-between">
          {header}
        </div>
      )}
      {data.length === 0 ? (
        <div className="px-5 py-10 text-center">
          {emptyIcon && <div className="mb-3 flex justify-center text-syn-text-tertiary">{emptyIcon}</div>}
          <p className="text-sm text-syn-text-secondary">{emptyMessage || 'No data'}</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[10px] font-bold uppercase tracking-[0.15em] text-syn-muted border-b border-syn-border">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`px-4 py-2.5 ${
                      col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                    }`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} className="border-b border-syn-border-subtle hover:bg-white/[0.02] transition-colors">
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-4 py-3 ${
                        col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                      }`}
                    >
                      {col.render(row, i)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
