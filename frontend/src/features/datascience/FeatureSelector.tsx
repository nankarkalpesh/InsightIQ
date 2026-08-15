import React, { useEffect, useState } from 'react';
import {
  Target,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  Clock,
  FileText,
  MapPin,
  Tag,
  Ban,
  UserX,
  Layers,
  RotateCcw,
  CheckSquare,
  Square
} from 'lucide-react';
import { fetchFeatureCandidates, type FeatureCandidate } from '../../lib/api';
import { useDataset } from '../../store/datasetStore';
import { useDSStore } from '../../store/dsStore';

interface FeatureSelectorProps {
  onNavigateToTarget?: () => void;
}

export const FeatureSelector: React.FC<FeatureSelectorProps> = ({ onNavigateToTarget }) => {
  const { dataset } = useDataset();
  const fileId = dataset ? dataset.file_id : null;
  const {
    selectedTarget,
    selectedFeatures,
    toggleFeature,
    setSelectedFeatures,
    selectAllRecommended,
    deselectAllFeatures,
  } = useDSStore();

  const [features, setFeatures] = useState<FeatureCandidate[]>([]);
  const [recommendedCount, setRecommendedCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isExcludedOpen, setIsExcludedOpen] = useState<boolean>(false);
  const [hasInitialized, setHasInitialized] = useState<boolean>(false);

  useEffect(() => {
    if (!fileId || !selectedTarget) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchFeatureCandidates(fileId, selectedTarget)
      .then((data) => {
        if (isMounted) {
          setFeatures(data.features || []);
          setRecommendedCount(data.recommended_count || 0);

          // Auto-select recommended features if not already set
          const recCols = (data.features || [])
            .filter((f) => f.status === 'recommended')
            .map((f) => f.column);

          if (selectedFeatures.size === 0 && !hasInitialized) {
            setSelectedFeatures(recCols);
            setHasInitialized(true);
          }

          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load feature candidates.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [fileId, selectedTarget]);

  // If no target is selected in dsStore
  if (!selectedTarget) {
    return (
      <div className="w-full max-w-3xl mx-auto py-16 px-6 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto shadow-xs">
          <Target className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-title-lg font-bold text-ink">Select a Target Column First</h3>
          <p className="text-body-md text-muted max-w-md mx-auto">
            Before configuring predictive features, choose which target column you want to model. InsightIQ will evaluate feature recommendations for that target.
          </p>
        </div>
        {onNavigateToTarget && (
          <button
            onClick={onNavigateToTarget}
            className="px-6 py-3 bg-primary text-white rounded-xl font-semibold text-sm hover:bg-primary-active shadow-xs transition-colors"
          >
            Go to Target Selection
          </button>
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="w-full space-y-6 py-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between">
          <div className="h-7 w-64 bg-surface-soft animate-pulse rounded-md" />
          <div className="h-9 w-40 bg-surface-soft animate-pulse rounded-xl" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div key={n} className="h-16 rounded-xl bg-surface-card border border-hairline p-4 animate-pulse flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-5 h-5 bg-surface-soft rounded-md" />
                <div className="h-5 w-40 bg-surface-soft rounded-md" />
              </div>
              <div className="h-6 w-32 bg-surface-soft rounded-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-4xl mx-auto py-12 px-6 text-center">
        <div className="p-8 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
          <div className="w-12 h-12 rounded-full bg-error-bg text-error flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-title-md text-ink">Failed to Load Feature Candidates</h3>
          <p className="text-body-sm text-muted max-w-md mx-auto">{error}</p>
          <button
            onClick={() => {
              if (fileId && selectedTarget) {
                setLoading(true);
                setError(null);
                fetchFeatureCandidates(fileId, selectedTarget)
                  .then((data) => {
                    setFeatures(data.features || []);
                    setRecommendedCount(data.recommended_count || 0);
                    setLoading(false);
                  })
                  .catch((e) => {
                    setError(e.message);
                    setLoading(false);
                  });
              }
            }}
            className="px-4 py-2 bg-primary text-white rounded-lg font-semibold text-sm hover:bg-primary-active transition-colors"
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  const recommendedFeatures = features.filter((f) => f.status === 'recommended');
  const excludedFeatures = features.filter((f) => f.status !== 'recommended');

  const selectedCount = selectedFeatures.size;

  const handleSelectAllRecommendedClick = () => {
    const recCols = recommendedFeatures.map((f) => f.column);
    selectAllRecommended(recCols);
  };

  const handleSelectAllClick = () => {
    const allCols = features.map((f) => f.column);
    setSelectedFeatures(allCols);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'recommended':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Recommended</span>
          </span>
        );
      case 'excluded_leakage':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Target Leakage</span>
          </span>
        );
      case 'excluded_identifier':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            <Tag className="w-3.5 h-3.5" />
            <span>Identifier</span>
          </span>
        );
      case 'excluded_identifier_like_name':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-pink-500/10 text-pink-600 dark:text-pink-400 border border-pink-500/20">
            <UserX className="w-3.5 h-3.5" />
            <span>Personal Name</span>
          </span>
        );
      case 'excluded_coordinate':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
            <MapPin className="w-3.5 h-3.5" />
            <span>Coordinates</span>
          </span>
        );
      case 'excluded_datetime':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
            <Clock className="w-3.5 h-3.5" />
            <span>Datetime</span>
          </span>
        );
      case 'excluded_free_text':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">
            <FileText className="w-3.5 h-3.5" />
            <span>Free Text</span>
          </span>
        );
      case 'excluded_high_cardinality':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Layers className="w-3.5 h-3.5" />
            <span>High Cardinality</span>
          </span>
        );
      case 'excluded_high_missing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">
            <Ban className="w-3.5 h-3.5" />
            <span>High Missing / Constant</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-semibold bg-surface-soft text-muted border border-hairline">
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="w-full space-y-6 max-w-5xl mx-auto">
      {/* Top Controls Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-primary/10 border border-primary/20 text-primary font-bold text-sm">
            <Target className="w-4 h-4 shrink-0" />
            <span>Target: {selectedTarget}</span>
          </div>

          <div className="flex items-center gap-2 text-caption font-semibold text-muted">
            <span>Total: <strong className="text-ink">{features.length}</strong></span>
            <span>•</span>
            <span>Recommended: <strong className="text-emerald-600 dark:text-emerald-400">{recommendedCount}</strong></span>
            <span>•</span>
            <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
              Selected: {selectedCount}
            </span>
          </div>
        </div>

        {/* Quick selection action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleSelectAllRecommendedClick}
            className="px-3 py-1.5 rounded-lg bg-surface-soft hover:bg-surface-soft/80 text-ink font-semibold text-xs border border-hairline transition-colors flex items-center gap-1.5 cursor-pointer"
            title="Check all AI-recommended features"
          >
            <CheckSquare className="w-3.5 h-3.5 text-emerald-500" />
            <span>Recommended ({recommendedCount})</span>
          </button>

          <button
            onClick={handleSelectAllClick}
            className="px-3 py-1.5 rounded-lg bg-surface-soft hover:bg-surface-soft/80 text-ink font-semibold text-xs border border-hairline transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <span>Select All</span>
          </button>

          <button
            onClick={deselectAllFeatures}
            className="px-3 py-1.5 rounded-lg bg-surface-soft hover:bg-surface-soft/80 text-muted hover:text-ink font-semibold text-xs border border-hairline transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Recommended Features List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-500" />
            <h3 className="text-title-sm font-bold text-ink">
              Recommended Features ({recommendedFeatures.length})
            </h3>
          </div>
          <span className="text-caption text-muted font-medium">Checked by default for modeling</span>
        </div>

        {recommendedFeatures.length === 0 ? (
          <div className="p-6 rounded-xl bg-surface-card border border-hairline text-center text-muted text-body-sm">
            No recommended features for this target. You can manually select features from the excluded section below.
          </div>
        ) : (
          <div className="space-y-2">
            {recommendedFeatures.map((feat) => {
              const isChecked = selectedFeatures.has(feat.column);

              return (
                <div
                  key={feat.column}
                  onClick={() => toggleFeature(feat.column)}
                  className={`
                    flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl transition-all duration-150 border cursor-pointer select-none
                    ${
                      isChecked
                        ? 'bg-surface-card border-hairline shadow-xs hover:border-primary/40'
                        : 'bg-surface-soft/30 border-hairline opacity-75 hover:opacity-100'
                    }
                  `}
                >
                  <div className="flex items-start sm:items-center gap-3.5 min-w-0">
                    <button
                      type="button"
                      className="mt-0.5 sm:mt-0 text-primary hover:text-primary-active shrink-0 cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFeature(feat.column);
                      }}
                    >
                      {isChecked ? (
                        <CheckSquare className="w-5 h-5 text-primary fill-primary/10" />
                      ) : (
                        <Square className="w-5 h-5 text-muted hover:text-ink" />
                      )}
                    </button>

                    <div className="space-y-0.5 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`font-bold text-sm ${isChecked ? 'text-ink' : 'text-muted line-through'}`}>
                          {feat.column}
                        </span>
                        {getStatusBadge(feat.status)}
                      </div>
                      <p className="text-caption text-muted truncate max-w-xl">{feat.reason}</p>
                    </div>
                  </div>

                  {/* Data Quality Note if present */}
                  {feat.data_quality_note && (
                    <div className="shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-caption font-medium max-w-md">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                      <span className="truncate">{feat.data_quality_note}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Excluded Features Section (Collapsible) */}
      <div className="rounded-2xl border border-hairline bg-surface-card overflow-hidden">
        <button
          onClick={() => setIsExcludedOpen(!isExcludedOpen)}
          className="w-full p-5 flex items-center justify-between hover:bg-surface-soft/40 transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-surface-soft border border-hairline flex items-center justify-center text-muted">
              <Ban className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-title-sm font-semibold text-ink">Excluded Features ({excludedFeatures.length})</h4>
                <span className="text-caption text-muted font-normal">(Collapsed by default)</span>
              </div>
              <p className="text-caption text-muted">
                Columns excluded due to identifiers, leakage, spatial coordinates, timestamps, or high cardinality.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {excludedFeatures.filter((f) => selectedFeatures.has(f.column)).length > 0 && (
              <span className="px-2.5 py-0.5 rounded-full bg-primary/10 text-primary font-bold text-caption">
                {excludedFeatures.filter((f) => selectedFeatures.has(f.column)).length} Manually Included
              </span>
            )}
            {isExcludedOpen ? <ChevronDown className="w-5 h-5 text-muted" /> : <ChevronRight className="w-5 h-5 text-muted" />}
          </div>
        </button>

        {isExcludedOpen && (
          <div className="p-5 pt-2 border-t border-hairline bg-surface-soft/20 space-y-3">
            <div className="text-caption font-semibold text-muted mb-2">
              PRD Control: You can manually check any excluded column to override the AI recommendation.
            </div>

            {excludedFeatures.length === 0 ? (
              <p className="text-body-sm text-muted">No features were excluded for this dataset.</p>
            ) : (
              <div className="space-y-2">
                {excludedFeatures.map((feat) => {
                  const isChecked = selectedFeatures.has(feat.column);

                  return (
                    <div
                      key={feat.column}
                      onClick={() => toggleFeature(feat.column)}
                      className={`
                        flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl transition-all duration-150 border cursor-pointer select-none
                        ${
                          isChecked
                            ? 'bg-primary/5 border-primary/40 shadow-xs'
                            : 'bg-surface-card border-hairline opacity-70 hover:opacity-100'
                        }
                      `}
                    >
                      <div className="flex items-start sm:items-center gap-3.5 min-w-0">
                        <button
                          type="button"
                          className="mt-0.5 sm:mt-0 text-primary shrink-0 cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleFeature(feat.column);
                          }}
                        >
                          {isChecked ? (
                            <CheckSquare className="w-5 h-5 text-primary fill-primary/10" />
                          ) : (
                            <Square className="w-5 h-5 text-muted hover:text-ink" />
                          )}
                        </button>

                        <div className="space-y-0.5 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`font-semibold text-sm ${isChecked ? 'text-ink font-bold' : 'text-muted'}`}>
                              {feat.column}
                            </span>
                            {getStatusBadge(feat.status)}
                            {isChecked && (
                              <span className="px-2 py-0.2 rounded-md bg-primary text-white text-[10px] font-bold uppercase tracking-wider">
                                Included
                              </span>
                            )}
                          </div>
                          <p className="text-caption text-muted leading-relaxed">{feat.reason}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
