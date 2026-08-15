import React, { useState, useEffect, useMemo } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Database,
  Loader2,
  Search
} from 'lucide-react';
import { fetchDatasetPreview, ApiError } from '../../lib/api';
import type { PaginatedPreviewResponse } from '../../lib/api';

interface DataPreviewTableProps {
  fileId: string;
}

export const DataPreviewTable: React.FC<DataPreviewTableProps> = ({ fileId }) => {
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);
  const [loading, setLoading] = useState<boolean>(true);
  const [previewData, setPreviewData] = useState<PaginatedPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchDatasetPreview(fileId, page, pageSize)
      .then((res) => {
        if (isMounted) {
          setPreviewData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof ApiError ? err.message : 'Failed to load dataset preview.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [fileId, page, pageSize]);

  // Extract columns list from preview records
  const columns = useMemo(() => {
    if (!previewData || previewData.data.length === 0) return [];
    return Object.keys(previewData.data[0]);
  }, [previewData]);

  // Client-side filter on loaded page records
  const filteredData = useMemo(() => {
    if (!previewData) return [];
    if (!searchQuery.trim()) return previewData.data;

    const query = searchQuery.toLowerCase().trim();
    return previewData.data.filter((row) =>
      Object.values(row).some((val) =>
        val !== null && val !== undefined && String(val).toLowerCase().includes(query)
      )
    );
  }, [previewData, searchQuery]);

  return (
    <div className="p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-light text-primary flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-title-md text-ink font-bold">Data Preview</h3>
            <p className="text-caption text-muted">
              Paginated view of raw dataset records ({previewData?.total_rows.toLocaleString() ?? 0} total rows)
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search loaded rows..."
            className="w-full h-9 pl-9 pr-3 bg-canvas border border-hairline rounded-lg text-sm text-ink outline-none focus:border-primary transition-colors"
          />
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="w-full h-64 border border-hairline rounded-xl flex items-center justify-center bg-canvas">
          <div className="flex items-center gap-3 text-muted text-sm font-medium">
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
            <span>Loading preview page {page}...</span>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="p-4 rounded-xl border border-error/30 bg-error-bg/30 text-error text-sm font-medium">
          {error}
        </div>
      )}

      {/* Preview Table */}
      {!loading && !error && previewData && (
        <>
          <div className="overflow-x-auto border border-hairline rounded-xl max-h-96 overflow-y-auto">
            {filteredData.length === 0 ? (
              <div className="p-8 text-center text-muted text-sm">
                No matching records found on page {page}.
              </div>
            ) : (
              <table className="w-full text-left text-sm border-collapse">
                <thead className="bg-canvas sticky top-0 z-10 border-b border-hairline text-caption font-semibold text-muted">
                  <tr>
                    <th className="py-3 px-3 w-12 text-center border-r border-hairline">#</th>
                    {columns.map((col) => (
                      <th key={col} className="py-3 px-4 whitespace-nowrap font-mono">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline">
                  {filteredData.map((row, idx) => {
                    const rowNumber = (page - 1) * pageSize + idx + 1;
                    return (
                      <tr key={idx} className="hover:bg-surface-soft/60 transition-colors">
                        <td className="py-2.5 px-3 text-center text-xs font-mono text-muted border-r border-hairline">
                          {rowNumber}
                        </td>
                        {columns.map((col) => {
                          const val = row[col];
                          return (
                            <td key={col} className="py-2.5 px-4 font-mono text-xs text-ink whitespace-nowrap max-w-xs truncate">
                              {val !== null && val !== undefined ? (
                                String(val)
                              ) : (
                                <span className="italic text-muted-soft">null</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <div className="flex items-center gap-2 text-caption text-muted">
              <span>Rows per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="h-8 px-2 bg-canvas border border-hairline rounded-md text-xs text-ink focus:border-primary outline-none"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span>
                Showing {Math.min((page - 1) * pageSize + 1, previewData.total_rows)} -{' '}
                {Math.min(page * pageSize, previewData.total_rows)} of {previewData.total_rows.toLocaleString()}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="p-1.5 rounded-md border border-hairline bg-surface-card text-ink disabled:opacity-40 disabled:cursor-not-allowed hover:bg-canvas transition-colors"
                title="Previous Page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <span className="text-caption font-semibold text-ink px-2">
                Page {page} of {previewData.total_pages || 1}
              </span>

              <button
                disabled={page >= previewData.total_pages}
                onClick={() => setPage((p) => Math.min(previewData.total_pages, p + 1))}
                className="p-1.5 rounded-md border border-hairline bg-surface-card text-ink disabled:opacity-40 disabled:cursor-not-allowed hover:bg-canvas transition-colors"
                title="Next Page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
