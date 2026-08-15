import React, { useEffect, useState } from 'react';
import {
  Target,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  Layers,
  BarChart2,
  HelpCircle,
  ArrowRight
} from 'lucide-react';
import { fetchTargetCandidates, type TargetCandidate } from '../../lib/api';
import { useDataset } from '../../store/datasetStore';
import { useDSStore } from '../../store/dsStore';

interface TargetSelectorProps {
  onTargetSelected?: (column: string) => void;
}

export const TargetSelector: React.FC<TargetSelectorProps> = ({ onTargetSelected }) => {
  const { dataset } = useDataset();
  const fileId = dataset ? dataset.file_id : null;
  const { selectedTarget, setTarget } = useDSStore();

  const [candidates, setCandidates] = useState<TargetCandidate[]>([]);
  const [executionTimeMs, setExecutionTimeMs] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isManualOpen, setIsManualOpen] = useState<boolean>(false);
  const [selectedCustomColumn, setSelectedCustomColumn] = useState<string>('');

  useEffect(() => {
    if (!fileId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchTargetCandidates(fileId)
      .then((data) => {
        if (isMounted) {
          // Sort candidates by rank_score descending
          const sorted = [...(data.candidates || [])].sort((a, b) => b.rank_score - a.rank_score);
          setCandidates(sorted);
          setExecutionTimeMs(data.execution_time_ms ?? null);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load target candidates.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [fileId]);

  const handleSelectTarget = (candidate: TargetCandidate) => {
    setTarget(candidate.column, candidate);
    if (onTargetSelected) {
      onTargetSelected(candidate.column);
    }
  };

  const handleSelectCustomTarget = (column: string) => {
    if (!column) return;
    setTarget(column, null);
    if (onTargetSelected) {
      onTargetSelected(column);
    }
  };

  // Get all columns from dataset metadata that are not candidate columns
  const allColumns = dataset?.columns?.map((c) => c.name) || [];
  const candidateColumnNames = new Set(candidates.map((c) => c.column));
  const otherColumns = allColumns.filter((col) => !candidateColumnNames.has(col));

  if (loading) {
    return (
      <div className="w-full space-y-6 py-6 max-w-5xl mx-auto">
        <div className="space-y-2">
          <div className="h-7 w-64 bg-surface-soft animate-pulse rounded-md" />
          <div className="h-4 w-96 bg-surface-soft animate-pulse rounded-md" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-64 rounded-2xl bg-surface-card border border-hairline p-6 animate-pulse space-y-4">
              <div className="flex justify-between items-center">
                <div className="h-6 w-36 bg-surface-soft rounded-md" />
                <div className="h-6 w-24 bg-surface-soft rounded-full" />
              </div>
              <div className="h-10 bg-surface-soft rounded-lg" />
              <div className="h-20 bg-surface-soft rounded-xl" />
              <div className="h-9 bg-surface-soft rounded-lg" />
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
          <h3 className="text-title-md text-ink">Failed to Load Target Candidates</h3>
          <p className="text-body-sm text-muted max-w-md mx-auto">{error}</p>
          <button
            onClick={() => {
              if (fileId) {
                setLoading(true);
                setError(null);
                fetchTargetCandidates(fileId)
                  .then((data) => {
                    setCandidates([...(data.candidates || [])].sort((a, b) => b.rank_score - a.rank_score));
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

  return (
    <div className="w-full space-y-8 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-primary/20">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-primary font-semibold text-sm">
            <Sparkles className="w-4 h-4" />
            <span>AI ML Target Analysis</span>
            {executionTimeMs !== null && (
              <span className="ml-2 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-caption font-bold flex items-center gap-1">
                <span>⚡ {executionTimeMs}ms</span>
              </span>
            )}
          </div>
          <h2 className="text-title-lg font-bold text-ink">Select Machine Learning Target</h2>
          <p className="text-body-sm text-muted">
            Choose the outcome column you want to predict. InsightIQ automatically evaluates column distributions, problem types, and rank scores.
          </p>
        </div>

        {selectedTarget && (
          <div className="shrink-0 flex items-center gap-3 bg-surface-card border border-primary/40 p-3.5 rounded-xl shadow-xs">
            <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Target className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">Selected Target</div>
              <div className="font-bold text-ink text-sm flex items-center gap-1.5">
                <span>{selectedTarget}</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Target Candidates Cards */}
      {candidates.length === 0 ? (
        <div className="p-8 rounded-2xl bg-surface-card border border-hairline text-center space-y-3">
          <HelpCircle className="w-10 h-10 text-muted mx-auto" />
          <h3 className="text-title-sm text-ink">No Recommended Machine Learning Targets Found</h3>
          <p className="text-body-sm text-muted max-w-md mx-auto">
            All columns in this dataset appear to be identifiers, spatial coordinates, or descriptions. You can manually select a target below.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {candidates.map((candidate, idx) => {
            const isSelected = selectedTarget === candidate.column;
            const isBinary = candidate.problem_type === 'binary_classification';
            const isMulti = candidate.problem_type === 'multiclass_classification';

            return (
              <div
                key={candidate.column}
                className={`
                  relative flex flex-col justify-between rounded-2xl p-6 transition-all duration-200 border
                  ${
                    isSelected
                      ? 'bg-primary/5 border-primary ring-2 ring-primary/40 shadow-md'
                      : 'bg-surface-card border-hairline hover:border-primary/40 hover:shadow-xs'
                  }
                `}
              >
                {/* Rank Badge Header */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-full bg-surface-soft text-muted font-bold text-caption border border-hairline">
                        #{idx + 1} Rank Score: {candidate.rank_score}
                      </span>
                    </div>

                    {/* Problem Type Badge */}
                    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-caption font-semibold border">
                      {isBinary && (
                        <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400 bg-blue-500/10 border-blue-500/20 px-2 py-0.5 rounded-full">
                          <Target className="w-3.5 h-3.5" />
                          <span>Binary Classification</span>
                        </span>
                      )}
                      {isMulti && (
                        <span className="flex items-center gap-1 text-purple-600 dark:text-purple-400 bg-purple-500/10 border-purple-500/20 px-2 py-0.5 rounded-full">
                          <Layers className="w-3.5 h-3.5" />
                          <span>Multiclass</span>
                        </span>
                      )}
                      {!isBinary && !isMulti && (
                        <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20 px-2 py-0.5 rounded-full">
                          <TrendingUp className="w-3.5 h-3.5" />
                          <span>Regression</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Column Name */}
                  <div>
                    <h3 className="text-title-md font-bold text-ink flex items-center gap-2">
                      <span>{candidate.column}</span>
                      {isSelected && <CheckCircle2 className="w-5 h-5 text-primary shrink-0" />}
                    </h3>
                    <p className="text-body-sm text-body mt-1 leading-relaxed">{candidate.reason}</p>
                  </div>

                  {/* Distribution Preview */}
                  <div className="p-4 rounded-xl bg-surface-soft/60 border border-hairline space-y-2.5">
                    <div className="flex items-center justify-between text-caption font-semibold text-muted">
                      <span className="flex items-center gap-1.5">
                        <BarChart2 className="w-3.5 h-3.5" />
                        <span>Distribution Preview</span>
                      </span>
                      <span>{candidate.unique_value_count} Classes</span>
                    </div>

                    {/* Categorical Distribution */}
                    {candidate.distribution && (isBinary || isMulti) && (
                      <div className="space-y-2">
                        {/* Mini bar representation */}
                        {(() => {
                          const total = Object.values(candidate.distribution).reduce(
                            (acc, curr) => acc + (typeof curr === 'number' ? curr : 0),
                            0
                          );
                          const entries = Object.entries(candidate.distribution);
                          return (
                            <>
                              <div className="h-3 w-full rounded-full bg-surface-soft overflow-hidden flex">
                                {entries.map(([clsName, count], i) => {
                                  const pct = total > 0 ? (Number(count) / total) * 100 : 0;
                                  const bgColors = [
                                    'bg-primary',
                                    'bg-purple-500',
                                    'bg-emerald-500',
                                    'bg-amber-500',
                                    'bg-sky-500',
                                  ];
                                  return (
                                    <div
                                      key={clsName}
                                      style={{ width: `${pct}%` }}
                                      className={`${bgColors[i % bgColors.length]} h-full transition-all duration-300`}
                                      title={`${clsName}: ${count} (${pct.toFixed(1)}%)`}
                                    />
                                  );
                                })}
                              </div>

                              {/* Class labels summary */}
                              <div className="flex flex-wrap gap-2 pt-1">
                                {entries.slice(0, 4).map(([clsName, count], i) => {
                                  const pct = total > 0 ? ((Number(count) / total) * 100).toFixed(0) : '0';
                                  const dotColors = [
                                    'bg-primary',
                                    'bg-purple-500',
                                    'bg-emerald-500',
                                    'bg-amber-500',
                                  ];
                                  return (
                                    <span
                                      key={clsName}
                                      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-surface-card border border-hairline text-caption text-ink font-medium"
                                    >
                                      <span className={`w-2 h-2 rounded-full ${dotColors[i % dotColors.length]}`} />
                                      <span className="truncate max-w-[100px]">{clsName}:</span>
                                      <span className="font-bold">{count} ({pct}%)</span>
                                    </span>
                                  );
                                })}
                                {entries.length > 4 && (
                                  <span className="text-caption text-muted self-center">
                                    +{entries.length - 4} more
                                  </span>
                                )}
                              </div>
                            </>
                          );
                        })()}
                      </div>
                    )}

                    {/* Regression Numeric Stats */}
                    {candidate.distribution && !isBinary && !isMulti && (
                      <div className="grid grid-cols-4 gap-2 pt-1">
                        <div className="bg-surface-card p-2 rounded-lg border border-hairline text-center">
                          <div className="text-[10px] text-muted font-semibold uppercase">Min</div>
                          <div className="text-caption font-bold text-ink">{candidate.distribution.min ?? 'N/A'}</div>
                        </div>
                        <div className="bg-surface-card p-2 rounded-lg border border-hairline text-center">
                          <div className="text-[10px] text-muted font-semibold uppercase">Max</div>
                          <div className="text-caption font-bold text-ink">{candidate.distribution.max ?? 'N/A'}</div>
                        </div>
                        <div className="bg-surface-card p-2 rounded-lg border border-hairline text-center">
                          <div className="text-[10px] text-muted font-semibold uppercase">Mean</div>
                          <div className="text-caption font-bold text-ink">{candidate.distribution.mean ?? 'N/A'}</div>
                        </div>
                        <div className="bg-surface-card p-2 rounded-lg border border-hairline text-center">
                          <div className="text-[10px] text-muted font-semibold uppercase">Std</div>
                          <div className="text-caption font-bold text-ink">{candidate.distribution.std ?? 'N/A'}</div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Data Quality Warning Note */}
                  {candidate.data_quality_note && (
                    <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-caption font-medium">
                      <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                      <span className="leading-snug">{candidate.data_quality_note}</span>
                    </div>
                  )}
                </div>

                {/* Footer Action Button */}
                <div className="pt-5 mt-4 border-t border-hairline">
                  <button
                    onClick={() => handleSelectTarget(candidate)}
                    className={`
                      w-full py-2.5 px-4 rounded-xl font-semibold text-sm transition-all duration-150 flex items-center justify-center gap-2 cursor-pointer
                      ${
                        isSelected
                          ? 'bg-primary text-white shadow-xs font-bold'
                          : 'bg-surface-soft hover:bg-primary hover:text-white text-ink border border-hairline'
                      }
                    `}
                  >
                    {isSelected ? (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Selected Target</span>
                      </>
                    ) : (
                      <>
                        <span>Use This Target</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Target Override Section */}
      <div className="rounded-2xl border border-hairline bg-surface-card overflow-hidden">
        <button
          onClick={() => setIsManualOpen(!isManualOpen)}
          className="w-full p-5 flex items-center justify-between hover:bg-surface-soft/40 transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-surface-soft border border-hairline flex items-center justify-center text-muted">
              <Target className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-title-sm font-semibold text-ink">Choose a different column manually</h4>
              <p className="text-caption text-muted">Select any non-candidate column from the dataset as target</p>
            </div>
          </div>
          {isManualOpen ? <ChevronUp className="w-5 h-5 text-muted" /> : <ChevronDown className="w-5 h-5 text-muted" />}
        </button>

        {isManualOpen && (
          <div className="p-5 pt-2 border-t border-hairline bg-surface-soft/30 space-y-4">
            {otherColumns.length === 0 ? (
              <p className="text-body-sm text-muted">All columns in the dataset are already in the target candidates list.</p>
            ) : (
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <select
                  value={selectedCustomColumn}
                  onChange={(e) => setSelectedCustomColumn(e.target.value)}
                  className="flex-1 px-4 py-2.5 rounded-xl border border-hairline bg-surface-card text-ink text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/40"
                >
                  <option value="">-- Choose from {otherColumns.length} other columns --</option>
                  {otherColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>

                <button
                  disabled={!selectedCustomColumn}
                  onClick={() => handleSelectCustomTarget(selectedCustomColumn)}
                  className="px-5 py-2.5 rounded-xl bg-primary text-white font-semibold text-sm hover:bg-primary-active disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
                >
                  Use Custom Target
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
