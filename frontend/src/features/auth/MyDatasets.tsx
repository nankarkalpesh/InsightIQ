import React, { useState, useEffect } from 'react';
import {
  Database,
  Clock,
  MessageSquare,
  BarChart2,
  Brain,
  Trash2,
  ShieldAlert,
  RefreshCw,
  FolderKanban,
  PlusCircle,
  ArrowRight,
  Loader2
} from 'lucide-react';
import {
  getUserDatasetsApi,
  deleteUserDatasetApi,
  resumeUserDatasetApi,
  formatBytes,
  type UserDatasetItem,
  type DatasetMetadataResponse
} from '../../lib/api';
import { useDataset } from '../../store/datasetStore';
import { useAuth } from '../../store/authStore';

interface MyDatasetsProps {
  onNavigateToOverview?: () => void;
  onNavigateToUpload?: () => void;
}

export const MyDatasets: React.FC<MyDatasetsProps> = ({
  onNavigateToOverview,
  onNavigateToUpload
}) => {
  const { user } = useAuth();
  const { setDataset } = useDataset();

  const [activities, setActivities] = useState<UserDatasetItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<UserDatasetItem | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchActivities = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getUserDatasetsApi(true);
      setActivities(res.datasets || []);
    } catch (err: any) {
      console.error('Failed to fetch user saved datasets:', err);
      setError(err?.message || 'Failed to load saved datasets');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchActivities();
    }
  }, [user]);

  const handleOpenActivity = async (item: UserDatasetItem) => {
    setOpeningId(item.file_id);
    setError(null);
    try {
      const res = await resumeUserDatasetApi(item.file_id);
      const userId = user?.id;
      const fid = item.file_id;

      // 1. Save dashboard items if available
      if (res.dashboard_config && Array.isArray(res.dashboard_config)) {
        try {
          const dashKey = userId ? `insightiq_u_${userId}_dashboard_${fid}` : `insightiq_guest_dashboard_${fid}`;
          localStorage.setItem(dashKey, JSON.stringify(res.dashboard_config));
        } catch (e) {
          console.warn('Could not save resumed dashboard config:', e);
        }
      }

      // 2. Save training run / DS selections if available
      if (res.training_runs && res.training_runs.length > 0) {
        try {
          const latestRun = res.training_runs[0];
          const dsKey = userId ? `insightiq_u_${userId}_ds_store_${fid}` : `insightiq_guest_ds_store_${fid}`;
          const dsPayload = {
            selectedTarget: latestRun.target_column,
            selectedTargetCandidate: null,
            isCustomTarget: true,
            selectedFeatures: latestRun.features || [],
            featureSelections: (latestRun.features || []).reduce((acc: any, f: string) => {
              acc[f] = true;
              return acc;
            }, {}),
            selectedModel: latestRun.model_name
              ? { model_name: latestRun.model_name, display_name: latestRun.model_name }
              : null,
            trainingResult: latestRun.metrics ? { metrics: latestRun.metrics, model_name: latestRun.model_name } : null
          };
          localStorage.setItem(dsKey, JSON.stringify(dsPayload));
        } catch (e) {
          console.warn('Could not save resumed DS state:', e);
        }
      }

      // 3. Save chat history if available
      if (res.chat_history && res.chat_history.length > 0) {
        try {
          const chatKey = userId ? `insightiq_u_${userId}_chat_session_${fid}` : `insightiq_guest_chat_session_${fid}`;
          const formattedMessages = res.chat_history.map((msg: any, idx: number) => ({
            id: `resumed-${idx}-${Date.now()}`,
            sender: msg.role === 'user' ? 'user' : 'assistant',
            text: msg.content || '',
            timestamp: 'Saved'
          }));
          const chatSessionData = {
            conversation_id: `resumed_${fid}`,
            messages: formattedMessages
          };
          localStorage.setItem(chatKey, JSON.stringify(chatSessionData));
        } catch (e) {
          console.warn('Could not save resumed chat history:', e);
        }
      }

      if (res && res.dataset) {
        const meta: DatasetMetadataResponse = {
          file_id: res.dataset.file_id,
          filename: item.filename,
          file_type: (item.file_type || 'csv').replace('.', ''),
          file_size: item.file_size || 0,
          row_count: res.dataset.health?.total_rows || item.row_count,
          column_count: res.dataset.health?.total_columns || item.column_count,
          columns: res.dataset.schema ? res.dataset.schema.map((s) => ({ name: s.name, dtype: s.dtype })) : [],
          requires_sheet_selection: false
        };
        setDataset(meta);

        if (onNavigateToOverview) {
          onNavigateToOverview();
        }
      }
    } catch (err: any) {
      console.error('Failed to open saved activity:', err);
      setError(err?.message || 'Unable to open saved dataset. Please re-upload if original file was removed.');
    } finally {
      setOpeningId(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteUserDatasetApi(deleteTarget.file_id);
      setActivities((prev) => prev.filter((a) => a.file_id !== deleteTarget.file_id));
      setDeleteTarget(null);
    } catch (err: any) {
      console.error('Failed to delete dataset activity:', err);
      alert(err?.message || 'Failed to delete saved activity');
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'N/A';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return isoString;
    }
  };

  if (!user) {
    return (
      <div className="w-full max-w-4xl mx-auto space-y-6 pb-12 animate-in fade-in duration-200">
        <div className="p-8 rounded-2xl bg-surface-card border border-hairline shadow-xs text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto border border-primary/20">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-ink tracking-tight">Authentication Required</h2>
          <p className="text-sm text-muted max-w-md mx-auto">
            Please log in or sign up for an InsightIQ account to save activities, restore dashboards, and manage your datasets across sessions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 pb-12 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-ink tracking-tight">My Saved Activities</h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-primary/10 text-primary rounded-full border border-primary/20">
              {activities.length} {activities.length === 1 ? 'Dataset' : 'Datasets'}
            </span>
          </div>
          <p className="text-sm text-muted mt-1">
            Access and resume your saved datasets, custom dashboards, ML models, and conversation history.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchActivities}
            disabled={isLoading}
            className="p-2 rounded-xl bg-surface-soft hover:bg-surface-hover text-muted hover:text-ink border border-hairline transition-colors cursor-pointer"
            title="Refresh Saved Activities"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-primary' : ''}`} />
          </button>
          {onNavigateToUpload && (
            <button
              onClick={onNavigateToUpload}
              className="px-4 py-2 rounded-xl bg-primary text-on-primary text-xs font-semibold hover:bg-primary-active transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Upload New Dataset</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((idx) => (
            <div key={idx} className="p-6 rounded-2xl bg-surface-card border border-hairline animate-pulse space-y-4">
              <div className="h-5 bg-surface-soft rounded-lg w-2/3" />
              <div className="h-4 bg-surface-soft rounded-lg w-1/2" />
              <div className="h-16 bg-surface-soft rounded-xl" />
            </div>
          ))}
        </div>
      ) : activities.length === 0 ? (
        /* Empty State */
        <div className="p-12 rounded-2xl bg-surface-card border border-dashed border-hairline text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-surface-soft text-muted flex items-center justify-center mx-auto border border-hairline">
            <FolderKanban className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-ink">No Saved Activities Yet</h3>
            <p className="text-xs text-muted max-w-sm mx-auto">
              When working on an uploaded dataset, click <strong className="text-ink">"Save Activity"</strong> in the top bar to persist your dataset, dashboard, and conversation history.
            </p>
          </div>
          {onNavigateToUpload && (
            <button
              onClick={onNavigateToUpload}
              className="px-4 py-2 rounded-xl bg-primary text-on-primary text-xs font-semibold hover:bg-primary-active transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Start Analyzing a Dataset</span>
            </button>
          )}
        </div>
      ) : (
        /* Dataset Activity Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {activities.map((item) => {
            const isOpening = openingId === item.file_id;
            return (
              <div
                key={item.file_id}
                className="p-5 rounded-2xl bg-surface-card border border-hairline hover:border-primary/40 transition-all duration-150 shadow-2xs flex flex-col justify-between space-y-4 group"
              >
                <div className="space-y-3">
                  {/* Card Title & Icon */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold border border-primary/20 shrink-0">
                        <Database className="w-5 h-5" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-sm font-bold text-ink truncate group-hover:text-primary transition-colors" title={item.activity_name || item.filename}>
                          {item.activity_name || item.filename}
                        </h3>
                        <p className="text-[11px] text-muted font-mono truncate mt-0.5">
                          {item.filename} ({item.file_size ? formatBytes(item.file_size) : item.file_type})
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Metadata Chips */}
                  <div className="flex items-center gap-2 text-[11px] text-muted">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-muted" />
                      <span>{formatDate(item.saved_at || item.uploaded_at)}</span>
                    </span>
                    <span>•</span>
                    <span>{item.row_count ? item.row_count.toLocaleString() : 0} rows</span>
                    <span>•</span>
                    <span>{item.column_count || 0} cols</span>
                  </div>

                  {/* Summary Badges */}
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div className="p-2 rounded-xl bg-surface-soft/60 border border-hairline flex flex-col items-center justify-center text-center">
                      <div className="flex items-center gap-1 text-[10px] text-muted font-medium">
                        <MessageSquare className="w-3 h-3 text-blue-500" />
                        <span>Chat</span>
                      </div>
                      <span className="text-xs font-bold text-ink mt-0.5">{item.chat_count || 0}</span>
                    </div>

                    <div className="p-2 rounded-xl bg-surface-soft/60 border border-hairline flex flex-col items-center justify-center text-center">
                      <div className="flex items-center gap-1 text-[10px] text-muted font-medium">
                        <BarChart2 className="w-3 h-3 text-emerald-500" />
                        <span>KPIs</span>
                      </div>
                      <span className="text-xs font-bold text-ink mt-0.5">{item.kpi_count || 0}</span>
                    </div>

                    <div className="p-2 rounded-xl bg-surface-soft/60 border border-hairline flex flex-col items-center justify-center text-center">
                      <div className="flex items-center gap-1 text-[10px] text-muted font-medium">
                        <Brain className="w-3 h-3 text-purple-500" />
                        <span>ML Runs</span>
                      </div>
                      <span className="text-xs font-bold text-ink mt-0.5">{item.ml_count || 0}</span>
                    </div>
                  </div>
                </div>

                {/* Actions Footer */}
                <div className="flex items-center justify-between pt-3 border-t border-hairline">
                  <button
                    onClick={() => setDeleteTarget(item)}
                    className="p-2 rounded-xl text-muted hover:text-red-600 dark:hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                    title="Delete Saved Activity"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => handleOpenActivity(item)}
                    disabled={isOpening}
                    className="px-3 py-1.5 rounded-xl bg-primary text-on-primary text-xs font-semibold hover:bg-primary-active transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs disabled:opacity-50"
                  >
                    {isOpening ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Opening...</span>
                      </>
                    ) : (
                      <>
                        <span>Open Activity</span>
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

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface-card border border-hairline rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center shrink-0 border border-red-500/20">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-ink">Delete Saved Activity?</h3>
                <p className="text-xs text-muted mt-0.5">Permanent action</p>
              </div>
            </div>

            <p className="text-xs text-muted leading-relaxed">
              Are you sure you want to delete <strong className="text-ink">{deleteTarget.activity_name || deleteTarget.filename}</strong>? Your persistent dataset file, dashboard KPIs, ML models, and conversation history will be permanently removed.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-hairline">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
                className="px-4 py-2 rounded-xl bg-surface-soft hover:bg-surface-hover text-ink text-xs font-semibold transition-colors cursor-pointer border border-hairline disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold transition-colors cursor-pointer shadow-xs flex items-center gap-1.5 disabled:opacity-50"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Permanently</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
