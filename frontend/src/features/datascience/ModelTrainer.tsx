import React, { useEffect, useState } from 'react';
import {
  Brain,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  RotateCcw,
  Sparkles,
  BarChart3,
  Clock,
  Database,
  ShieldAlert,
  Target,
  Download
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
  trainModel,
  getModelExportUrl,
  getPredictionsExportUrl,
  getMetricsExportUrl,
  getCodeExportUrl
} from '../../lib/api';
import { useDataset } from '../../store/datasetStore';
import { useDSStore } from '../../store/dsStore';

interface ModelTrainerProps {
  onNavigateToModels?: () => void;
  onNavigateToFeatures?: () => void;
  onNavigateToTarget?: () => void;
}

interface StepMessage {
  id: number;
  label: string;
  detail: string;
  status: 'pending' | 'running' | 'completed';
}

export const ModelTrainer: React.FC<ModelTrainerProps> = ({
  onNavigateToModels,
  onNavigateToFeatures: _onNavigateToFeatures,
  onNavigateToTarget: _onNavigateToTarget,
}) => {
  const { dataset } = useDataset();
  const fileId = dataset ? dataset.file_id : null;
  const {
    selectedTarget,
    selectedFeatures,
    selectedModel,
    trainingResult,
    setTrainingResult,
  } = useDSStore();

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Animated execution steps state
  const [steps, setSteps] = useState<StepMessage[]>([
    { id: 1, label: 'Data Preprocessing & Split', detail: 'Imputing missing values & 80/20 train/test split', status: 'pending' },
    { id: 2, label: 'Estimator Pipeline Training', detail: 'Fitting ColumnTransformer & model pipeline', status: 'pending' },
    { id: 3, label: 'Performance Evaluation', detail: 'Calculating test set metrics & feature importances', status: 'pending' },
  ]);

  const runTrainingPipeline = async () => {
    if (!fileId || !selectedTarget || selectedFeatures.size === 0 || !selectedModel) return;

    setLoading(true);
    setError(null);

    // Step 1: Preprocessing
    setSteps([
      { id: 1, label: 'Data Preprocessing & Split', detail: 'Imputing missing values & 80/20 train/test split', status: 'running' },
      { id: 2, label: 'Estimator Pipeline Training', detail: `Preparing ${selectedModel.model_name}...`, status: 'pending' },
      { id: 3, label: 'Performance Evaluation', detail: 'Calculating test set metrics & feature importances', status: 'pending' },
    ]);

    await new Promise((resolve) => setTimeout(resolve, 500));

    // Step 2: Fitting
    setSteps([
      { id: 1, label: 'Data Preprocessing & Split', detail: 'Imputing missing values & 80/20 train/test split', status: 'completed' },
      { id: 2, label: 'Estimator Pipeline Training', detail: `Fitting ${selectedModel.model_name} on training rows...`, status: 'running' },
      { id: 3, label: 'Performance Evaluation', detail: 'Calculating test set metrics & feature importances', status: 'pending' },
    ]);

    try {
      const featureList = Array.from(selectedFeatures);
      const data = await trainModel(fileId, selectedTarget, featureList, selectedModel.model_name);

      // Step 3: Evaluation & Completion
      setSteps([
        { id: 1, label: 'Data Preprocessing & Split', detail: 'Imputing missing values & 80/20 train/test split', status: 'completed' },
        { id: 2, label: 'Estimator Pipeline Training', detail: `Fitted ${selectedModel.model_name} successfully`, status: 'completed' },
        { id: 3, label: 'Performance Evaluation', detail: 'Computed accuracy, metrics & feature importances', status: 'running' },
      ]);

      await new Promise((resolve) => setTimeout(resolve, 400));

      setSteps([
        { id: 1, label: 'Data Preprocessing & Split', detail: 'Imputing missing values & 80/20 train/test split', status: 'completed' },
        { id: 2, label: 'Estimator Pipeline Training', detail: `Fitted ${selectedModel.model_name} successfully`, status: 'completed' },
        { id: 3, label: 'Performance Evaluation', detail: 'Evaluation complete', status: 'completed' },
      ]);

      setTrainingResult(data);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Model training failed.');
      setLoading(false);
    }
  };

  useEffect(() => {
    // Auto-trigger training if no result exists for current selection
    if (fileId && selectedTarget && selectedFeatures.size > 0 && selectedModel && !trainingResult && !loading && !error) {
      runTrainingPipeline();
    }
  }, [fileId, selectedTarget, selectedFeatures.size, selectedModel?.model_name]);

  // Guard State: Missing Target, Features, or Model Selection
  if (!selectedTarget || selectedFeatures.size === 0 || !selectedModel) {
    return (
      <div className="w-full max-w-3xl mx-auto py-16 px-6 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto shadow-xs">
          <Brain className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-title-lg font-bold text-ink">Model Selection Required</h3>
          <p className="text-body-md text-muted max-w-md mx-auto">
            {!selectedTarget
              ? 'Please select a target variable first.'
              : selectedFeatures.size === 0
              ? 'Please select at least one feature in Feature Engineering.'
              : 'Please select a machine learning algorithm in Model Selection to start training.'}
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-2">
          {!selectedModel && onNavigateToModels && (
            <button
              onClick={onNavigateToModels}
              className="px-6 py-3 bg-primary text-white rounded-xl font-semibold text-sm hover:bg-primary-active shadow-xs transition-colors flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Go to Model Selection</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  // Training Loading State with Animated Execution Steps
  if (loading) {
    return (
      <div className="w-full max-w-2xl mx-auto py-16 px-6 space-y-8">
        <div className="text-center space-y-2">
          <div className="w-14 h-14 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mx-auto shadow-xs animate-bounce">
            <Brain className="w-7 h-7" />
          </div>
          <h3 className="text-title-lg font-bold text-ink">Training {selectedModel.model_name}</h3>
          <p className="text-body-sm text-muted">
            Fitting pipeline on target <strong>{selectedTarget}</strong> with {selectedFeatures.size} features
          </p>
        </div>

        {/* Execution Steps */}
        <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
          {steps.map((step) => (
            <div key={step.id} className="flex items-start gap-4 p-3 rounded-xl bg-surface-soft/60">
              <div className="mt-0.5 shrink-0">
                {step.status === 'completed' && (
                  <div className="w-6 h-6 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                )}
                {step.status === 'running' && (
                  <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-600 dark:text-purple-400 flex items-center justify-center animate-spin">
                    <Sparkles className="w-3.5 h-3.5" />
                  </div>
                )}
                {step.status === 'pending' && (
                  <div className="w-6 h-6 rounded-full bg-surface-soft border border-hairline text-muted flex items-center justify-center text-caption font-bold">
                    {step.id}
                  </div>
                )}
              </div>
              <div className="space-y-0.5">
                <div className={`text-sm font-semibold ${step.status === 'running' ? 'text-purple-600 dark:text-purple-400 font-bold' : 'text-ink'}`}>
                  {step.label}
                </div>
                <div className="text-caption text-muted">{step.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="w-full max-w-3xl mx-auto py-12 px-6">
        <div className="p-8 rounded-2xl bg-surface-card border border-hairline shadow-xs text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-error-bg text-error flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-title-md font-bold text-ink">Model Training Error</h3>
          <p className="text-body-sm text-muted max-w-md mx-auto">{error}</p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              onClick={runTrainingPipeline}
              className="px-5 py-2.5 bg-primary text-white rounded-xl font-semibold text-sm hover:bg-primary-active transition-colors flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Retry Training</span>
            </button>
            {onNavigateToModels && (
              <button
                onClick={onNavigateToModels}
                className="px-5 py-2.5 bg-surface-soft border border-hairline text-ink rounded-xl font-semibold text-sm hover:bg-surface-card transition-colors"
              >
                Try Different Model
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!trainingResult) {
    return (
      <div className="w-full max-w-3xl mx-auto py-16 px-6 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mx-auto shadow-xs">
          <Brain className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-title-lg font-bold text-ink">Ready to Train {selectedModel.model_name}</h3>
          <p className="text-body-md text-muted max-w-md mx-auto">
            Target variable <strong>{selectedTarget}</strong> with {selectedFeatures.size} selected features.
          </p>
        </div>
        <button
          onClick={runTrainingPipeline}
          className="px-6 py-3 bg-purple-600 text-white rounded-xl font-bold text-sm hover:bg-purple-700 shadow-md transition-colors flex items-center gap-2 mx-auto cursor-pointer"
        >
          <Sparkles className="w-4 h-4" />
          <span>Train Selected Model</span>
        </button>
      </div>
    );
  }

  const {
    training_run_id,
    model_name,
    problem_type,
    classification_metrics,
    regression_metrics,
    feature_importance,
    training_time_seconds,
    train_row_count,
    test_row_count,
    data_quality_note,
  } = trainingResult;

  const isClassification = problem_type.includes('classification');

  return (
    <div className="w-full space-y-6 max-w-5xl mx-auto">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-purple-500/10 via-purple-500/5 to-transparent border border-purple-500/20">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 font-semibold text-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <span>Training & Evaluation Complete</span>
          </div>
          <h2 className="text-title-lg font-bold text-ink flex items-center gap-2">
            <span>{model_name} Results</span>
          </h2>
          <p className="text-body-sm text-muted">
            Evaluated on target <strong>{selectedTarget}</strong> with 80/20 train/test split.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {onNavigateToModels && (
            <button
              onClick={onNavigateToModels}
              className="px-4 py-2.5 bg-surface-card border border-hairline text-ink rounded-xl font-semibold text-sm hover:border-purple-500/40 hover:shadow-xs transition-all flex items-center gap-2 cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Try Different Model</span>
            </button>
          )}
          <button
            onClick={runTrainingPipeline}
            className="px-4 py-2.5 bg-purple-600 text-white rounded-xl font-semibold text-sm hover:bg-purple-700 shadow-xs transition-colors flex items-center gap-2 cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Retrain</span>
          </button>
        </div>
      </div>

      {/* Prominent Data Quality / Weak Model Warning Banner */}
      {data_quality_note && (
        <div className="flex items-start gap-3 p-5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 shadow-xs">
          <ShieldAlert className="w-6 h-6 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-sm uppercase tracking-wider text-amber-700 dark:text-amber-300">
              Data Quality & Performance Warning
            </div>
            <p className="text-body-sm font-medium leading-relaxed">{data_quality_note}</p>
          </div>
        </div>
      )}

      {/* Primary Metrics Grid */}
      {isClassification && classification_metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">Accuracy</div>
            <div className="text-title-lg font-extrabold text-purple-600 dark:text-purple-400">
              {(classification_metrics.accuracy * 100).toFixed(1)}%
            </div>
            {classification_metrics.baseline_accuracy != null && (
              <div className="text-[11px] text-muted font-medium">
                Baseline: {(classification_metrics.baseline_accuracy * 100).toFixed(1)}%
              </div>
            )}
            <div className="h-1.5 w-full bg-surface-soft rounded-full overflow-hidden mt-1">
              <div
                style={{ width: `${classification_metrics.accuracy * 100}%` }}
                className="h-full bg-purple-500 rounded-full"
              />
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">Precision</div>
            <div className="text-title-lg font-extrabold text-ink">
              {(classification_metrics.precision * 100).toFixed(1)}%
            </div>
            <div className="text-caption text-muted">Weighted avg</div>
          </div>

          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">Recall</div>
            <div className="text-title-lg font-extrabold text-ink">
              {(classification_metrics.recall * 100).toFixed(1)}%
            </div>
            <div className="text-caption text-muted">Weighted avg</div>
          </div>

          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">F1 Score</div>
            <div className="text-title-lg font-extrabold text-ink">
              {(classification_metrics.f1 * 100).toFixed(1)}%
            </div>
            <div className="text-caption text-muted">
              {classification_metrics.roc_auc != null ? `ROC-AUC: ${classification_metrics.roc_auc}` : 'Weighted avg'}
            </div>
          </div>
        </div>
      )}

      {!isClassification && regression_metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">R² Score</div>
            <div className="text-title-lg font-extrabold text-purple-600 dark:text-purple-400">
              {regression_metrics.r2.toFixed(3)}
            </div>
            <div className="text-caption text-muted">Coefficient of determination</div>
          </div>

          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">MAE</div>
            <div className="text-title-lg font-extrabold text-ink">
              {regression_metrics.mae.toFixed(2)}
            </div>
            <div className="text-caption text-muted">Mean absolute error</div>
          </div>

          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">RMSE</div>
            <div className="text-title-lg font-extrabold text-ink">
              {regression_metrics.rmse.toFixed(2)}
            </div>
            <div className="text-caption text-muted">Root mean squared error</div>
          </div>

          <div className="p-5 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-1">
            <div className="text-caption font-bold uppercase tracking-wider text-muted">MSE</div>
            <div className="text-title-lg font-extrabold text-ink">
              {regression_metrics.mse.toFixed(2)}
            </div>
            <div className="text-caption text-muted">Mean squared error</div>
          </div>
        </div>
      )}

      {/* Main Analysis Section: Confusion Matrix & Feature Importance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Confusion Matrix (Classification) */}
        {isClassification && classification_metrics?.confusion_matrix && (
          <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-title-sm font-bold text-ink flex items-center gap-2">
                <Target className="w-4 h-4 text-purple-500" />
                <span>Confusion Matrix</span>
              </h3>
              <span className="text-caption text-muted">Actual vs Predicted</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-center border-collapse">
                <thead>
                  <tr>
                    <th className="p-2 text-caption text-muted font-normal text-left">Actual \ Pred</th>
                    {classification_metrics.confusion_matrix.labels.map((lbl) => (
                      <th key={lbl} className="p-2 text-caption font-bold text-ink border-b border-hairline">
                        {lbl}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {classification_metrics.confusion_matrix.matrix.map((row, i) => {
                    const rowLabel = classification_metrics.confusion_matrix.labels[i];
                    return (
                      <tr key={i}>
                        <td className="p-2 text-caption font-bold text-ink text-left border-r border-hairline">
                          {rowLabel}
                        </td>
                        {row.map((cellVal, j) => {
                          const isDiagonal = i === j;
                          return (
                            <td
                              key={j}
                              className={`p-3 text-sm font-bold border border-hairline rounded-lg transition-colors ${
                                isDiagonal
                                  ? 'bg-purple-500/15 text-purple-700 dark:text-purple-300 font-extrabold'
                                  : 'bg-surface-soft/40 text-muted'
                              }`}
                            >
                              {cellVal}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Feature Importance Bar Chart */}
        {feature_importance && feature_importance.length > 0 && (
          <div className={`p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4 ${!isClassification ? 'md:col-span-2' : ''}`}>
            <div className="flex items-center justify-between">
              <h3 className="text-title-sm font-bold text-ink flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-purple-500" />
                <span>Feature Importance</span>
              </h3>
              <span className="text-caption text-muted">Relative Impact</span>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={feature_importance.slice(0, 10)}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 40, bottom: 5 }}
                >
                  <XAxis type="number" tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} stroke="currentColor" className="text-caption text-muted" />
                  <YAxis type="category" dataKey="feature" width={100} stroke="currentColor" className="text-caption font-semibold text-ink" />
                  <Tooltip
                    formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`, 'Importance']}
                    contentStyle={{ borderRadius: '12px', background: 'var(--color-surface-card)', borderColor: 'var(--color-hairline)' }}
                  />
                  <Bar dataKey="importance" radius={[0, 6, 6, 0]}>
                    {feature_importance.slice(0, 10).map((_, index) => (
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

      {/* Model Export & Reproducibility Section */}
      {fileId && training_run_id && (
        <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-title-sm font-bold text-ink flex items-center gap-2">
              <Download className="w-4 h-4 text-purple-500" />
              <span>Export Model & Reproducibility Artifacts</span>
            </h3>
            <span className="text-caption text-muted">Ready for production deployment</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <a
              href={getModelExportUrl(fileId, training_run_id)}
              download
              className="flex items-center justify-between p-3.5 rounded-xl bg-surface-soft/80 border border-hairline hover:border-purple-500/40 hover:bg-surface-soft hover:shadow-xs transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold text-xs">
                  .joblib
                </div>
                <div className="text-left">
                  <div className="text-sm font-bold text-ink group-hover:text-purple-600 transition-colors">Fitted Model</div>
                  <div className="text-[11px] text-muted">Serialized Pipeline</div>
                </div>
              </div>
              <Download className="w-4 h-4 text-muted group-hover:text-purple-600 transition-colors" />
            </a>

            <a
              href={getPredictionsExportUrl(fileId, training_run_id)}
              download
              className="flex items-center justify-between p-3.5 rounded-xl bg-surface-soft/80 border border-hairline hover:border-purple-500/40 hover:bg-surface-soft hover:shadow-xs transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
                  .csv
                </div>
                <div className="text-left">
                  <div className="text-sm font-bold text-ink group-hover:text-purple-600 transition-colors">Predictions</div>
                  <div className="text-[11px] text-muted">Test & Dataset CSV</div>
                </div>
              </div>
              <Download className="w-4 h-4 text-muted group-hover:text-purple-600 transition-colors" />
            </a>

            <a
              href={getMetricsExportUrl(fileId, training_run_id)}
              download
              className="flex items-center justify-between p-3.5 rounded-xl bg-surface-soft/80 border border-hairline hover:border-purple-500/40 hover:bg-surface-soft hover:shadow-xs transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold text-xs">
                  .json
                </div>
                <div className="text-left">
                  <div className="text-sm font-bold text-ink group-hover:text-purple-600 transition-colors">Metrics & Meta</div>
                  <div className="text-[11px] text-muted">Full Evaluation JSON</div>
                </div>
              </div>
              <Download className="w-4 h-4 text-muted group-hover:text-purple-600 transition-colors" />
            </a>

            <a
              href={getCodeExportUrl(fileId, training_run_id)}
              download
              className="flex items-center justify-between p-3.5 rounded-xl bg-surface-soft/80 border border-hairline hover:border-purple-500/40 hover:bg-surface-soft hover:shadow-xs transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center font-bold text-xs">
                  .py
                </div>
                <div className="text-left">
                  <div className="text-sm font-bold text-ink group-hover:text-purple-600 transition-colors">Training Code</div>
                  <div className="text-[11px] text-muted">Runnable Python Script</div>
                </div>
              </div>
              <Download className="w-4 h-4 text-muted group-hover:text-purple-600 transition-colors" />
            </a>
          </div>
        </div>
      )}

      {/* Run Metadata Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-surface-soft/60 border border-hairline text-caption text-muted">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>Training Time: <strong>{training_time_seconds}s</strong></span>
          </div>
          <div className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5" />
            <span>Dataset Split: <strong>{train_row_count.toLocaleString()} Train</strong> / <strong>{test_row_count.toLocaleString()} Test</strong></span>
          </div>
        </div>

        <div className="font-mono text-[11px]">
          Run ID: {training_run_id}
        </div>
      </div>
    </div>
  );
};
