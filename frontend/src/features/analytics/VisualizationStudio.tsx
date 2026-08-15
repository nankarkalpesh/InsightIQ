import React, { useState, useEffect, useMemo } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Loader2,
  Plus,
  RefreshCw,
  Search
} from 'lucide-react';
import { useDataset } from '../../store/datasetStore';
import { fetchDatasetCharts, ApiError, API_BASE_URL } from '../../lib/api';
import type { ChartRecommendationResponse } from '../../lib/api';
import { RenderedChartCard } from './RenderedChartCard';

export const VisualizationStudio: React.FC = () => {
  const { dataset, clearDataset } = useDataset();
  const [chartResponse, setChartResponse] = useState<ChartRecommendationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorDetails, setErrorDetails] = useState<{
    message: string;
    guidance: string;
  } | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadCharts = async () => {
    if (!dataset?.file_id) return;

    setLoading(true);
    setErrorDetails(null);

    try {
      const data = await fetchDatasetCharts(dataset.file_id);
      setChartResponse(data);
      setLoading(false);
    } catch (err: any) {
      console.error('Failed to load chart recommendations:', err);
      if (err instanceof ApiError) {
        setErrorDetails({
          message: err.message,
          guidance: err.userGuidance,
        });
      } else {
        setErrorDetails({
          message: err.message || 'Failed to load chart recommendations.',
          guidance: `Please check your connection to backend server at ${API_BASE_URL} and try again.`,
        });
      }
      setLoading(false);
    }
  };

  useEffect(() => {
    if (dataset?.file_id) {
      loadCharts();
    } else {
      setLoading(false);
    }
  }, [dataset?.file_id]);

  const filteredCharts = useMemo(() => {
    if (!chartResponse?.charts) return [];
    if (!searchQuery.trim()) return chartResponse.charts;

    const query = searchQuery.toLowerCase().trim();
    return chartResponse.charts.filter(
      (c) =>
        c.title.toLowerCase().includes(query) ||
        c.x_axis.toLowerCase().includes(query) ||
        c.y_axis.toLowerCase().includes(query) ||
        c.chart_type.toLowerCase().includes(query) ||
        c.reason.toLowerCase().includes(query)
    );
  }, [chartResponse, searchQuery]);

  if (!dataset) {
    return (
      <div className="w-full max-w-4xl mx-auto flex flex-col items-center justify-center min-h-[65vh] text-center p-8 rounded-2xl border border-dashed border-hairline bg-surface-soft/40 space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-primary-light text-primary flex items-center justify-center text-3xl font-bold shadow-xs">
          <BarChart3 className="w-8 h-8" />
        </div>
        <div className="space-y-1">
          <h2 className="text-title-lg text-ink font-bold">No Dataset Loaded</h2>
          <p className="text-body-md text-muted max-w-md mx-auto leading-relaxed">
            Upload a dataset to generate automated interactive chart visualizations tailored to your data.
          </p>
        </div>
        <div className="pt-2">
          <button onClick={clearDataset} className="btn-primary gap-2">
            <Plus className="w-4 h-4" />
            <span>Upload a Dataset</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary-light text-primary flex items-center justify-center shrink-0">
            <BarChart3 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-title-md text-ink font-bold">Visualization Studio</h2>
              {chartResponse && (
                <span className="px-2.5 py-0.5 text-xs font-semibold bg-primary-light text-primary rounded-full border border-primary/20">
                  {chartResponse.total_charts} Visualizations
                </span>
              )}
            </div>
            <p className="text-caption text-muted">
              Interactive charts and aggregate visualizations for {dataset.filename}
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search charts, axes, or types..."
            className="w-full h-9 pl-9 pr-3 bg-canvas border border-hairline rounded-lg text-sm text-ink outline-none focus:border-primary transition-colors"
          />
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="p-8 rounded-2xl border border-hairline bg-surface-card shadow-xs flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-primary animate-spin mb-4" />
          <h3 className="text-title-sm text-ink font-semibold mb-1">
            Analyzing Data & Generating Visualizations...
          </h3>
          <p className="text-body-sm text-muted">
            Evaluating column cardinalities, distributions, and optimal chart types.
          </p>
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
                Failed to Load Chart Recommendations
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
            <p className="text-body-sm text-body">{errorDetails.guidance}</p>
          </div>

          <button onClick={loadCharts} className="btn-primary gap-2">
            <RefreshCw className="w-4 h-4" />
            <span>Retry Fetching Charts</span>
          </button>
        </div>
      )}

      {/* Charts Grid */}
      {!loading && !errorDetails && chartResponse && (
        <>
          {chartResponse.message && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 text-sm font-medium">
              {chartResponse.message}
            </div>
          )}

          {filteredCharts.length === 0 ? (
            <div className="p-8 text-center border border-hairline rounded-2xl bg-surface-card text-muted text-sm">
              No charts found matching "{searchQuery}".
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {filteredCharts.map((chart) => (
                <RenderedChartCard
                  key={chart.title}
                  chartConfig={chart}
                  fileId={dataset.file_id}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};
