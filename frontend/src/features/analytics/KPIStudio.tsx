import React, { useState, useEffect, useMemo } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Gauge,
  Loader2,
  Plus,
  RefreshCw,
  Search
} from 'lucide-react';
import { useDataset } from '../../store/datasetStore';
import { fetchDatasetKPIs, ApiError, API_BASE_URL } from '../../lib/api';
import type { KPIRecommendationResponse } from '../../lib/api';
import { KPICard } from './KPICard';

export const KPIStudio: React.FC = () => {
  const { dataset, clearDataset } = useDataset();
  const [kpiResponse, setKpiResponse] = useState<KPIRecommendationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorDetails, setErrorDetails] = useState<{
    message: string;
    guidance: string;
  } | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const loadKPIs = async () => {
    if (!dataset?.file_id) return;

    setLoading(true);
    setErrorDetails(null);

    try {
      const data = await fetchDatasetKPIs(dataset.file_id);
      setKpiResponse(data);
      setLoading(false);
    } catch (err: any) {
      console.error('Failed to load KPIs:', err);
      if (err instanceof ApiError) {
        setErrorDetails({
          message: err.message,
          guidance: err.userGuidance,
        });
      } else {
        setErrorDetails({
          message: err.message || 'Failed to load KPI recommendations.',
          guidance: `Please check your connection to backend server at ${API_BASE_URL} and try again.`,
        });
      }
      setLoading(false);
    }
  };

  useEffect(() => {
    if (dataset?.file_id) {
      loadKPIs();
    } else {
      setLoading(false);
    }
  }, [dataset?.file_id]);

  const handleAddToDashboard = (kpiName: string) => {
    setToastMessage(`Added "${kpiName}" to your Dashboard!`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Filter KPIs by search query
  const filteredKPIs = useMemo(() => {
    if (!kpiResponse?.kpis) return [];
    if (!searchQuery.trim()) return kpiResponse.kpis;

    const query = searchQuery.toLowerCase().trim();
    return kpiResponse.kpis.filter((kpi) =>
      kpi.kpi_name.toLowerCase().includes(query) ||
      kpi.definition.toLowerCase().includes(query) ||
      kpi.dax.toLowerCase().includes(query) ||
      kpi.required_columns.some((c) => c.toLowerCase().includes(query))
    );
  }, [kpiResponse, searchQuery]);

  // Empty state if no dataset is loaded yet
  if (!dataset) {
    return (
      <div className="w-full max-w-4xl mx-auto flex flex-col items-center justify-center min-h-[65vh] text-center p-8 rounded-2xl border border-dashed border-hairline bg-surface-soft/40 space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-primary-light text-primary flex items-center justify-center text-3xl font-bold shadow-xs">
          <Gauge className="w-8 h-8" />
        </div>
        <div className="space-y-1">
          <h2 className="text-title-lg text-ink font-bold">No Dataset Loaded</h2>
          <p className="text-body-md text-muted max-w-md mx-auto leading-relaxed">
            Upload a dataset to generate automated schema-driven KPI measures and DAX expressions tailored to your data.
          </p>
        </div>
        <div className="pt-2">
          <button
            onClick={clearDataset}
            className="btn-primary gap-2"
          >
            <Plus className="w-4 h-4" />
            <span>Upload a Dataset</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-900 text-white shadow-xl border border-slate-700 animate-in slide-in-from-bottom duration-200">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary-light text-primary flex items-center justify-center shrink-0">
            <Gauge className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-title-md text-ink font-bold">KPI Studio & DAX Measures</h2>
              {kpiResponse && (
                <span className="px-2.5 py-0.5 text-xs font-semibold bg-primary-light text-primary rounded-full border border-primary/20">
                  {kpiResponse.total_kpis} Recommended
                </span>
              )}
            </div>
            <p className="text-caption text-muted">
              Schema-driven automated metrics for {dataset.filename}
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
            placeholder="Search KPIs, DAX, or columns..."
            className="w-full h-9 pl-9 pr-3 bg-canvas border border-hairline rounded-lg text-sm text-ink outline-none focus:border-primary transition-colors"
          />
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-6">
          <div className="p-8 rounded-2xl border border-hairline bg-surface-card shadow-xs flex flex-col items-center justify-center min-h-[300px]">
            <Loader2 className="w-8 h-8 text-primary animate-spin mb-4" />
            <h3 className="text-title-sm text-ink font-semibold mb-1">
              Generating Recommended KPIs & DAX Measures...
            </h3>
            <p className="text-body-sm text-muted">
              Scanning schema columns, evaluating statistical measures, and computing values.
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
                Failed to Load KPI Recommendations
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
              onClick={loadKPIs}
              className="btn-primary gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry Fetching KPIs</span>
            </button>
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      {!loading && !errorDetails && kpiResponse && (
        <>
          {kpiResponse.message && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 text-sm font-medium">
              {kpiResponse.message}
            </div>
          )}

          {filteredKPIs.length === 0 ? (
            <div className="p-8 text-center border border-hairline rounded-2xl bg-surface-card text-muted text-sm">
              No KPIs found matching "{searchQuery}".
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredKPIs.map((kpi) => (
                <KPICard
                  key={kpi.kpi_name}
                  kpi={kpi}
                  onAddToDashboard={handleAddToDashboard}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};
