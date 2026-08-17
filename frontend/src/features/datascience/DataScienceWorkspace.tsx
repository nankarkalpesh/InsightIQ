import React, { useState } from 'react';
import { Target, Layers, Brain, Sparkles, CheckCircle2, BarChart2, Play } from 'lucide-react';
import { TargetSelector } from './TargetSelector';
import { FeatureSelector } from './FeatureSelector';
import { ModelSelector } from './ModelSelector';
import { ModelTrainer } from './ModelTrainer';
import { PredictionPlayground } from './PredictionPlayground';
import { DSProvider, useDSStore } from '../../store/dsStore';
import { useDataset } from '../../store/datasetStore';
import { DatasetEmptyState } from '../../components/common/DatasetEmptyState';

type DSSubTab = 'Target' | 'Features' | 'Models' | 'Evaluation' | 'Playground';

const DataScienceWorkspaceContent: React.FC = () => {
  const [activeTab, setActiveTabState] = useState<DSSubTab>(() => {
    try {
      const saved = localStorage.getItem('insightiq_ds_subtab');
      return (saved as DSSubTab) || 'Target';
    } catch {
      return 'Target';
    }
  });

  const { selectedTarget, selectedFeatures, selectedModel, trainingResult } = useDSStore();

  const setActiveTab = (tab: DSSubTab) => {
    setActiveTabState(tab);
    try {
      localStorage.setItem('insightiq_ds_subtab', tab);
    } catch (e) {
      console.error('Failed to save ds subtab to localStorage:', e);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Sub-Tab Navigation Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-hairline max-w-5xl mx-auto">
        <div role="tablist" aria-label="Data Science Workflow Tabs" className="flex flex-wrap items-center gap-1.5 p-1 bg-surface-soft/60 border border-hairline rounded-xl max-w-full">
          <button
            role="tab"
            aria-selected={activeTab === 'Target'}
            aria-label="Target Selection Tab"
            onClick={() => setActiveTab('Target')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none cursor-pointer shrink-0 ${
              activeTab === 'Target'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Target className="w-4 h-4 text-primary" />
            <span>Target Selection</span>
            {selectedTarget && (
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'Features'}
            aria-label="Feature Engineering Tab"
            onClick={() => setActiveTab('Features')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none cursor-pointer shrink-0 ${
              activeTab === 'Features'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Layers className="w-4 h-4 text-purple-500" />
            <span>Feature Engineering</span>
            {selectedFeatures.size > 0 && (
              <span className="ml-1 px-1.5 py-0.2 text-[10px] font-bold bg-primary text-white rounded-full">
                {selectedFeatures.size}
              </span>
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'Models'}
            aria-label="Model Selection Tab"
            onClick={() => setActiveTab('Models')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none cursor-pointer shrink-0 ${
              activeTab === 'Models'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Brain className="w-4 h-4 text-emerald-500" />
            <span>Model Selection</span>
            {selectedModel && (
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'Evaluation'}
            aria-label="Training and Evaluation Tab"
            onClick={() => setActiveTab('Evaluation')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none cursor-pointer shrink-0 ${
              activeTab === 'Evaluation'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <BarChart2 className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <span>Training & Evaluation</span>
            {trainingResult && (
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'Playground'}
            aria-label="Prediction Playground Tab"
            onClick={() => setActiveTab('Playground')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-150 select-none cursor-pointer shrink-0 ${
              activeTab === 'Playground'
                ? 'bg-surface-card text-ink shadow-xs border border-hairline'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Play className="w-4 h-4 text-emerald-600 dark:text-emerald-400 fill-current" />
            <span>Prediction Playground</span>
            {trainingResult && (
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
            )}
          </button>
        </div>

        {/* Workspace Summary Pills */}
        <div className="flex items-center gap-2 text-caption flex-wrap">
          {selectedTarget ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Target: {selectedTarget}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-soft text-muted font-medium border border-hairline">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              <span>Step 1: Select Target</span>
            </div>
          )}

          {selectedFeatures.size > 0 && (
            <div className="px-3 py-1 rounded-full bg-purple-500/10 text-purple-700 dark:text-purple-300 border border-purple-500/20 font-semibold">
              {selectedFeatures.size} Features
            </div>
          )}

          {selectedModel && (
            <div className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 font-semibold">
              Model: {selectedModel.model_name}
            </div>
          )}
        </div>
      </div>

      {/* Render Active Sub-Tab View */}
      {activeTab === 'Target' && (
        <TargetSelector onTargetSelected={() => setActiveTab('Features')} />
      )}
      {activeTab === 'Features' && (
        <FeatureSelector onNavigateToTarget={() => setActiveTab('Target')} />
      )}
      {activeTab === 'Models' && (
        <ModelSelector
          onNavigateToFeatures={() => setActiveTab('Features')}
          onNavigateToTarget={() => setActiveTab('Target')}
          onNavigateToTraining={() => setActiveTab('Evaluation')}
        />
      )}
      {activeTab === 'Evaluation' && (
        <ModelTrainer
          onNavigateToModels={() => setActiveTab('Models')}
          onNavigateToFeatures={() => setActiveTab('Features')}
          onNavigateToTarget={() => setActiveTab('Target')}
        />
      )}
      {activeTab === 'Playground' && (
        <PredictionPlayground
          onNavigateToTraining={() => setActiveTab('Evaluation')}
        />
      )}
    </div>
  );
};

export interface DataScienceWorkspaceProps {
  onNavigateToUpload?: () => void;
}

export const DataScienceWorkspace: React.FC<DataScienceWorkspaceProps> = ({ onNavigateToUpload }) => {
  const { dataset } = useDataset();

  if (!dataset) {
    return (
      <DatasetEmptyState
        badgeText="Data Science Engine"
        icon={Brain}
        title="No Dataset Loaded"
        description="Upload a dataset to perform feature analysis, target selection, automated ML model training, and interactive prediction playgrounds."
        features={['Target & Feature Selection', 'AutoML Model Training', 'Prediction Playground']}
        onNavigateToUpload={onNavigateToUpload}
      />
    );
  }

  return (
    <DSProvider>
      <DataScienceWorkspaceContent />
    </DSProvider>
  );
};
