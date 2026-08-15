import React, { useState, useMemo } from 'react';
import { ArrowUpDown, ChevronDown, ChevronUp, Table } from 'lucide-react';
import type { ColumnSchemaItem } from '../../lib/api';

interface SchemaTableProps {
  schema: ColumnSchemaItem[];
}

type SortField = 'name' | 'dtype' | 'unique_count' | 'null_count' | 'null_percentage';
type SortOrder = 'asc' | 'desc';

export const SchemaTable: React.FC<SchemaTableProps> = ({ schema }) => {
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const sortedSchema = useMemo(() => {
    return [...schema].sort((a, b) => {
      let aVal: any = a[sortField];
      let bVal: any = b[sortField];

      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [schema, sortField, sortOrder]);

  const getDtypeBadgeStyle = (dtype: string) => {
    const lower = dtype.toLowerCase();
    if (lower.includes('int') || lower.includes('float') || lower.includes('number')) {
      return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
    }
    if (lower.includes('date') || lower.includes('time')) {
      return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
    }
    if (lower.includes('bool')) {
      return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
    }
    return 'bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/20';
  };

  return (
    <div className="p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-light text-primary flex items-center justify-center">
            <Table className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-title-md text-ink font-bold">Column Schema & Types</h3>
            <p className="text-caption text-muted">
              {schema.length} columns detected with inferred types and null ratios
            </p>
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto border border-hairline rounded-xl max-h-96 overflow-y-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead className="bg-canvas sticky top-0 z-10 border-b border-hairline text-caption font-semibold text-muted">
            <tr>
              <th
                onClick={() => handleSort('name')}
                className="py-3 px-4 cursor-pointer hover:text-ink transition-colors select-none"
              >
                <div className="flex items-center gap-1.5">
                  <span>Column Name</span>
                  {sortField === 'name' ? (
                    sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                  ) : (
                    <ArrowUpDown className="w-3.5 h-3.5 text-muted-soft opacity-0 group-hover:opacity-100" />
                  )}
                </div>
              </th>

              <th
                onClick={() => handleSort('dtype')}
                className="py-3 px-4 cursor-pointer hover:text-ink transition-colors select-none"
              >
                <div className="flex items-center gap-1.5">
                  <span>Data Type</span>
                  {sortField === 'dtype' && (
                    sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </div>
              </th>

              <th
                onClick={() => handleSort('unique_count')}
                className="py-3 px-4 cursor-pointer hover:text-ink transition-colors text-right select-none"
              >
                <div className="flex items-center justify-end gap-1.5">
                  <span>Unique Values</span>
                  {sortField === 'unique_count' && (
                    sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </div>
              </th>

              <th
                onClick={() => handleSort('null_count')}
                className="py-3 px-4 cursor-pointer hover:text-ink transition-colors text-right select-none"
              >
                <div className="flex items-center justify-end gap-1.5">
                  <span>Missing (Null)</span>
                  {sortField === 'null_count' && (
                    sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </div>
              </th>

              <th className="py-3 px-4 text-left">Sample Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {sortedSchema.map((col) => (
              <tr key={col.name} className="hover:bg-surface-soft/60 transition-colors">
                <td className="py-3 px-4 font-mono font-medium text-ink truncate max-w-[200px]">
                  {col.name}
                </td>

                <td className="py-3 px-4 whitespace-nowrap">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold border ${getDtypeBadgeStyle(
                      col.dtype
                    )}`}
                  >
                    {col.dtype}
                  </span>
                </td>

                <td className="py-3 px-4 text-right font-mono text-ink">
                  {col.unique_count.toLocaleString()}
                </td>

                <td className="py-3 px-4 text-right font-mono">
                  <span className={col.null_count > 0 ? 'text-amber-600 dark:text-amber-400 font-semibold' : 'text-muted'}>
                    {col.null_count.toLocaleString()} ({col.null_percentage}%)
                  </span>
                </td>

                <td className="py-3 px-4 text-muted text-xs font-mono truncate max-w-[220px]">
                  {col.sample_value !== null && col.sample_value !== undefined
                    ? String(col.sample_value)
                    : <span className="italic text-muted-soft">null</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
