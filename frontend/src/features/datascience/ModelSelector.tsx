import React, { useEffect, useState } from 'react';
import {
  Target,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Star,
  Brain,
  ArrowRight,
  TrendingUp,
  ShieldCheck
} from 'lucide-react';
import { fetchModelRecommendations, type ModelRecommendation } from '../../lib/api';
import { useDataset } from '../../store/datasetStore';
import { useDSStore } from '../../store/dsStore';

interface ModelSelectorProps {
  onNavigateToFeatures?: () => void;
  onNavigateToTarget?: () => void;
  onNavigateToTraining?: () => void;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  onNavigateToFeatures,
  onNavigateToTarget,
  onNavigateToTraining,
}) => {
  const { dataset } = useDataset();
  const fileId = dataset ? dataset.file_id : null;
  const { selectedTarget, selectedFeatures, selectedModel, setModel } = useDSStore();

  const [models, setModels] = useState<ModelRecommendation[]>([]);
  const [dataQualityNote, setDataQualityNote] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!fileId || !selectedTarget || selectedFeatures.size === 0) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    const featureList = Array.from(selectedFeatures);

    fetchModelRecommendations(fileId, selectedTarget, featureList)
      .then((data) => {
        if (isMounted) {
          const sorted = [...(data.recommendations || [])].sort(
            (a, b) => b.suitability_score - a.suitability_score
          );
          setModels(sorted);
          setDataQualityNote(data.data_quality_note || null);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load model recommendations.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [fileId, selectedTarget, selectedFeatures.size]);

  // Guard State: Target or Features missing
  if (!selectedTarget || selectedFeatures.size === 0) {
    return (
      <div className="w-full max-w-3xl mx-auto py-16 px-6 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mx-auto shadow-xs">
          <Brain className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-title-lg font-bold text-ink">Target & Features Required</h3>
          <p className="text-body-md text-muted max-w-md mx-auto">
            {!selectedTarget
              ? 'Please select a target variable first before generating machine learning model recommendations.'
              : 'Please select at least one predictive feature in Feature Engineering before evaluating machine learning models.'}
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-2">
          {!selectedTarget && onNavigateToTarget && (
            <button
              onClick={onNavigateToTarget}
              className="px-6 py-3 bg-primary text-white rounded-xl font-semibold text-sm hover:bg-primary-active shadow-xs transition-colors"
            >
              Go to Target Selection
            </button>
          )}
          {selectedTarget && onNavigateToFeatures && (
            <button
              onClick={onNavigateToFeatures}
              className="px-6 py-3 bg-primary text-white rounded-xl font-semibold text-sm hover:bg-primary-active shadow-xs transition-colors flex items-center gap-2"
            >
              <span>Go to Feature Engineering</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-72 rounded-2xl bg-surface-card border border-hairline p-6 animate-pulse space-y-4">
              <div className="flex justify-between items-center">
                <div className="h-6 w-40 bg-surface-soft rounded-md" />
                <div className="h-6 w-28 bg-surface-soft rounded-full" />
              </div>
              <div className="h-4 w-full bg-surface-soft rounded-full" />
              <div className="h-12 bg-surface-soft rounded-lg" />
              <div className="h-16 bg-surface-soft rounded-lg" />
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
          <h3 className="text-title-md text-ink">Failed to Load Model Recommendations</h3>
          <p className="text-body-sm text-muted max-w-md mx-auto">{error}</p>
          <button
            onClick={() => {
              if (fileId && selectedTarget) {
                setLoading(true);
                setError(null);
                fetchModelRecommendations(fileId, selectedTarget, Array.from(selectedFeatures))
                  .then((data) => {
                    const sorted = [...(data.recommendations || [])].sort(
                      (a, b) => b.suitability_score - a.suitability_score
                    );
                    setModels(sorted);
                    setDataQualityNote(data.data_quality_note || null);
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

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'from-emerald-500 to-teal-500 text-emerald-600 dark:text-emerald-400';
    if (score >= 75) return 'from-primary to-sky-500 text-primary';
    return 'from-amber-500 to-orange-500 text-amber-600 dark:text-amber-400';
  };

  return (
    <div className="w-full space-y-6 max-w-5xl mx-auto">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-purple-500/10 via-purple-500/5 to-transparent border border-purple-500/20">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 font-semibold text-sm">
            <Brain className="w-4 h-4" />
            <span>AI Model Recommendation Engine</span>
          </div>
          <h2 className="text-title-lg font-bold text-ink">Select Machine Learning Algorithm</h2>
          <p className="text-body-sm text-muted">
            Ranked algorithms tailored to target <strong>{selectedTarget}</strong> and {selectedFeatures.size} selected features.
          </p>
        </div>

        {selectedModel && (
          <div className="shrink-0 flex items-center gap-3 bg-surface-card border border-purple-500/30 p-3.5 rounded-xl shadow-xs">
            <div className="w-9 h-9 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">Active Model</div>
              <div className="font-bold text-ink text-sm flex items-center gap-1.5">
                <span>{selectedModel.model_name}</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
            </div>

            {onNavigateToTraining && (
              <button
                onClick={onNavigateToTraining}
                className="ml-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Train Model</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Small Dataset Quality Warning Note if present */}
      {dataQualityNote && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-sm font-medium">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-bold">Small Sample Size Warning</div>
            <p className="text-caption leading-relaxed">{dataQualityNote}</p>
          </div>
        </div>
      )}

      {/* Model Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {models.map((model, idx) => {
          const isSelected = selectedModel?.model_name === model.model_name;
          const isBaseline = model.recommended_for_baseline;
          const isRegression = model.problem_type === 'regression';

          return (
            <div
              key={model.model_name}
              className={`
                relative flex flex-col justify-between rounded-2xl p-6 transition-all duration-200 border
                ${
                  isSelected
                    ? 'bg-purple-500/5 border-purple-500 ring-2 ring-purple-500/40 shadow-md'
                    : 'bg-surface-card border-hairline hover:border-purple-500/40 hover:shadow-xs'
                }
              `}
            >
              <div className="space-y-4">
                {/* Header: Name, Rank & Badges */}
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2.5 py-0.5 rounded-full bg-surface-soft text-muted font-bold text-caption border border-hairline">
                        #{idx + 1} Rank
                      </span>

                      {/* Recommended Baseline Badge */}
                      {isBaseline && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-caption font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                          <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                          <span>Recommended Baseline</span>
                        </span>
                      )}

                      {/* User Selection Pill */}
                      {isSelected && (
                        <span className="px-2.5 py-0.5 rounded-full bg-purple-600 text-white text-[10px] font-bold uppercase tracking-wider">
                          Selected Choice
                        </span>
                      )}
                    </div>

                    <h3 className="text-title-md font-bold text-ink flex items-center gap-2 pt-1">
                      <span>{model.model_name}</span>
                      {isSelected && <CheckCircle2 className="w-5 h-5 text-purple-600 dark:text-purple-400 shrink-0" />}
                    </h3>
                  </div>

                  {/* Problem type indicator */}
                  <span className="shrink-0 px-2.5 py-1 rounded-full text-caption font-semibold border bg-surface-soft text-muted border-hairline flex items-center gap-1">
                    {isRegression ? <TrendingUp className="w-3.5 h-3.5 text-emerald-500" /> : <Target className="w-3.5 h-3.5 text-primary" />}
                    <span>{isRegression ? 'Regression' : 'Classification'}</span>
                  </span>
                </div>

                {/* Visual Suitability Score Bar */}
                <div className="p-3.5 rounded-xl bg-surface-soft/60 border border-hairline space-y-2">
                  <div className="flex items-center justify-between text-caption font-bold">
                    <span className="text-muted">Suitability Score</span>
                    <span className={`text-sm font-extrabold ${getScoreColor(model.suitability_score)}`}>
                      {model.suitability_score} / 100
                    </span>
                  </div>

                  <div className="h-2.5 w-full rounded-full bg-surface-soft overflow-hidden">
                    <div
                      style={{ width: `${Math.min(100, Math.max(0, model.suitability_score))}%` }}
                      className={`h-full bg-gradient-to-r ${getScoreColor(model.suitability_score)} transition-all duration-500 rounded-full`}
                    />
                  </div>
                </div>

                {/* "Why" Explanation */}
                <p className="text-body-sm text-ink leading-relaxed">{model.why}</p>

                {/* Advantages List */}
                <div className="space-y-1.5 pt-1">
                  <div className="text-caption font-bold text-ink flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Key Advantages</span>
                  </div>
                  <ul className="space-y-1">
                    {model.advantages.map((adv, i) => (
                      <li key={i} className="flex items-start gap-2 text-caption text-body">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{adv}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Limitations List */}
                <div className="space-y-1.5 pt-1">
                  <div className="text-caption font-bold text-ink flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    <span>Limitations & Trade-offs</span>
                  </div>
                  <ul className="space-y-1">
                    {model.limitations.map((lim, i) => (
                      <li key={i} className="flex items-start gap-2 text-caption text-muted">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                        <span>{lim}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-5 mt-4 border-t border-hairline">
                <button
                  onClick={() => setModel(model)}
                  className={`
                    w-full py-2.5 px-4 rounded-xl font-semibold text-sm transition-all duration-150 flex items-center justify-center gap-2 cursor-pointer
                    ${
                      isSelected
                        ? 'bg-purple-600 hover:bg-purple-700 text-white shadow-xs font-bold'
                        : 'bg-surface-soft hover:bg-purple-600 hover:text-white text-ink border border-hairline'
                    }
                  `}
                >
                  {isSelected ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Selected Model</span>
                    </>
                  ) : (
                    <>
                      <span>Select This Model</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
