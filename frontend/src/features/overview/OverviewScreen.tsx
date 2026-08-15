import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  FileSpreadsheet,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { useDataset } from '../../store/datasetStore';
import { fetchDatasetOverview, ApiError, formatBytes, API_BASE_URL } from '../../lib/api';
import type { DatasetOverviewResponse } from '../../lib/api';
import { DatasetHealthCard } from './DatasetHealthCard';
import { SchemaTable } from './SchemaTable';
import { DataPreviewTable } from './DataPreviewTable';
import { InsightsList } from './InsightsList';

export const OverviewScreen: React.FC = () => {
  const { dataset, clearDataset } = useDataset();
  const [overview, setOverview] = useState<DatasetOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorDetails, setErrorDetails] = useState<{
    message: string;
    guidance: string;
  } | null>(null);

  const loadOverviewData = async () => {
    if (!dataset?.file_id) return;

    setLoading(true);
    setErrorDetails(null);

    try {
      const data = await fetchDatasetOverview(dataset.file_id);
      setOverview(data);
      setLoading(false);
    } catch (err: any) {
      console.error('Failed to fetch dataset overview:', err);
      if (err instanceof ApiError) {
        setErrorDetails({
          message: err.message,
          guidance: err.userGuidance
        });
      } else {
        setErrorDetails({
          message: err.message || 'Failed to load dataset overview.',
          guidance: `Please check your connection to backend at ${API_BASE_URL} and try again.`
        });
      }
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverviewData();
  }, [dataset?.file_id]);

  if (!dataset) {
    return null;
  }

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary-light text-primary flex items-center justify-center font-bold">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-title-md text-ink font-bold">{dataset.filename}</h2>
              {dataset.selected_sheet && (
                <span className="px-2.5 py-0.5 text-xs font-semibold bg-surface-soft text-primary rounded-full border border-hairline">
                  Sheet: {dataset.selected_sheet}
                </span>
              )}
            </div>
            <p className="text-caption text-muted">
              {formatBytes(dataset.file_size)} • Ingested & AI profiling complete
            </p>
          </div>
        </div>

        <button
          onClick={clearDataset}
          className="btn-secondary gap-2 text-sm shrink-0"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Upload New Dataset</span>
        </button>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-6">
          <div className="p-8 rounded-2xl border border-hairline bg-surface-card shadow-xs flex flex-col items-center justify-center min-h-[300px]">
            <Loader2 className="w-8 h-8 text-primary animate-spin mb-4" />
            <h3 className="text-title-sm text-ink font-semibold mb-1">
              Analyzing & Profiling Dataset...
            </h3>
            <p className="text-body-sm text-muted">
              Calculating statistical distributions, column quality scores, and factual insights.
            </p>
          </div>
        </div>
      )}

      {/* Error Display */}
      {errorDetails && !loading && (
        <div className="rounded-2xl border border-error/30 bg-error-bg/30 p-6 md:p-8 shadow-xs">
          <div className="flex items-start gap-4 mb-4">
            <div className="w-10 h-10 rounded-xl bg-error/15 text-error flex items-center justify-center shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-title-md text-error font-bold">
                Failed to Load Dataset Overview
              </h3>
              <p className="text-body-sm text-ink font-medium mt-1">
                {errorDetails.message}
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-surface-card border border-hairline mb-6">
            <div className="text-caption-uppercase text-muted font-bold mb-1">
              Remediation
            </div>
            <p className="text-body-sm text-body">
              {errorDetails.guidance}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadOverviewData}
              className="btn-primary gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry Fetching Overview</span>
            </button>
          </div>
        </div>
      )}

      {/* Real Profiling Overview Content */}
      {!loading && !errorDetails && overview && (
        <div className="space-y-6">
          {/* Health Audit Card */}
          <DatasetHealthCard health={overview.health} />

          {/* Factual Insights */}
          <InsightsList insights={overview.insights} />

          {/* Schema & Column Types */}
          <SchemaTable schema={overview.schema} />

          {/* Paginated Data Preview */}
          <DataPreviewTable fileId={dataset.file_id} />
        </div>
      )}
    </div>
  );
};
