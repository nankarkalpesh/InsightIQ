export interface ColumnMetadata {
  name: string;
  dtype: string;
}

export interface DatasetMetadataResponse {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  row_count?: number | null;
  column_count?: number | null;
  columns?: ColumnMetadata[] | null;
  sheet_names?: string[] | null;
  selected_sheet?: string | null;
  requires_sheet_selection: boolean;
}

// Overview & Profiling Types
export interface HealthOverview {
  total_rows: number;
  total_columns: number;
  missing_cells: number;
  missing_percentage: number;
  duplicate_rows: number;
  duplicate_percentage: number;
  quality_score: number;
  constant_columns: string[];
  likely_id_columns: string[];
}

export interface ColumnSchemaItem {
  name: string;
  dtype: string;
  unique_count: number;
  null_count: number;
  null_percentage: number;
  sample_value?: any;
}

export interface NumericColumnStats {
  mean?: number | null;
  median?: number | null;
  min?: number | null;
  max?: number | null;
  std?: number | null;
}

export interface CategoricalValueCount {
  value: string;
  count: number;
}

export interface CategoricalColumnStats {
  top_values: CategoricalValueCount[];
}

export interface DatetimeColumnStats {
  min?: string | null;
  max?: string | null;
  range_days?: number | null;
}

export interface ColumnStatisticsResponse {
  numeric: Record<string, NumericColumnStats>;
  categorical: Record<string, CategoricalColumnStats>;
  datetime: Record<string, DatetimeColumnStats>;
}

export interface DatasetOverviewResponse {
  file_id: string;
  health: HealthOverview;
  schema: ColumnSchemaItem[];
  statistics: ColumnStatisticsResponse;
  insights: string[];
}

export interface PaginatedPreviewResponse {
  file_id: string;
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
  data: Record<string, any>[];
}

export interface RecommendedKPI {
  kpi_name: string;
  value: number | string | null;
  definition: string;
  required_columns: string[];
  calculation_logic: string;
  reason: string;
  dax: string;
}

export interface KPIRecommendationResponse {
  file_id: string;
  total_kpis: number;
  message?: string | null;
  kpis: RecommendedKPI[];
}

export interface RecommendedChart {
  chart_type: string;
  title: string;
  x_axis: string;
  y_axis: string;
  legend?: string | null;
  aggregation: string;
  suggested_filters: string[];
  sort: string;
  top_n?: number | null;
  date_granularity?: string | null;
  reason: string;
}

export interface ChartRecommendationResponse {
  file_id: string;
  total_charts: number;
  message?: string | null;
  charts: RecommendedChart[];
}

export interface ChartDataPoint {
  name?: string;
  value?: number;
  x?: number;
  y?: number;
}

export interface ChartDataResponse {
  file_id: string;
  x_axis: string;
  y_axis: string;
  aggregation: string;
  chart_type: string;
  total_points: number;
  data: ChartDataPoint[];
}

export interface TargetCandidate {
  column: string;
  problem_type: string;
  unique_value_count: number;
  raw_unique_value_count?: number | null;
  distribution?: Record<string, any> | null;
  reason: string;
  rank_score: number;
  data_quality_note?: string | null;
}

export interface TargetCandidatesResponse {
  file_id: string;
  total_candidates: number;
  execution_time_ms?: number | null;
  message?: string | null;
  candidates: TargetCandidate[];
}

export interface FeatureCandidate {
  column: string;
  name?: string;
  status: string;
  reason: string;
  data_quality_note?: string | null;
  is_categorical?: boolean;
  distinct_values?: string[];
  min_val?: number | null;
  max_val?: number | null;
  mean_val?: number | null;
}

export interface FeatureCandidatesResponse {
  file_id: string;
  target: string;
  total_features: number;
  recommended_count: number;
  features: FeatureCandidate[];
}

export interface ModelRecommendation {
  model_name: string;
  problem_type: string;
  suitability_score: number;
  why: string;
  advantages: string[];
  limitations: string[];
  recommended_for_baseline: boolean;
}

export interface ModelRecommendationsResponse {
  file_id: string;
  target: string;
  problem_type: string;
  total_models: number;
  data_quality_note?: string | null;
  recommendations: ModelRecommendation[];
}

export interface ConfusionMatrixData {
  labels: string[];
  matrix: number[][];
}

export interface ClassificationMetrics {
  accuracy: number;
  baseline_accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  confusion_matrix: ConfusionMatrixData;
  roc_auc?: number | null;
}

export interface RegressionMetrics {
  mae: number;
  mse: number;
  rmse: number;
  r2: number;
}

export interface FeatureImportanceItem {
  feature: string;
  importance: number;
}

export interface ModelTrainingResponse {
  training_run_id: string;
  file_id: string;
  target: string;
  model_name: string;
  problem_type: string;
  train_row_count: number;
  test_row_count: number;
  training_time_seconds: number;
  classification_metrics?: ClassificationMetrics | null;
  regression_metrics?: RegressionMetrics | null;
  feature_importance: FeatureImportanceItem[];
  data_quality_note?: string | null;
}

export interface ClassProbability {
  label: string;
  probability: number;
}

export interface PredictResponse {
  training_run_id: string;
  problem_type: string;
  predicted_class?: string | null;
  probabilities?: ClassProbability[] | null;
  predicted_value?: number | null;
}


export class ApiError extends Error {
  errorCode: string;
  userGuidance: string;

  constructor(message: string, errorCode: string = 'UNKNOWN_ERROR', userGuidance: string = '') {
    super(message);
    this.name = 'ApiError';
    this.errorCode = errorCode;
    this.userGuidance = userGuidance;
  }
}

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getErrorGuidance(errorCode: string, message: string): string {
  switch (errorCode) {
    case 'UNSUPPORTED_FILE_TYPE':
      return 'This file format is not supported. Please upload a file in .csv, .xlsx, .xls, .json, or .parquet format.';
    case 'EMPTY_FILE':
      return 'The uploaded file contains no data (0 bytes). Please check your data source and select a valid file.';
    case 'CORRUPTED_FILE':
      return 'This file appears corrupted or unparseable. Try re-exporting it from your software and uploading again.';
    case 'SHEET_NOT_FOUND':
      return 'The chosen Excel sheet was not found in the workbook. Please select a valid sheet.';
    case 'FILE_NOT_FOUND':
      return 'The uploaded file reference expired. Please re-upload your dataset.';
    default:
      if (message.toLowerCase().includes('corrupted') || message.toLowerCase().includes('parse')) {
        return 'Try re-exporting your file in a clean format and uploading again.';
      }
      return 'Please verify your file format and content, then try again.';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: any = {};
    try {
      errorData = await response.json();
    } catch {
      // response was not JSON
    }

    const detail = errorData.detail;
    if (typeof detail === 'object' && detail !== null) {
      const code = detail.error_code || 'INGESTION_ERROR';
      const msg = detail.message || 'An error occurred while processing the dataset.';
      const guidance = getErrorGuidance(code, msg);
      throw new ApiError(msg, code, guidance);
    } else if (typeof detail === 'string') {
      const guidance = getErrorGuidance('API_ERROR', detail);
      throw new ApiError(detail, 'API_ERROR', guidance);
    } else {
      const msg = `Server returned HTTP status ${response.status}`;
      throw new ApiError(msg, 'HTTP_ERROR', getErrorGuidance('HTTP_ERROR', msg));
    }
  }

  return response.json();
}

export function getAuthHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...customHeaders };
  try {
    const token = localStorage.getItem('insightiq_auth_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    let guestSessionId = localStorage.getItem('insightiq_guest_session_id');
    if (!guestSessionId) {
      guestSessionId = 'guest_' + Math.random().toString(36).substring(2, 11);
      localStorage.setItem('insightiq_guest_session_id', guestSessionId);
    }
    headers['X-Session-ID'] = guestSessionId;
  } catch (e) {
    // Ignore localStorage errors
  }
  return headers;
}

export async function uploadFile(file: File, sheetName?: string): Promise<DatasetMetadataResponse> {
  const formData = new FormData();
  formData.append('file', file);

  let url = `${API_BASE_URL}/api/upload`;
  if (sheetName) {
    url += `?sheet_name=${encodeURIComponent(sheetName)}`;
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });
    return await handleResponse<DatasetMetadataResponse>(response);
  } catch (error) {
    const isRender = API_BASE_URL.includes('onrender.com');
    const guidance = isRender
      ? 'Render free instances spin down after inactivity and take 30-50 seconds to wake up. Please click "Try Uploading Again" in a few seconds once the backend finishes waking up.'
      : 'Please ensure the InsightIQ backend service is running and accessible.';

    throw new ApiError(
      `Unable to connect to backend server at ${API_BASE_URL}.`,
      'NETWORK_ERROR',
      guidance
    );
  }
}

export async function selectSheet(fileId: string, sheetName: string): Promise<DatasetMetadataResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/upload/select-sheet`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: fileId,
        sheet_name: sheetName,
      }),
    });
    return await handleResponse<DatasetMetadataResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      `Unable to connect to backend server at ${API_BASE_URL}.`,
      'NETWORK_ERROR',
      'Please ensure the InsightIQ backend service is running and accessible.'
    );
  }
}

export async function fetchDatasetOverview(fileId: string): Promise<DatasetOverviewResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/overview`, {
      headers: getAuthHeaders(),
    });
    return await handleResponse<DatasetOverviewResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Unable to load dataset overview statistics.',
      'NETWORK_ERROR',
      'Please ensure the backend server is running and accessible.'
    );
  }
}

export async function fetchDatasetPreview(
  fileId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<PaginatedPreviewResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/preview?page=${page}&page_size=${pageSize}`,
      { headers: getAuthHeaders() }
    );
    return await handleResponse<PaginatedPreviewResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Unable to load dataset preview rows.',
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function fetchDatasetKPIs(fileId: string): Promise<KPIRecommendationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/kpis`, {
      headers: getAuthHeaders(),
    });
    return await handleResponse<KPIRecommendationResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Unable to load KPI recommendations.',
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function fetchDatasetCharts(fileId: string): Promise<ChartRecommendationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/charts`, {
      headers: getAuthHeaders(),
    });
    return await handleResponse<ChartRecommendationResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Unable to load chart recommendations.',
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function fetchChartData(
  fileId: string,
  chart: RecommendedChart
): Promise<ChartDataResponse> {
  const params = new URLSearchParams({
    x_axis: chart.x_axis,
    y_axis: chart.y_axis,
    aggregation: chart.aggregation || 'SUM',
    chart_type: chart.chart_type || 'bar',
  });

  if (chart.top_n) {
    params.append('top_n', chart.top_n.toString());
  }
  if (chart.date_granularity) {
    params.append('date_granularity', chart.date_granularity);
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/chart-data?${params.toString()}`,
      { headers: getAuthHeaders() }
    );
    return await handleResponse<ChartDataResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      `Unable to load chart data for ${chart.title}.`,
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function fetchTargetCandidates(fileId: string): Promise<TargetCandidatesResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/target-candidates`, {
      headers: getAuthHeaders(),
    });
    return await handleResponse<TargetCandidatesResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Unable to load target candidates.',
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function fetchFeatureCandidates(
  fileId: string,
  targetCol: string
): Promise<FeatureCandidatesResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/feature-candidates?target=${encodeURIComponent(targetCol)}`,
      { headers: getAuthHeaders() }
    );
    return await handleResponse<FeatureCandidatesResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      `Unable to load feature candidates for target '${targetCol}'.`,
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function fetchModelRecommendations(
  fileId: string,
  targetCol: string,
  featureCols?: string[]
): Promise<ModelRecommendationsResponse> {
  const params = new URLSearchParams({ target: targetCol });
  if (featureCols && featureCols.length > 0) {
    params.append('features', featureCols.join(','));
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/model-recommendations?${params.toString()}`,
      { headers: getAuthHeaders() }
    );
    return await handleResponse<ModelRecommendationsResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      `Unable to load model recommendations for target '${targetCol}'.`,
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function trainModel(
  fileId: string,
  target: string,
  features: string[],
  modelName: string
): Promise<ModelTrainingResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/train`, {
      method: 'POST',
      headers: getAuthHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        target,
        features,
        model_name: modelName,
      }),
    });
    return await handleResponse<ModelTrainingResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Model training failed.',
      'NETWORK_ERROR',
      'Please check your backend connection and try again.'
    );
  }
}

export async function predictWithModel(
  fileId: string,
  trainingRunId: string,
  inputValues: Record<string, any>
): Promise<PredictResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/predict`, {
      method: 'POST',
      headers: getAuthHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        training_run_id: trainingRunId,
        input_values: inputValues,
      }),
    });
    return await handleResponse<PredictResponse>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Prediction failed.',
      'NETWORK_ERROR',
      'Please check your input values and backend connection.'
    );
  }
}

export function getModelExportUrl(fileId: string, trainingRunId: string): string {
  return `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/export/model?training_run_id=${encodeURIComponent(trainingRunId)}`;
}

export function getPredictionsExportUrl(fileId: string, trainingRunId: string): string {
  return `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/export/predictions?training_run_id=${encodeURIComponent(trainingRunId)}`;
}

export function getMetricsExportUrl(fileId: string, trainingRunId: string): string {
  return `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/export/metrics?training_run_id=${encodeURIComponent(trainingRunId)}`;
}

export function getCodeExportUrl(fileId: string, trainingRunId: string): string {
  return `${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/export/code?training_run_id=${encodeURIComponent(trainingRunId)}`;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface SuggestedAction {
  type: 'create_chart' | 'create_kpi';
  payload: Record<string, any>;
}

export interface ChatResponse {
  conversation_id: string;
  response_text: string;
  tool_calls_made: string[];
  suggested_action?: SuggestedAction | null;
  status?: string;
}

export async function sendChatMessage(
  fileId: string,
  message: string,
  conversationId?: string,
  onChunk?: (chunkText: string, toolCallsMade: string[], cid: string, suggestedAction?: SuggestedAction | null) => void
): Promise<ChatResponse> {
  const useStream = Boolean(onChunk);
  try {
    const response = await fetch(`${API_BASE_URL}/api/dataset/${encodeURIComponent(fileId)}/chat`, {
      method: 'POST',
      headers: getAuthHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        stream: useStream,
      }),
    });

    if (!useStream) {
      return await handleResponse<ChatResponse>(response);
    }

    if (!response.ok) {
      return await handleResponse<ChatResponse>(response);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new ApiError('Streaming not supported by browser reader.', 'STREAMING_ERROR');
    }

    const decoder = new TextDecoder('utf-8');
    let accumulatedText = '';
    let returnedCid = conversationId || '';
    let toolCallsMade: string[] = [];
    let returnedSuggestedAction: SuggestedAction | null = null;
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const jsonStr = trimmed.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            if (data.conversation_id) returnedCid = data.conversation_id;
            if (data.tool_calls_made) toolCallsMade = data.tool_calls_made;
            if ('suggested_action' in data) returnedSuggestedAction = data.suggested_action;
            if (data.chunk || data.done) {
              if (data.chunk) accumulatedText += data.chunk;
              if (onChunk) {
                onChunk(data.chunk || '', toolCallsMade, returnedCid, returnedSuggestedAction);
              }
            }
          } catch {
            // Ignore partial lines
          }
        }
      }
    }

    // Process leftover buffer string if stream finished without a trailing newline
    if (buffer.trim().startsWith('data: ')) {
      const jsonStr = buffer.trim().slice(6);
      try {
        const data = JSON.parse(jsonStr);
        if (data.conversation_id) returnedCid = data.conversation_id;
        if (data.tool_calls_made) toolCallsMade = data.tool_calls_made;
        if ('suggested_action' in data) returnedSuggestedAction = data.suggested_action;
        if (data.chunk) accumulatedText += data.chunk;
        if (onChunk && data.chunk) {
          onChunk(data.chunk, toolCallsMade, returnedCid, returnedSuggestedAction);
        }
      } catch {
        // Ignore malformed JSON
      }
    }

    return {
      conversation_id: returnedCid,
      response_text: accumulatedText,
      tool_calls_made: toolCallsMade,
      suggested_action: returnedSuggestedAction,
      status: 'ok',
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Unable to connect to AI Data Chat endpoint.',
      'NETWORK_ERROR',
      'Please ensure the InsightIQ backend service is running and Ollama is active.'
    );
  }
}

export function formatBytes(bytes: number, decimals: number = 1): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export interface UserAuthInfo {
  id: string;
  email: string;
  display_name: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserAuthInfo;
}

export interface UserDatasetItem {
  file_id: string;
  filename: string;
  file_type: string;
  row_count?: number;
  column_count?: number;
  uploaded_at?: string;
}

export interface ResumeDatasetResponse {
  dataset: DatasetOverviewResponse;
  dashboard_config: any[];
  training_runs: any[];
  chat_history: any[];
}

export async function signupApi(email: string, password: string, displayName?: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName })
  });
  return await handleResponse<AuthResponse>(response);
}

export async function loginApi(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return await handleResponse<AuthResponse>(response);
}

export async function getMeApi(token?: string): Promise<{ user: UserAuthInfo }> {
  const headers = getAuthHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, { headers });
  return await handleResponse<{ user: UserAuthInfo }>(response);
}

export async function getUserDatasetsApi(): Promise<{ datasets: UserDatasetItem[] }> {
  const headers = getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/user/datasets`, { headers });
  return await handleResponse<{ datasets: UserDatasetItem[] }>(response);
}

export async function resumeUserDatasetApi(datasetId: string): Promise<ResumeDatasetResponse> {
  const headers = getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/user/datasets/${datasetId}/resume`, { headers });
  return await handleResponse<ResumeDatasetResponse>(response);
}

export async function saveDashboardConfigApi(datasetId: string, items: any[]): Promise<{ status: string; message: string }> {
  const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
  const response = await fetch(`${API_BASE_URL}/api/user/datasets/${datasetId}/dashboard`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ items })
  });
  return await handleResponse<{ status: string; message: string }>(response);
}

export async function saveDSStateApi(
  datasetId: string,
  targetColumn: string,
  features: string[],
  modelName: string,
  metrics?: Record<string, any>
): Promise<{ status: string; run_id: string; message: string }> {
  const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
  const response = await fetch(`${API_BASE_URL}/api/user/datasets/${datasetId}/ds-state`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      target_column: targetColumn,
      features,
      model_name: modelName,
      metrics: metrics || {}
    })
  });
  return await handleResponse<{ status: string; run_id: string; message: string }>(response);
}

export interface LLMProviderItem {
  id: string;
  name: string;
  configured: boolean;
  status: string;
  details: string;
}

export interface LLMProviderSettingsResponse {
  active_provider: string;
  providers: LLMProviderItem[];
}

export async function fetchLLMProviderSettings(): Promise<LLMProviderSettingsResponse> {
  const headers = getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/settings/llm-provider`, { headers });
  return await handleResponse<LLMProviderSettingsResponse>(response);
}

export async function updateLLMProviderSetting(
  provider: string,
  groqApiKey?: string
): Promise<{ active_provider: string; message: string }> {
  const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
  const payload: Record<string, any> = { provider };
  if (groqApiKey !== undefined) {
    payload.groq_api_key = groqApiKey;
  }
  const response = await fetch(`${API_BASE_URL}/api/settings/llm-provider`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });
  return await handleResponse<{ active_provider: string; message: string }>(response);
}
