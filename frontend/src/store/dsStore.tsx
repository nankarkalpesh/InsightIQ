import React, { createContext, useContext, useState, useEffect } from 'react';
import { saveDSStateApi, type TargetCandidate, type ModelRecommendation, type ModelTrainingResponse } from '../lib/api';
import { useDataset } from './datasetStore';
import { useAuth } from './authStore';

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
  hydrateDSState: (target: string | null, features: string[], modelName: string | null, metrics?: Record<string, any>) => void;
}

const DSContext = createContext<DSContextType | undefined>(undefined);

export const DSProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { dataset } = useDataset();
  const { user } = useAuth();
  const fileId = dataset ? dataset.file_id : null;
  const userId = user?.id;

  const getStorageKey = (fid?: string | null, uId?: string) =>
    uId
      ? `insightiq_u_${uId}_ds_store_${fid || 'default'}`
      : `insightiq_guest_ds_store_${fid || 'default'}`;

  const storageKey = getStorageKey(fileId, userId);

  const [selectedTarget, setSelectedTargetState] = useState<string | null>(null);
  const [selectedTargetCandidate, setSelectedTargetCandidateState] = useState<TargetCandidate | null>(null);
  const [isCustomTarget, setIsCustomTargetState] = useState<boolean>(false);
  const [selectedFeatures, setSelectedFeaturesState] = useState<Set<string>>(new Set());
  const [featureSelections, setFeatureSelectionsState] = useState<Record<string, boolean>>({});
  const [selectedModel, setSelectedModelState] = useState<ModelRecommendation | null>(null);
  const [trainingResult, setTrainingResultState] = useState<ModelTrainingResponse | null>(null);

  // Reset state on logout
  useEffect(() => {
    const handleLogout = () => {
      setSelectedTargetState(null);
      setSelectedTargetCandidateState(null);
      setIsCustomTargetState(false);
      setSelectedFeaturesState(new Set());
      setFeatureSelectionsState({});
      setSelectedModelState(null);
      setTrainingResultState(null);
    };
    window.addEventListener('insightiq_logout', handleLogout);
    return () => {
      window.removeEventListener('insightiq_logout', handleLogout);
    };
  }, []);

  // Sync / restore state when fileId or storageKey changes
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
      const savedRaw = localStorage.getItem(storageKey);
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
  }, [fileId, storageKey]);

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
      localStorage.setItem(storageKey, JSON.stringify(payload));
    } catch (err) {
      console.error('Failed to save DS state to localStorage:', err);
    }

    if (user && target) {
      const featureList = Array.from(feats);
      const modelName = model?.model_name || (tResult as any)?.model_name || 'selected';
      saveDSStateApi(fileId, target, featureList, modelName, tResult?.metrics || {}).catch((err) => {
        console.warn('Failed to save DS state to backend:', err);
      });
    }
  };

  const hydrateDSState = (
    target: string | null,
    features: string[],
    modelName: string | null,
    metrics?: Record<string, any>
  ) => {
    const featsSet = new Set<string>(features || []);
    const featMap: Record<string, boolean> = {};
    (features || []).forEach((f) => {
      featMap[f] = true;
    });
    setSelectedTargetState(target);
    setIsCustomTargetState(true);
    setSelectedFeaturesState(featsSet);
    setFeatureSelectionsState(featMap);
    const modelObj = modelName ? ({ model_name: modelName, display_name: modelName } as any) : null;
    setSelectedModelState(modelObj);
    saveState(target, null, true, featsSet, featMap, modelObj, null);
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
      localStorage.removeItem(storageKey);
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
        hydrateDSState,
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
