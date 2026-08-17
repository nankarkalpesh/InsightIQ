import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User,
  Wrench,
  Trash2,
  AlertTriangle,
  Loader2,
  FileSpreadsheet,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  History,
  Plus,
  Check,
  Table as TableIcon
} from 'lucide-react';
import { useDataset } from '../../store/datasetStore';
import { useDashboard } from '../../store/dashboardStore';
import { useLLMProvider } from '../../store/llmStore';
import { useAuth } from '../../store/authStore';
import { sendChatMessage, ApiError, type SuggestedAction, type RecommendedChart } from '../../lib/api';
import ReactMarkdown from 'react-markdown';
import { RenderedChartCard } from '../analytics/RenderedChartCard';
import { BrandLogo } from '../../components/icons/BrandLogo';
import { DatasetEmptyState } from '../../components/common/DatasetEmptyState';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  toolCalls?: string[];
  suggestedAction?: SuggestedAction | null;
}

interface SavedChatSession {
  conversation_id?: string;
  messages: ChatMessage[];
}

export interface DataChatWorkspaceProps {
  onNavigateToUpload?: () => void;
}

const SUGGESTED_PROMPTS = [
  'Summarize this dataset and report its quality health score.',
  'How many rows and columns are in this dataset?',
  'What key insights or anomalies should I be aware of?',
  'List all the columns along with total dataset metrics.'
];

const InlineMarkdownTable: React.FC<{ text: string }> = ({ text }) => {
  if (!text) return null;
  const matches = [...text.matchAll(/\*\s*\*\*?([^*:]+)\*\*?:\s*([^\n]+)/g)];
  if (matches.length < 2) return null;

  const rows = matches.map(m => ({
    category: m[1].trim(),
    value: m[2].trim()
  }));

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-hairline bg-surface-card/80 shadow-xs">
      <div className="px-3 py-2 bg-surface-soft/80 border-b border-hairline flex items-center justify-between text-xs font-semibold text-ink">
        <span className="flex items-center gap-1.5">
          <TableIcon className="w-3.5 h-3.5 text-primary" />
          Structured Data Table
        </span>
        <span className="text-[10px] text-muted font-mono">{rows.length} items</span>
      </div>
      <div className="max-h-48 overflow-y-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-soft/40 border-b border-hairline text-muted font-medium text-[11px] sticky top-0">
            <tr>
              <th className="px-3 py-1.5 font-medium">Category / Field</th>
              <th className="px-3 py-1.5 font-medium text-right">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {rows.map((r, i) => (
              <tr key={i} className="hover:bg-surface-hover/50 transition-colors">
                <td className="px-3 py-1.5 font-medium text-ink">{r.category}</td>
                <td className="px-3 py-1.5 font-mono text-ink text-right">{r.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export const DataChatWorkspace: React.FC<DataChatWorkspaceProps> = ({ onNavigateToUpload }) => {
  const { dataset } = useDataset();
  const { addItem, isInDashboard } = useDashboard();
  const { activeProvider } = useLLMProvider();
  const { user } = useAuth();
  
  const fileId = dataset?.file_id;
  const userId = user?.id;

  const providerBadgeText = activeProvider === 'groq' ? 'Groq Ready' : 'Ollama Ready';
  const providerDisplayName = activeProvider === 'groq' ? 'Groq Cloud' : 'Ollama';

  const getChatStorageKey = (fid?: string, uId?: string) =>
    uId
      ? `insightiq_u_${uId}_chat_session_${fid || 'default'}`
      : `insightiq_guest_chat_session_${fid || 'default'}`;

  const storageKey = getChatStorageKey(fileId, userId);

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (!fileId) return [];
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed: SavedChatSession = JSON.parse(saved);
        return parsed.messages || [];
      }
    } catch (e) {
      console.error('Failed to load chat messages from localStorage:', e);
    }
    return [];
  });

  const [input, setInput] = useState<string>('');
  const [conversationId, setConversationId] = useState<string | undefined>(() => {
    if (!fileId) return undefined;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed: SavedChatSession = JSON.parse(saved);
        return parsed.conversation_id;
      }
    } catch {
      return undefined;
    }
    return undefined;
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<{ message: string; guidance?: string } | null>(null);
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Reset on logout
  useEffect(() => {
    const handleLogout = () => {
      setMessages([]);
      setConversationId(undefined);
    };
    window.addEventListener('insightiq_logout', handleLogout);
    return () => {
      window.removeEventListener('insightiq_logout', handleLogout);
    };
  }, []);

  // Sync state when fileId or storageKey changes
  useEffect(() => {
    if (!fileId) {
      setMessages([]);
      setConversationId(undefined);
      return;
    }
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed: SavedChatSession = JSON.parse(saved);
        setMessages(parsed.messages || []);
        setConversationId(parsed.conversation_id);
      } else {
        setMessages([]);
        setConversationId(undefined);
      }
    } catch {
      setMessages([]);
      setConversationId(undefined);
    }
  }, [fileId, storageKey]);

  // Persist messages & conversationId to localStorage whenever they change
  useEffect(() => {
    if (!fileId) return;
    try {
      const sessionData: SavedChatSession = {
        conversation_id: conversationId,
        messages,
      };
      localStorage.setItem(storageKey, JSON.stringify(sessionData));
    } catch (e) {
      console.error('Failed to save chat session to localStorage:', e);
    }
  }, [fileId, storageKey, conversationId, messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (textToSend?: string) => {
    const messageContent = (textToSend || input).trim();
    if (!messageContent || isLoading || !dataset) return;

    setError(null);
    setInput('');

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: messageContent,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const aiMsgId = `ai-${Date.now()}`;
    const initialAiMsg: ChatMessage = {
      id: aiMsgId,
      sender: 'assistant',
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      toolCalls: [],
      suggestedAction: null,
    };

    setMessages((prev) => [...prev, userMsg, initialAiMsg]);
    setIsLoading(true);

    try {
      const res = await sendChatMessage(
        dataset.file_id,
        messageContent,
        conversationId,
        (chunkText, toolCallsMade, returnedCid, returnedSuggestedAction) => {
          if (returnedCid) setConversationId(returnedCid);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMsgId
                ? {
                    ...msg,
                    text: msg.text + chunkText,
                    toolCalls: toolCallsMade && toolCallsMade.length > 0 ? toolCallsMade : msg.toolCalls,
                    suggestedAction: returnedSuggestedAction !== undefined ? returnedSuggestedAction : msg.suggestedAction,
                  }
                : msg
            )
          );
        }
      );

      if (res.conversation_id) {
        setConversationId(res.conversation_id);
      }

      if (res.status === 'ollama_unavailable' || res.status === 'groq_unavailable') {
        setError({
          message: `${providerDisplayName} assistant is currently unavailable.`,
          guidance: res.response_text || `Please ensure ${providerDisplayName} is properly configured on the server.`,
        });
        setMessages((prev) => prev.filter((msg) => msg.id !== aiMsgId));
        return;
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMsgId
            ? {
                ...msg,
                text: res.response_text || msg.text || 'No response returned from assistant.',
                toolCalls: res.tool_calls_made || msg.toolCalls || [],
                suggestedAction: res.suggested_action !== undefined ? res.suggested_action : msg.suggestedAction,
              }
            : msg
        )
      );
    } catch (err) {
      console.error('Data Chat error:', err);
      setMessages((prev) => prev.filter((msg) => msg.id !== aiMsgId || msg.text.length > 0));
      if (err instanceof ApiError) {
        setError({
          message: err.message,
          guidance: err.userGuidance,
        });
      } else {
        setError({
          message: 'An unexpected error occurred while communicating with the AI chat endpoint.',
          guidance: 'Please ensure your backend server and Ollama instance are running.',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setConversationId(undefined);
    if (fileId) {
      const storageKey = getChatStorageKey(fileId, userId);
      try {
        localStorage.removeItem(storageKey);
      } catch (e) {
        console.error('Failed to clear chat session from localStorage:', e);
      }
    }
  };

  const toggleToolDetails = (msgId: string) => {
    setExpandedTools((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  if (!dataset) {
    return (
      <DatasetEmptyState
        badgeText="AI Assistant"
        icon={Sparkles}
        title="No Dataset Loaded"
        description="Upload a dataset to start asking AI-powered natural language questions and generating automated data insights."
        features={['Natural Language Queries', 'Automated Tool Router', 'Instant Data Insights']}
        onNavigateToUpload={onNavigateToUpload}
      />
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto flex flex-col h-[calc(100vh-6.5rem)] min-h-[550px] bg-surface-card rounded-2xl border border-hairline shadow-sm overflow-hidden theme-transition">
      {/* Workspace Header */}
      <div className="px-6 py-4 border-b border-hairline bg-surface-soft/60 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary text-on-primary flex items-center justify-center shadow-xs">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-title-md text-ink font-semibold">Data Chat Assistant</h2>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-caption text-success bg-success-bg font-medium border border-success/20">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                {providerBadgeText}
              </span>
              {messages.length > 0 && (
                <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] text-muted bg-surface-soft font-medium border border-hairline">
                  <History className="w-3 h-3 text-primary" />
                  History Restored
                </span>
              )}
            </div>
            <p className="text-caption text-muted flex items-center gap-2 mt-0.5">
              <FileSpreadsheet className="w-3.5 h-3.5 text-primary" />
              <span className="font-medium text-ink truncate max-w-[200px]">{dataset.filename}</span>
              <span>•</span>
              <span>{dataset.row_count ? `${dataset.row_count.toLocaleString()} rows` : 'Active'}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-caption font-medium rounded-lg border border-hairline text-muted hover:text-error hover:border-error/30 hover:bg-error-bg/30 transition-all cursor-pointer"
              title="Clear Conversation History"
            >
              <Trash2 className="w-4 h-4" />
              <span>New Chat</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Messages Scroll Container */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 bg-canvas/40">
        {/* Welcome / Empty Conversation State */}
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto my-6 text-center space-y-6">
            <div className="inline-flex p-3 rounded-2xl bg-primary/10 border border-primary/20 mb-2">
              <BrandLogo size={44} />
            </div>
            <div className="space-y-2">
              <h3 className="text-title-lg text-ink font-semibold">Ask anything about your dataset</h3>
              <p className="text-body-sm text-muted max-w-md mx-auto">
                InsightIQ's AI assistant uses {providerDisplayName} tool-calling to directly summarize, profile, and compute dataset metrics on demand.
              </p>
            </div>

            {/* Suggested Prompt Chips */}
            <div className="pt-4">
              <p className="text-caption text-muted font-semibold uppercase tracking-wider mb-3">
                Suggested Prompts
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(prompt)}
                    className="p-3 rounded-xl border border-hairline bg-surface-card hover:border-primary hover:bg-primary-light/30 text-body-sm text-ink font-medium text-left transition-all duration-150 shadow-2xs group flex items-start justify-between cursor-pointer"
                  >
                    <span>{prompt}</span>
                    <Sparkles className="w-4 h-4 text-primary opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2 mt-0.5" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Message History */}
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          const hasToolCalls = msg.toolCalls && msg.toolCalls.length > 0;
          const isExpanded = expandedTools[msg.id];

          return (
            <div
              key={msg.id}
              className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-2xs font-semibold text-caption ${
                  isUser
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface-soft border border-hairline text-primary'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Bubble Body */}
              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-2xs text-body-sm space-y-2 ${
                  isUser
                    ? 'bg-primary text-on-primary rounded-tr-xs'
                    : 'bg-surface-card border border-hairline text-ink rounded-tl-xs'
                }`}
              >
                {/* Tool Invocation Transparency Banner */}
                {hasToolCalls && (
                  <div className="rounded-lg bg-surface-soft/80 border border-hairline p-2 text-caption font-mono text-ink">
                    <button
                      onClick={() => toggleToolDetails(msg.id)}
                      className="w-full flex items-center justify-between gap-2 text-primary font-semibold hover:underline text-left cursor-pointer"
                    >
                      <span className="flex items-center gap-1.5">
                        <Wrench className="w-3.5 h-3.5 text-primary" />
                        Tool Invoked: <code className="bg-primary/10 px-1.5 py-0.5 rounded text-primary">{msg.toolCalls?.join(', ')}</code>
                      </span>
                      {isExpanded ? <ChevronDown className="w-3.5 h-3.5 text-muted" /> : <ChevronRight className="w-3.5 h-3.5 text-muted" />}
                    </button>
                    {isExpanded && (
                      <div className="mt-2 pt-2 border-t border-hairline text-muted text-[11px] font-sans">
                        Executed backend function <code className="font-mono text-ink font-semibold">get_dataset_summary(file_id="{dataset.file_id}")</code> to fetch live dataset summary metrics.
                      </div>
                    )}
                  </div>
                )}

                {/* Message Text */}
                {isUser ? (
                  <div className="whitespace-pre-wrap leading-relaxed">
                    {msg.text}
                  </div>
                ) : (
                  <>
                    <div className="prose prose-sm dark:prose-invert max-w-none text-body-sm leading-relaxed text-ink space-y-1.5 [&_p]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-semibold [&_strong]:text-ink [&_li]:my-0.5">
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                    </div>

                    {/* Inline Tabular Data View for bulleted list summaries */}
                    <InlineMarkdownTable text={msg.text} />
                  </>
                )}

                {/* Inline Rich Visualizations (Live Recharts Visualization in Chat Bubble) */}
                {msg.suggestedAction?.type === 'create_chart' && dataset && (
                  <div className="mt-3 overflow-hidden rounded-2xl border border-hairline bg-surface-card/90 shadow-sm p-1">
                    <RenderedChartCard chartConfig={msg.suggestedAction.payload as unknown as RecommendedChart} fileId={dataset.file_id} />
                  </div>
                )}

                {/* Suggested Action Card / Button for KPIs or additional context */}
                {msg.suggestedAction && msg.suggestedAction.type === 'create_kpi' && (
                  <div className="mt-3 pt-2.5 border-t border-hairline flex flex-col gap-2 bg-surface-soft/80 p-3 rounded-xl border border-hairline">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-caption font-semibold text-ink flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-primary" />
                        Suggested KPI Metric
                      </span>
                      <span className="text-[11px] text-muted font-medium truncate max-w-[180px]">
                        {msg.suggestedAction.payload.kpi_name}
                      </span>
                    </div>

                    <div className="flex items-center justify-between gap-3 pt-1">
                      <div className="flex items-baseline gap-2">
                        <span className="text-lg font-bold text-ink font-mono">
                          {typeof msg.suggestedAction.payload.value === 'number'
                            ? msg.suggestedAction.payload.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                            : msg.suggestedAction.payload.value}
                        </span>
                        {msg.suggestedAction.payload.dax && (
                          <span className="px-1.5 py-0.5 text-[10px] font-mono bg-purple-500/10 text-purple-600 dark:text-purple-400 rounded border border-purple-500/20">
                            {msg.suggestedAction.payload.dax}
                          </span>
                        )}
                      </div>

                      {(() => {
                        const payload = msg.suggestedAction.payload;
                        const itemId = `kpi_chat_${payload.kpi_name || msg.id}`;
                        const isAdded = isInDashboard(itemId);

                        const handleActionClick = () => {
                          if (isAdded) return;
                          addItem({
                            id: itemId,
                            type: 'kpi',
                            kpiData: {
                              kpi_name: payload.kpi_name || 'Chat Metric',
                              value: payload.value,
                              definition: payload.definition || '',
                              required_columns: payload.required_columns || [],
                              calculation_logic: payload.calculation_logic || '',
                              reason: payload.reason || 'Calculated from AI Data Chat',
                              dax: payload.dax || ''
                            }
                          });
                        };

                        return (
                          <button
                            type="button"
                            onClick={handleActionClick}
                            disabled={isAdded}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-caption font-semibold rounded-lg transition-all shadow-2xs shrink-0 cursor-pointer ${
                              isAdded
                                ? 'bg-success/15 text-success border border-success/30 cursor-default'
                                : 'bg-primary text-on-primary hover:bg-primary-active'
                            }`}
                          >
                            {isAdded ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-success" />
                                <span>Added to Dashboard</span>
                              </>
                            ) : (
                              <>
                                <Plus className="w-3.5 h-3.5" />
                                <span>Add to Dashboard</span>
                              </>
                            )}
                          </button>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* Timestamp */}
                <div
                  className={`text-[10px] ${
                    isUser ? 'text-on-primary/75 text-right' : 'text-muted text-left'
                  }`}
                >
                  {msg.timestamp}
                </div>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-surface-soft border border-hairline text-primary flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 animate-bounce" />
            </div>
            <div className="bg-surface-card border border-hairline rounded-2xl rounded-tl-xs px-4 py-3 shadow-2xs flex items-center gap-3 text-body-sm text-muted">
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
              <span>Analyzing dataset with {providerDisplayName}...</span>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="p-4 rounded-xl bg-error-bg border border-error/30 text-error flex items-start gap-3 shadow-xs">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-error" />
            <div className="space-y-1 text-body-sm">
              <p className="font-semibold">{error.message}</p>
              {error.guidance && <p className="text-caption opacity-90">{error.guidance}</p>}
              <div className="pt-2">
                <button
                  onClick={() => handleSend()}
                  className="px-3 py-1 bg-error text-white font-medium text-caption rounded-md hover:bg-error/90 transition-colors cursor-pointer inline-flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3 h-3" />
                  Retry Request
                </button>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Bar */}
      <div className="p-4 border-t border-hairline bg-surface-soft/40 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-end gap-2"
        >
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your dataset (e.g. 'Summarize rows and health score')..."
              rows={1}
              disabled={isLoading}
              className="w-full resize-none rounded-xl border border-hairline bg-surface-card px-4 py-3 text-body-sm text-ink placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60 max-h-32 transition-all"
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-1.5 text-caption text-muted pointer-events-none">
              <span className="hidden sm:inline text-[10px] font-mono">Press Enter ↵</span>
            </div>
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="h-11 px-4 rounded-xl bg-primary text-on-primary font-semibold text-body-sm flex items-center justify-center gap-2 hover:bg-primary-active disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-xs cursor-pointer shrink-0"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};
