import React, { createContext, useContext, useState, useEffect } from 'react';
import type { TargetCandidate, ModelRecommendation, ModelTrainingResponse } from '../lib/api';
import { useDataset } from './datasetStore';

interface DSContextType {
  fileId: string | null;
  selectedTarget: string | null;
  selectedTargetCandidate: TargetCandidate | null;
  isCustomTarget: boolean;
  selectedFeatures: Set<string>;
  featureSelections: Record<string, boolean>;
  selectedModel: ModelRecommendation | null;
  trainingResult: ModelTrainingResponse | null;
  setTarget: (column: string, candidate?: TargetCandidate | null) => void;
  toggleFeature: (column: string) => void;
  setSelectedFeatures: (features: string[]) => void;
  selectAllRecommended: (recommendedCols: string[]) => void;
  deselectAllFeatures: () => void;
  setModel: (model: ModelRecommendation | null) => void;
  setTrainingResult: (result: ModelTrainingResponse | null) => void;
  resetDSStore: () => void;
}

const DSContext = createContext<DSContextType | undefined>(undefined);

const STORAGE_KEY_PREFIX = 'insightiq_ds_store_';

export const DSProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { dataset } = useDataset();
  const fileId = dataset ? dataset.file_id : null;

  const [selectedTarget, setSelectedTargetState] = useState<string | null>(null);
  const [selectedTargetCandidate, setSelectedTargetCandidateState] = useState<TargetCandidate | null>(null);
  const [isCustomTarget, setIsCustomTargetState] = useState<boolean>(false);
  const [selectedFeatures, setSelectedFeaturesState] = useState<Set<string>>(new Set());
  const [featureSelections, setFeatureSelectionsState] = useState<Record<string, boolean>>({});
  const [selectedModel, setSelectedModelState] = useState<ModelRecommendation | null>(null);
  const [trainingResult, setTrainingResultState] = useState<ModelTrainingResponse | null>(null);

  // Sync / restore state when fileId changes
  useEffect(() => {
    if (!fileId) {
      setSelectedTargetState(null);
      setSelectedTargetCandidateState(null);
      setIsCustomTargetState(false);
      setSelectedFeaturesState(new Set());
      setFeatureSelectionsState({});
      setSelectedModelState(null);
      setTrainingResultState(null);
      return;
    }

    try {
      const savedRaw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${fileId}`);
      if (savedRaw) {
        const parsed = JSON.parse(savedRaw);
        if (parsed.selectedTarget) {
          setSelectedTargetState(parsed.selectedTarget);
          setSelectedTargetCandidateState(parsed.selectedTargetCandidate || null);
          setIsCustomTargetState(!!parsed.isCustomTarget);
          const feats = new Set<string>(parsed.selectedFeatures || []);
          setSelectedFeaturesState(feats);
          const featMap: Record<string, boolean> = {};
          feats.forEach((f) => {
            featMap[f] = true;
          });
          setFeatureSelectionsState(parsed.featureSelections || featMap);
          setSelectedModelState(parsed.selectedModel || null);
          setTrainingResultState(parsed.trainingResult || null);
        }
      }
    } catch (err) {
      console.error('Failed to restore DS state from localStorage:', err);
    }
  }, [fileId]);

  // Save to localStorage whenever state changes
  const saveState = (
    target: string | null,
    candidate: TargetCandidate | null,
    custom: boolean,
    feats: Set<string>,
    featMap: Record<string, boolean>,
    model: ModelRecommendation | null,
    tResult: ModelTrainingResponse | null
  ) => {
    if (!fileId) return;
    try {
      const payload = {
        selectedTarget: target,
        selectedTargetCandidate: candidate,
        isCustomTarget: custom,
        selectedFeatures: Array.from(feats),
        featureSelections: featMap,
        selectedModel: model,
        trainingResult: tResult,
      };
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${fileId}`, JSON.stringify(payload));
    } catch (err) {
      console.error('Failed to save DS state to localStorage:', err);
    }
  };

  const setTarget = (column: string, candidate: TargetCandidate | null = null) => {
    const isCustom = !candidate;
    setSelectedTargetState(column);
    setSelectedTargetCandidateState(candidate);
    setIsCustomTargetState(isCustom);

    // Reset features, model, and training results when target changes
    const emptySet = new Set<string>();
    const emptyMap: Record<string, boolean> = {};
    setSelectedFeaturesState(emptySet);
    setFeatureSelectionsState(emptyMap);
    setSelectedModelState(null);
    setTrainingResultState(null);

    saveState(column, candidate, isCustom, emptySet, emptyMap, null, null);
  };

  const toggleFeature = (column: string) => {
    setSelectedFeaturesState((prevSet) => {
      const newSet = new Set(prevSet);
      const newMap = { ...featureSelections };
      if (newSet.has(column)) {
        newSet.delete(column);
        newMap[column] = false;
      } else {
        newSet.add(column);
        newMap[column] = true;
      }
      setFeatureSelectionsState(newMap);
      saveState(selectedTarget, selectedTargetCandidate, isCustomTarget, newSet, newMap, selectedModel, trainingResult);
      return newSet;
    });
  };

  const setSelectedFeatures = (featuresList: string[]) => {
    const newSet = new Set(featuresList);
    const newMap: Record<string, boolean> = {};
    featuresList.forEach((f) => {
      newMap[f] = true;
    });
    setSelectedFeaturesState(newSet);
    setFeatureSelectionsState(newMap);
    saveState(selectedTarget, selectedTargetCandidate, isCustomTarget, newSet, newMap, selectedModel, trainingResult);
  };

  const selectAllRecommended = (recommendedCols: string[]) => {
    setSelectedFeaturesState((prevSet) => {
      const newSet = new Set(prevSet);
      const newMap = { ...featureSelections };
      recommendedCols.forEach((c) => {
        newSet.add(c);
        newMap[c] = true;
      });
      setFeatureSelectionsState(newMap);
      saveState(selectedTarget, selectedTargetCandidate, isCustomTarget, newSet, newMap, selectedModel, trainingResult);
      return newSet;
    });
  };

  const deselectAllFeatures = () => {
    const emptySet = new Set<string>();
    const emptyMap: Record<string, boolean> = {};
    setSelectedFeaturesState(emptySet);
    setFeatureSelectionsState(emptyMap);
    saveState(selectedTarget, selectedTargetCandidate, isCustomTarget, emptySet, emptyMap, selectedModel, trainingResult);
  };

  const setModel = (model: ModelRecommendation | null) => {
    setSelectedModelState(model);
    setTrainingResultState(null); // Reset training result when model choice changes
    saveState(selectedTarget, selectedTargetCandidate, isCustomTarget, selectedFeatures, featureSelections, model, null);
  };

  const setTrainingResult = (result: ModelTrainingResponse | null) => {
    setTrainingResultState(result);
    saveState(selectedTarget, selectedTargetCandidate, isCustomTarget, selectedFeatures, featureSelections, selectedModel, result);
  };

  const resetDSStore = () => {
    setSelectedTargetState(null);
    setSelectedTargetCandidateState(null);
    setIsCustomTargetState(false);
    setSelectedFeaturesState(new Set());
    setFeatureSelectionsState({});
    setSelectedModelState(null);
    setTrainingResultState(null);
    if (fileId) {
      localStorage.removeItem(`${STORAGE_KEY_PREFIX}${fileId}`);
    }
  };

  return (
    <DSContext.Provider
      value={{
        fileId,
        selectedTarget,
        selectedTargetCandidate,
        isCustomTarget,
        selectedFeatures,
        featureSelections,
        selectedModel,
        trainingResult,
        setTarget,
        toggleFeature,
        setSelectedFeatures,
        selectAllRecommended,
        deselectAllFeatures,
        setModel,
        setTrainingResult,
        resetDSStore,
      }}
    >
      {children}
    </DSContext.Provider>
  );
};

export const useDSStore = () => {
  const context = useContext(DSContext);
  if (!context) {
    throw new Error('useDSStore must be used within a DSProvider');
  }
  return context;
};
