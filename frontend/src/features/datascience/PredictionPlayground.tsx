import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  RotateCcw,
  Brain,
  AlertTriangle,
  ArrowLeft,
  Sliders,
  Target,
  BarChart3
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

import {
  predictWithModel,
  fetchFeatureCandidates,
  type PredictResponse,
  type FeatureCandidate
} from '../../lib/api';
import { useDataset } from '../../store/datasetStore';
import { useDSStore } from '../../store/dsStore';

interface PredictionPlaygroundProps {
  onNavigateToTraining?: () => void;
}

export const PredictionPlayground: React.FC<PredictionPlaygroundProps> = ({
  onNavigateToTraining
}) => {
  const { dataset } = useDataset();
  const fileId = dataset ? dataset.file_id : null;
  const { trainingResult } = useDSStore();

  const [featureMetadata, setFeatureMetadata] = useState<Record<string, FeatureCandidate>>({});
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [predicting, setPredicting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);

  // Load feature metadata (distinct values & stats) when trainingResult is available
  useEffect(() => {
    if (!fileId || !trainingResult) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchFeatureCandidates(fileId, trainingResult.target)
      .then((data) => {
        if (isMounted) {
          const map: Record<string, FeatureCandidate> = {};
          (data.features || []).forEach((f) => {
            map[f.name || f.column] = f;
          });
          setFeatureMetadata(map);

          // Initialize default inputs
          const initInputs: Record<string, string> = {};
          const trainedFeatures = trainingResult.feature_importance.map((f) => f.feature);

          trainedFeatures.forEach((featName) => {
            const meta = map[featName];
            if (meta) {
              if (meta.is_categorical && meta.distinct_values && meta.distinct_values.length > 0) {
                initInputs[featName] = meta.distinct_values[0];
              } else if (meta.mean_val != null) {
                initInputs[featName] = String(meta.mean_val);
              } else if (meta.min_val != null) {
                initInputs[featName] = String(meta.min_val);
              } else {
                initInputs[featName] = '0';
              }
            } else {
              initInputs[featName] = '';
            }
          });

          setInputs(initInputs);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn('Failed to load feature candidates metadata:', err);
          // Fallback initialization
          const initInputs: Record<string, string> = {};
          trainingResult.feature_importance.forEach((f) => {
            initInputs[f.feature] = '';
          });
          setInputs(initInputs);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [fileId, trainingResult?.training_run_id]);

  if (!trainingResult) {
    return (
      <div className="w-full max-w-3xl mx-auto py-16 px-6 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mx-auto shadow-xs">
          <Brain className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-title-lg font-bold text-ink">Model Training Required</h3>
          <p className="text-body-md text-muted max-w-md mx-auto">
            Please train a model first in <strong>Training & Evaluation</strong> before using the interactive Prediction Playground.
          </p>
        </div>
        {onNavigateToTraining && (
          <button
            onClick={onNavigateToTraining}
            className="px-6 py-3 bg-purple-600 text-white rounded-xl font-semibold text-sm hover:bg-purple-700 shadow-xs transition-colors flex items-center gap-2 mx-auto cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Go to Model Training</span>
          </button>
        )}
      </div>
    );
  }

  const { training_run_id, target, model_name, problem_type, feature_importance } = trainingResult;
  const trainedFeatures = feature_importance.map((f) => f.feature);
  const isClassification = problem_type.includes('classification');

  const handleInputChange = (featureName: string, value: string) => {
    setInputs((prev) => ({
      ...prev,
      [featureName]: value,
    }));
  };

  const handleReset = () => {
    const resetValues: Record<string, string> = {};
    trainedFeatures.forEach((f) => {
      const meta = featureMetadata[f];
      if (meta && meta.is_categorical && meta.distinct_values && meta.distinct_values.length > 0) {
        resetValues[f] = meta.distinct_values[0];
      } else if (meta && meta.mean_val != null) {
        resetValues[f] = String(meta.mean_val);
      } else {
        resetValues[f] = '';
      }
    });
    setInputs(resetValues);
    setPrediction(null);
    setError(null);
  };

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileId) return;

    // Check missing inputs
    const missing = trainedFeatures.filter(
      (f) => inputs[f] === undefined || inputs[f] === null || String(inputs[f]).trim() === ''
    );

    if (missing.length > 0) {
      setError(`Please fill in required feature value(s): ${missing.join(', ')}`);
      return;
    }

    setPredicting(true);
    setError(null);

    try {
      const res = await predictWithModel(fileId, training_run_id, inputs);
      setPrediction(res);
      setPredicting(false);
    } catch (err: any) {
      setError(err.message || 'Prediction failed.');
      setPredicting(false);
    }
  };

  // Extract top class probability if available
  const topProbability = prediction?.probabilities && prediction.probabilities.length > 0
    ? (prediction.probabilities[0].probability * 100).toFixed(1)
    : null;

  return (
    <div className="w-full space-y-6 max-w-5xl mx-auto">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-purple-500/10 via-purple-500/5 to-transparent border border-purple-500/20">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 font-semibold text-sm">
            <Sparkles className="w-4 h-4" />
            <span>Interactive Prediction Playground</span>
          </div>
          <h2 className="text-title-lg font-bold text-ink">Test Real-Time Predictions</h2>
          <p className="text-body-sm text-muted">
            Enter sample feature values to generate instant predictions using fitted <strong>{model_name}</strong>.
          </p>
        </div>

        <div className="shrink-0 flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface-card border border-hairline text-caption font-semibold text-ink shadow-xs">
          <Target className="w-4 h-4 text-purple-500" />
          <span>Target: <strong>{target}</strong></span>
        </div>
      </div>

      {/* Main Grid: Form Left, Results Right */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Left Column: Feature Inputs Form */}
        <div className="md:col-span-6 space-y-4">
          <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-hairline pb-3">
              <h3 className="text-title-sm font-bold text-ink flex items-center gap-2">
                <Sliders className="w-4 h-4 text-purple-500" />
                <span>Feature Inputs ({trainedFeatures.length})</span>
              </h3>
              <button
                type="button"
                onClick={handleReset}
                className="text-caption font-semibold text-muted hover:text-ink transition-colors flex items-center gap-1 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            </div>

            {loading ? (
              <div className="space-y-4 py-4 animate-pulse">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="space-y-1.5">
                    <div className="h-4 w-28 bg-surface-soft rounded-md" />
                    <div className="h-10 w-full bg-surface-soft rounded-xl" />
                  </div>
                ))}
              </div>
            ) : (
              <form onSubmit={handlePredict} className="space-y-4">
                {error && (
                  <div className="p-3.5 rounded-xl bg-error-bg border border-error-border text-error text-caption font-medium flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="space-y-3.5 max-h-[460px] overflow-y-auto pr-1">
                  {trainedFeatures.map((featName) => {
                    const meta = featureMetadata[featName];
                    const isCat = meta?.is_categorical;
                    const distinctValues = meta?.distinct_values || [];

                    return (
                      <div key={featName} className="space-y-1.5">
                        <div className="flex items-center justify-between text-caption">
                          <label htmlFor={`input-${featName}`} className="font-bold text-ink flex items-center gap-1.5">
                            <span>{featName}</span>
                            {isCat ? (
                              <span className="px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-700 dark:text-purple-300 text-[10px]">
                                Categorical
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-700 dark:text-sky-300 text-[10px]">
                                Numeric
                              </span>
                            )}
                          </label>
                          {meta && !isCat && meta.min_val != null && meta.max_val != null && (
                            <span className="text-muted text-[11px]">
                              Range: [{meta.min_val}, {meta.max_val}]
                            </span>
                          )}
                        </div>

                        {isCat && distinctValues.length > 0 ? (
                          <select
                            id={`input-${featName}`}
                            value={inputs[featName] || ''}
                            onChange={(e) => handleInputChange(featName, e.target.value)}
                            className="w-full px-3.5 py-2.5 rounded-xl bg-surface-soft border border-hairline text-ink font-medium text-sm focus:outline-none focus:border-purple-500 transition-all cursor-pointer"
                          >
                            {distinctValues.map((val) => (
                              <option key={val} value={val}>
                                {val}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            id={`input-${featName}`}
                            type={isCat ? 'text' : 'number'}
                            step="any"
                            placeholder={meta?.mean_val != null ? `e.g. ${meta.mean_val}` : 'Enter value...'}
                            value={inputs[featName] || ''}
                            onChange={(e) => handleInputChange(featName, e.target.value)}
                            className="w-full px-3.5 py-2.5 rounded-xl bg-surface-soft border border-hairline text-ink font-medium text-sm focus:outline-none focus:border-purple-500 transition-all"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>

                <button
                  type="submit"
                  disabled={predicting}
                  className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-bold text-sm rounded-xl shadow-xs transition-colors flex items-center justify-center gap-2 cursor-pointer mt-2"
                >
                  {predicting ? (
                    <>
                      <Sparkles className="w-4 h-4 animate-spin" />
                      <span>Generating Prediction...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Predict Target Value</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Right Column: Prediction Output Card */}
        <div className="md:col-span-6 space-y-4">
          {!prediction && !predicting && (
            <div className="h-full min-h-[380px] p-8 rounded-2xl bg-surface-card border border-hairline shadow-xs flex flex-col items-center justify-center text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shadow-xs">
                <Brain className="w-7 h-7" />
              </div>
              <div className="space-y-1">
                <h4 className="text-title-sm font-bold text-ink">Ready for Real-Time Inference</h4>
                <p className="text-body-sm text-muted max-w-xs mx-auto">
                  Adjust feature inputs on the left and click <strong>Predict Target Value</strong> to test model outputs.
                </p>
              </div>
            </div>
          )}

          {predicting && (
            <div className="h-full min-h-[380px] p-8 rounded-2xl bg-surface-card border border-hairline shadow-xs flex flex-col items-center justify-center text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-purple-500/20 text-purple-600 dark:text-purple-400 flex items-center justify-center animate-spin">
                <Sparkles className="w-6 h-6" />
              </div>
              <h4 className="text-title-sm font-bold text-ink">Computing Prediction...</h4>
            </div>
          )}

          {prediction && !predicting && (
            <div className="space-y-4 animate-fadeIn">
              {/* Classification Prediction Card */}
              {isClassification && prediction.predicted_class != null && (
                <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-5">
                  <div className="space-y-1">
                    <div className="text-caption font-bold uppercase tracking-wider text-muted">
                      Predicted Class ({target})
                    </div>
                    <div className="text-title-lg font-extrabold text-purple-600 dark:text-purple-400 flex items-center gap-3">
                      <span>{prediction.predicted_class}</span>
                      {topProbability && (
                        <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 text-caption font-bold">
                          {topProbability}% Confidence
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Probability Distribution Chart */}
                  {prediction.probabilities && prediction.probabilities.length > 0 && (
                    <div className="space-y-3 pt-3 border-t border-hairline">
                      <div className="flex items-center justify-between text-caption font-bold text-ink">
                        <span className="flex items-center gap-1.5">
                          <BarChart3 className="w-4 h-4 text-purple-500" />
                          <span>Class Probability Distribution</span>
                        </span>
                        <span className="text-muted">Ranked Probabilities</span>
                      </div>

                      <div className="h-56 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={prediction.probabilities.slice(0, 8)}
                            layout="vertical"
                            margin={{ top: 5, right: 30, left: 30, bottom: 5 }}
                          >
                            <XAxis
                              type="number"
                              domain={[0, 1]}
                              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                              stroke="currentColor"
                              className="text-caption text-muted"
                            />
                            <YAxis
                              type="category"
                              dataKey="label"
                              width={90}
                              stroke="currentColor"
                              className="text-caption font-semibold text-ink"
                            />
                            <Tooltip
                              formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`, 'Probability']}
                              contentStyle={{ borderRadius: '12px', background: 'var(--color-surface-card)', borderColor: 'var(--color-hairline)' }}
                            />
                            <Bar dataKey="probability" radius={[0, 6, 6, 0]}>
                              {prediction.probabilities.slice(0, 8).map((_, index) => (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={index === 0 ? '#9333ea' : index === 1 ? '#a855f7' : '#c084fc'}
                                />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Regression Prediction Card */}
              {!isClassification && prediction.predicted_value != null && (
                <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
                  <div className="space-y-1">
                    <div className="text-caption font-bold uppercase tracking-wider text-muted">
                      Predicted Value ({target})
                    </div>
                    <div className="text-title-lg font-extrabold text-purple-600 dark:text-purple-400">
                      {prediction.predicted_value.toLocaleString()}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
