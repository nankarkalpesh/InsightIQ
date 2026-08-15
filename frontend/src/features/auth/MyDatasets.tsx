import React, { useState, useEffect } from 'react';
import { Database, Calendar, Layers, ArrowRight, Loader2, RefreshCw, AlertCircle, FileSpreadsheet, PlusCircle } from 'lucide-react';
import { useDataset } from '../../store/datasetStore';
import { getUserDatasetsApi, resumeUserDatasetApi, type UserDatasetItem, type DatasetMetadataResponse } from '../../lib/api';

interface MyDatasetsProps {
  onNavigateToOverview: () => void;
  onNavigateToUpload: () => void;
}

export const MyDatasets: React.FC<MyDatasetsProps> = ({
  onNavigateToOverview,
  onNavigateToUpload
}) => {
  const { setDataset } = useDataset();
  const [datasets, setDatasets] = useState<UserDatasetItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [resumingFileId, setResumingFileId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchUserDatasets = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await getUserDatasetsApi();
      setDatasets(res.datasets || []);
    } catch (err: any) {
      console.error('Failed to load user datasets:', err);
      setErrorMsg(err?.message || 'Could not fetch your dataset history.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUserDatasets();
  }, []);

  const handleResumeDataset = async (datasetItem: UserDatasetItem) => {
    setResumingFileId(datasetItem.file_id);
    setErrorMsg(null);

    try {
      const res = await resumeUserDatasetApi(datasetItem.file_id);
      
      // Save dashboard items if available
      if (res.dashboard_config && Array.isArray(res.dashboard_config)) {
        try {
          localStorage.setItem(`insightiq_dashboard_${datasetItem.file_id}`, JSON.stringify(res.dashboard_config));
        } catch (e) {
          console.warn('Could not save resumed dashboard config:', e);
        }
      }

      // Reconstruct DatasetMetadataResponse for datasetStore
      const meta: DatasetMetadataResponse = {
        file_id: res.dataset.file_id,
        filename: datasetItem.filename,
        file_type: datasetItem.file_type.replace('.', '') || 'csv',
        file_size: 0,
        row_count: datasetItem.row_count,
        column_count: datasetItem.column_count,
        columns: res.dataset.schema ? res.dataset.schema.map((s) => ({ name: s.name, dtype: s.dtype })) : [],
        requires_sheet_selection: false
      };

      setDataset(meta);
      onNavigateToOverview();
    } catch (err: any) {
      console.error('Failed to resume dataset session:', err);
      setErrorMsg(err?.message || 'Failed to resume dataset session.');
    } finally {
      setResumingFileId(null);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto py-6 px-4 md:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-display-xs md:text-display-sm text-ink font-bold tracking-tight">
            My Saved Datasets
          </h1>
          <p className="text-body-sm text-muted">
            Access and resume your past uploaded datasets, dashboards, and ML runs.
          </p>
        </div>

        <button
          onClick={onNavigateToUpload}
          className="btn-primary gap-2 self-start sm:self-auto cursor-pointer"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Upload New Dataset</span>
        </button>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="mb-6 p-4 rounded-xl border border-error/30 bg-error-bg/60 text-error text-body-sm flex items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-error" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={fetchUserDatasets}
            className="inline-flex items-center gap-1.5 text-caption font-semibold underline underline-offset-2 hover:opacity-80 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="py-16 text-center space-y-3">
          <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" />
          <p className="text-body-sm text-muted font-medium">Fetching dataset history...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && datasets.length === 0 && (
        <div className="rounded-2xl border border-dashed border-hairline p-12 text-center bg-surface-card max-w-lg mx-auto space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-primary-light/60 border border-primary/20 flex items-center justify-center text-primary mx-auto">
            <FileSpreadsheet className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-title-md text-ink font-semibold">No saved datasets yet</h3>
            <p className="text-body-sm text-muted mt-1">
              Datasets uploaded while logged into your account will automatically appear here for easy session restoration.
            </p>
          </div>
          <button
            onClick={onNavigateToUpload}
            className="btn-primary gap-2 mx-auto cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Upload Your First Dataset</span>
          </button>
        </div>
      )}

      {/* Dataset Grid */}
      {!isLoading && datasets.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {datasets.map((item) => {
            const isResuming = resumingFileId === item.file_id;
            const formattedDate = item.uploaded_at
              ? new Date(item.uploaded_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric'
                })
              : 'Recently uploaded';

            return (
              <div
                key={item.file_id}
                className="rounded-2xl border border-hairline bg-surface-card p-5 shadow-2xs hover:shadow-md hover:border-primary/50 transition-all duration-200 flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="w-10 h-10 rounded-xl bg-primary-light/60 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                      <Database className="w-5 h-5" />
                    </div>
                    <span className="px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-canvas text-muted border border-hairline uppercase">
                      {item.file_type.replace('.', '')}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-title-sm font-semibold text-ink truncate" title={item.filename}>
                      {item.filename}
                    </h3>
                    <div className="flex items-center gap-3 text-caption text-muted mt-1">
                      <span className="flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5" />
                        {item.row_count !== undefined && item.row_count !== null ? item.row_count.toLocaleString() : 0} rows
                      </span>
                      <span>•</span>
                      <span>{item.column_count || 0} cols</span>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-hairline flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-caption text-muted-soft">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>{formattedDate}</span>
                  </div>

                  <button
                    onClick={() => handleResumeDataset(item)}
                    disabled={isResuming}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-caption font-semibold bg-primary text-white hover:bg-primary-hover transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
                  >
                    {isResuming ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Resuming...</span>
                      </>
                    ) : (
                      <>
                        <span>Resume</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
