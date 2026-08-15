import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  fetchLLMProviderSettings,
  updateLLMProviderSetting,
  type LLMProviderItem
} from '../lib/api';

export interface LLMProviderContextType {
  activeProvider: string;
  providers: LLMProviderItem[];
  isLoading: boolean;
  error: string | null;
  refreshSettings: () => Promise<void>;
  setActiveProvider: (providerId: string, groqApiKey?: string) => Promise<void>;
}

export const LLMProviderContext = createContext<LLMProviderContextType | undefined>(undefined);

export const LLMProviderStore: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeProvider, setActiveProviderState] = useState<string>('ollama');
  const [providers, setProviders] = useState<LLMProviderItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchLLMProviderSettings();
      setActiveProviderState(data.active_provider || 'ollama');
      setProviders(data.providers || []);
    } catch (err: any) {
      console.error('Failed to fetch LLM provider settings:', err);
      setError(err?.message || 'Failed to load LLM provider settings');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSettings();
  }, [refreshSettings]);

  const setActiveProvider = async (providerId: string, groqApiKey?: string) => {
    try {
      const res = await updateLLMProviderSetting(providerId, groqApiKey);
      setActiveProviderState(res.active_provider);
      await refreshSettings();
    } catch (err: any) {
      console.error('Failed to update LLM provider setting:', err);
      throw err;
    }
  };

  return (
    <LLMProviderContext.Provider
      value={{
        activeProvider,
        providers,
        isLoading,
        error,
        refreshSettings,
        setActiveProvider,
      }}
    >
      {children}
    </LLMProviderContext.Provider>
  );
};

export const useLLMProvider = (): LLMProviderContextType => {
  const context = useContext(LLMProviderContext);
  if (!context) {
    throw new Error('useLLMProvider must be used within an LLMProviderStore');
  }
  return context;
};
