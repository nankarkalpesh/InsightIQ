import React, { useState } from 'react';
import {
  Database,
  Sun,
  Moon,
  Trash2,
  Cpu,
  Info,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  ShieldAlert
} from 'lucide-react';
import { useDataset } from '../../store/datasetStore';
import { useTheme } from '../../hooks/useTheme';
import { useLLMProvider } from '../../store/llmStore';

interface SettingsWorkspaceProps {
  onNavigateToNav?: (nav: 'Overview' | 'Analytics' | 'Data Science' | 'Data Chat' | 'Settings') => void;
}

export const SettingsWorkspace: React.FC<SettingsWorkspaceProps> = ({ onNavigateToNav }) => {
  const { dataset, clearDataset } = useDataset();
  const { theme, toggleTheme } = useTheme();
  const { activeProvider, providers, isLoading: isLLMLoading, refreshSettings, setActiveProvider } = useLLMProvider();
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [isUpdatingProvider, setIsUpdatingProvider] = useState<boolean>(false);

  const handleClearSessionConfirmed = () => {
    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (
          key && (
            key.includes('_dataset_session') ||
            key.includes('_dashboard_') ||
            key.includes('_ds_store_') ||
            key.includes('_chat_session_')
          )
        ) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k));
    } catch (e) {
      console.error('Failed to clear dataset session keys from localStorage:', e);
    }
    clearDataset();
    setShowClearConfirm(false);
    if (onNavigateToNav) {
      onNavigateToNav('Overview');
    }
  };


  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 pb-12 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <h1 className="text-2xl font-bold text-ink tracking-tight">Workspace Settings</h1>
          <p className="text-sm text-muted mt-1">
            Manage dataset session, appearance, AI engine connection, and local workspace state.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 text-xs font-semibold bg-primary/10 text-primary rounded-full border border-primary/20 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Local Alpha Environment</span>
          </span>
        </div>
      </div>

      {/* 1. Active Dataset Information Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold border border-primary/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">Current Dataset Session</h2>
              <p className="text-xs text-muted">Active dataset in local browser & memory store</p>
            </div>
          </div>
          {dataset && onNavigateToNav && (
            <button
              onClick={() => onNavigateToNav('Overview')}
              className="px-3 py-1.5 rounded-lg bg-surface-soft hover:bg-surface-hover text-xs font-semibold text-ink border border-hairline transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <span>View Overview</span>
              <ExternalLink className="w-3.5 h-3.5 text-muted" />
            </button>
          )}
        </div>

        {dataset ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="p-3.5 rounded-xl bg-surface-soft/60 border border-hairline">
              <div className="text-xs text-muted font-medium">Filename</div>
              <div className="text-sm font-semibold text-ink truncate mt-1">{dataset.filename}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-soft/60 border border-hairline">
              <div className="text-xs text-muted font-medium">Row Count</div>
              <div className="text-sm font-semibold text-ink mt-1">
                {dataset.row_count !== null && dataset.row_count !== undefined ? dataset.row_count.toLocaleString() : 'N/A'} rows
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-surface-soft/60 border border-hairline">
              <div className="text-xs text-muted font-medium">Columns</div>
              <div className="text-sm font-semibold text-ink mt-1">
                {dataset.column_count || (dataset.columns ? dataset.columns.length : 0)} columns
              </div>
            </div>

            {dataset.columns && dataset.columns.length > 0 && (
              <div className="md:col-span-3 pt-2">
                <div className="text-xs font-medium text-muted mb-2">Detected Columns</div>
                <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto p-2 bg-surface-soft/40 border border-hairline rounded-xl">
                  {dataset.columns.map((col, idx) => {
                    const colName = typeof col === 'string' ? col : col.name;
                    return (
                      <span key={`${colName}-${idx}`} className="px-2 py-0.5 text-[11px] font-mono bg-surface-card text-ink border border-hairline rounded-md">
                        {colName}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 rounded-xl bg-surface-soft/40 border border-dashed border-hairline text-center space-y-3">
            <p className="text-sm text-muted">No dataset is currently uploaded in this session.</p>
            {onNavigateToNav && (
              <button
                onClick={() => onNavigateToNav('Overview')}
                className="px-4 py-2 rounded-xl bg-primary text-white text-xs font-semibold hover:bg-primary-hover transition-colors cursor-pointer shadow-xs"
              >
                Upload Dataset
              </button>
            )}
          </div>
        )}
      </div>

      {/* 2. Theme & Appearance Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold border border-purple-500/20">
              {theme === 'dark' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">Appearance & Theme</h2>
              <p className="text-xs text-muted">Customize workspace dark/light visual theme</p>
            </div>
          </div>
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-soft hover:bg-surface-hover text-ink text-xs font-semibold border border-hairline transition-all duration-150 cursor-pointer"
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-4 h-4 text-amber-500" />
                <span>Switch to Light Mode</span>
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-purple-500" />
                <span>Switch to Dark Mode</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 3. AI Assistant & LLM Provider Selector Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold border border-emerald-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">AI Assistant & LLM Engine</h2>
              <p className="text-xs text-muted">Select active LLM provider for Data Chat & Tool Calling</p>
            </div>
          </div>
          <button
            onClick={() => refreshSettings()}
            disabled={isLLMLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-soft hover:bg-surface-hover text-ink text-xs font-semibold border border-hairline transition-colors cursor-pointer disabled:opacity-50"
            title="Refresh LLM Provider Status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLLMLoading ? 'animate-spin text-primary' : ''}`} />
            <span>{isLLMLoading ? 'Checking...' : 'Refresh Status'}</span>
          </button>
        </div>

        {providerError && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs">
            {providerError}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
          {providers.map((p) => {
            const isActive = activeProvider === p.id;
            const isConfigured = p.configured;
            const isGroq = p.id === 'groq';
            const isOllama = p.id === 'ollama';

            const handleSelect = async () => {
              if (!isConfigured || isActive || isUpdatingProvider) return;
              setProviderError(null);
              setIsUpdatingProvider(true);
              try {
                await setActiveProvider(p.id);
              } catch (err: any) {
                setProviderError(err?.message || `Failed to switch provider to ${p.name}`);
              } finally {
                setIsUpdatingProvider(false);
              }
            };

            // Provider-specific status labels & descriptions
            let statusText = 'Not configured';
            let statusColor = 'text-muted';
            let dotColor = 'bg-red-400';
            let helperNote: string | null = null;

            if (isGroq) {
              if (p.status === 'ready' || isConfigured) {
                statusText = 'Connected & Ready';
                statusColor = 'text-emerald-600 dark:text-emerald-400';
                dotColor = 'bg-emerald-500 animate-pulse';
                helperNote = p.key_source === 'user' ? 'Using your personal API key' : 'Using InsightIQ default API access';
              } else if (p.status === 'default_limit_reached') {
                statusText = 'Default API limit reached';
                statusColor = 'text-amber-600 dark:text-amber-400';
                dotColor = 'bg-amber-500';
                helperNote = 'Add your own Groq API key to continue using Groq Cloud.';
              } else if (p.status === 'user_key_limit_reached') {
                statusText = 'Personal API key limit reached';
                statusColor = 'text-amber-600 dark:text-amber-400';
                dotColor = 'bg-amber-500';
                helperNote = 'Your configured API key has exceeded its quota limit.';
              } else {
                statusText = 'Key not configured';
                helperNote = 'Add an API key below to enable Groq Cloud.';
              }
            } else if (isOllama) {
              if (p.status === 'ready' || isConfigured) {
                statusText = 'Connected & Ready';
                statusColor = 'text-emerald-600 dark:text-emerald-400';
                dotColor = 'bg-emerald-500 animate-pulse';
                helperNote = `Ollama is running (Model: ${p.model || 'llama3.2:3b'})`;
              } else if (p.status === 'model_missing') {
                statusText = 'Required model missing';
                statusColor = 'text-amber-600 dark:text-amber-400';
                dotColor = 'bg-amber-500';
                helperNote = `The required Ollama model (${p.model || 'llama3.2:3b'}) is not installed on this computer.`;
              } else if (p.status === 'unreachable' || p.status === 'not_running') {
                statusText = 'Ollama unavailable';
                statusColor = 'text-red-500';
                dotColor = 'bg-red-400';
                helperNote = 'Ollama is not currently reachable on this computer. Start Ollama locally, then click Refresh Status.';
              } else if (p.status === 'detection_unavailable') {
                statusText = 'Detection unavailable';
                statusColor = 'text-amber-600 dark:text-amber-400';
                dotColor = 'bg-amber-500';
                helperNote = 'Local status cannot be verified from this deployment.';
              }
            }

            return (
              <div
                key={p.id}
                onClick={handleSelect}
                className={`p-4 rounded-xl border transition-all duration-150 relative flex flex-col justify-between space-y-3 ${isActive
                    ? 'bg-primary/5 border-primary shadow-2xs'
                    : isConfigured
                      ? 'bg-surface-soft/40 border-hairline hover:border-primary/40 cursor-pointer'
                      : 'bg-surface-soft/20 border-hairline opacity-75 cursor-not-allowed'
                  }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <input
                      type="radio"
                      name="llm_provider"
                      checked={isActive}
                      disabled={!isConfigured || isUpdatingProvider}
                      onChange={handleSelect}
                      className="text-primary focus:ring-primary h-4 w-4 cursor-pointer disabled:cursor-not-allowed"
                    />
                    <div>
                      <h3 className="text-sm font-semibold text-ink">{p.name}</h3>
                      {p.model && <p className="text-[11px] font-mono text-muted mt-0.5">Model: {p.model}</p>}
                    </div>
                  </div>
                  {isActive && (
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-primary/10 text-primary rounded-md border border-primary/20 shrink-0">
                      Active
                    </span>
                  )}
                </div>

                {helperNote && (
                  <p className="text-[11px] text-muted leading-snug bg-surface-card/60 p-2 rounded-lg border border-hairline/60">
                    {helperNote}
                  </p>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-hairline text-[11px]">
                  <div className="flex items-center gap-1.5 font-medium">
                    <span className={`w-2 h-2 rounded-full ${dotColor}`} />
                    <span className={`font-semibold ${statusColor}`}>{statusText}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Custom Groq API Key Input Form */}
        <div className="pt-4 border-t border-hairline space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="groq_key_input" className="block text-xs font-semibold text-ink">
              Configure Personal Groq API Key (Optional)
            </label>
            {providers.find(p => p.id === 'groq')?.key_source === 'user' && (
              <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Your personal API key is configured</span>
              </span>
            )}
          </div>
          <p className="text-xs text-muted leading-relaxed">
            InsightIQ uses its default API access when available. You can add your own Groq API key for independent access.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const input = form.elements.namedItem('groq_key_input') as HTMLInputElement;
              if (!input || !input.value.trim()) return;
              setIsUpdatingProvider(true);
              setProviderError(null);
              try {
                await setActiveProvider('groq', input.value.trim());
                input.value = '';
              } catch (err: any) {
                setProviderError(err?.message || 'Failed to save Groq API key.');
              } finally {
                setIsUpdatingProvider(false);
              }
            }}
            className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-1"
          >
            <div className="flex-1">
              <input
                id="groq_key_input"
                name="groq_key_input"
                type="password"
                placeholder="gsk_..."
                className="w-full px-3 py-2 rounded-xl border border-hairline bg-surface-soft text-xs text-ink placeholder:text-muted focus:outline-none focus:border-primary"
              />
            </div>
            <button
              type="submit"
              disabled={isUpdatingProvider}
              className="px-4 py-2 rounded-xl bg-primary text-on-primary font-semibold text-xs hover:bg-primary-hover transition-colors cursor-pointer shrink-0 disabled:opacity-50 shadow-xs"
            >
              Save Key & Activate
            </button>
          </form>
        </div>
      </div>

      {/* 4. Destructive Action Zone (Clear Session) */}
      <div className="p-6 rounded-2xl bg-surface-card border border-red-500/20 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-red-500/10 text-red-600 dark:text-red-400 flex items-center justify-center font-bold border border-red-500/20">
              <Trash2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">Session Reset & Workspace Clear</h2>
              <p className="text-xs text-muted">Reset current dataset, cached metrics, and returned charts</p>
            </div>
          </div>
          <button
            onClick={() => setShowClearConfirm(true)}
            className="px-4 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 text-xs font-semibold border border-red-500/20 transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Session</span>
          </button>
        </div>
      </div>

      {/* 5. App Info Card */}
      <div className="p-6 rounded-2xl bg-surface-card border border-hairline shadow-xs space-y-3">
        <div className="flex items-center gap-2 text-ink font-semibold text-sm">
          <Info className="w-4 h-4 text-primary" />
          <span>InsightIQ Platform Metadata</span>
        </div>
        <div className="text-xs text-muted leading-relaxed grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
          <div><strong className="text-ink">Version:</strong> InsightIQ v1.0 (Alpha)</div>
          <div><strong className="text-ink">Backend:</strong> FastAPI + Python 3.14 (Pandas/Scikit-Learn)</div>
          <div><strong className="text-ink">Frontend:</strong> React 18 + TypeScript + Recharts</div>
          <div><strong className="text-ink">LLM Model:</strong> Ollama llama3.2:3b (Tool-Calling Enabled)</div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-surface-card border border-hairline rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center shrink-0 border border-red-500/20">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-ink">Clear Dataset Session?</h3>
                <p className="text-xs text-muted mt-0.5">This action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-muted leading-relaxed">
              Clearing the session will remove the currently active dataset, reset all generated KPIs, custom charts, trained models, and conversation history. You will be redirected to the dataset upload screen.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-hairline">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-4 py-2 rounded-xl bg-surface-soft hover:bg-surface-hover text-ink text-xs font-semibold transition-colors cursor-pointer border border-hairline"
              >
                Cancel
              </button>
              <button
                onClick={handleClearSessionConfirmed}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold transition-colors cursor-pointer shadow-xs"
              >
                Yes, Clear Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
