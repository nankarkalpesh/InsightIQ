import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchDatasetOverview, type DatasetMetadataResponse } from '../lib/api';

const SESSION_STORAGE_KEY = 'insightiq_dataset_session';

export interface DatasetContextType {
  dataset: DatasetMetadataResponse | null;
  setDataset: (dataset: DatasetMetadataResponse | null) => void;
  clearDataset: () => void;
  isRestoringSession: boolean;
  sessionError: string | null;
}

export const DatasetContext = createContext<DatasetContextType | undefined>(undefined);

export const DatasetProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [dataset, setDatasetState] = useState<DatasetMetadataResponse | null>(null);
  const [isRestoringSession, setIsRestoringSession] = useState<boolean>(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  // Restore session on app load
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      try {
        const savedSessionStr = localStorage.getItem(SESSION_STORAGE_KEY);
        if (!savedSessionStr) {
          if (isMounted) setIsRestoringSession(false);
          return;
        }

        const savedData: DatasetMetadataResponse = JSON.parse(savedSessionStr);
        if (!savedData || !savedData.file_id) {
          localStorage.removeItem(SESSION_STORAGE_KEY);
          if (isMounted) setIsRestoringSession(false);
          return;
        }

        // Validate backend session exists
        await fetchDatasetOverview(savedData.file_id);

        if (isMounted) {
          setDatasetState(savedData);
          setIsRestoringSession(false);
        }
      } catch (err) {
        console.warn('Backend session expired or unreachable:', err);
        localStorage.removeItem(SESSION_STORAGE_KEY);
        if (isMounted) {
          setDatasetState(null);
          setSessionError('Your previous session expired or the server restarted. Please re-upload your dataset.');
          setIsRestoringSession(false);
        }
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const setDataset = (newDataset: DatasetMetadataResponse | null) => {
    setDatasetState(newDataset);
    setSessionError(null);
    if (newDataset) {
      try {
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newDataset));
      } catch (e) {
        console.error('Failed to save dataset session to localStorage:', e);
      }
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  };

  const clearDataset = () => {
    setDatasetState(null);
    setSessionError(null);
    localStorage.removeItem(SESSION_STORAGE_KEY);
  };

  return (
    <DatasetContext.Provider
      value={{
        dataset,
        setDataset,
        clearDataset,
        isRestoringSession,
        sessionError,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
};

export const useDataset = (): DatasetContextType => {
  const context = useContext(DatasetContext);
  if (!context) {
    throw new Error('useDataset must be used within a DatasetProvider');
  }
  return context;
};
