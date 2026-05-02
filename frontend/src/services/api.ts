const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const API_ROOT_URL = API_BASE_URL.replace(/\/api\/?$/, '');
const TOKEN_STORAGE_KEY = 'medsimplify_auth_token';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload?.detail || payload?.error || detail;
    } catch {
      // Fall back to the generic message above.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export interface UploadResponse {
  file_id: string;
  filename: string;
  saved_as: string;
  file_path: string;
  size: number;
  status: string;
}

export interface EntityResult {
  text: string;
  label: string;
  start: number;
  end: number;
  source: string;
}

export interface StructuredData {
  raw_text: string;
  entities: EntityResult[];
  extracted_values: Array<Record<string, string>>;
  structured_tests: TestResult[];
  abnormal_count: number;
  sections?: Record<string, string>;
  narrative_findings?: Array<Record<string, string>>;
  medications?: EntityResult[];
  conditions?: EntityResult[];
  anatomy?: EntityResult[];
  visual_overlays?: VisualOverlayPage[];
}

export interface VisualHighlight {
  text: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  style: 'entity' | 'abnormal';
}

export interface VisualOverlayPage {
  page_number: number;
  width: number;
  height: number;
  preview_available: boolean;
  highlight_count: number;
  highlights: VisualHighlight[];
}

export interface ReadabilityMetrics {
  flesch_reading_ease: number;
  flesch_kincaid_grade: number;
  average_sentence_length: number;
  average_syllables_per_word: number;
  word_count: number;
  sentence_count: number;
}

export interface ProcessEvaluation {
  readability: ReadabilityMetrics;
  extraction: {
    entities_found: number;
    tests_found: number;
    abnormal_tests: number;
  };
}

export interface TestResult {
  test_name: string;
  value: string;
  unit: string;
  normal_range?: {
    min: number;
    max: number;
    unit: string;
  };
  status: string;
  risk_level: number;
  confidence: number;
  explanation: string;
  retrieved_sources: string[];
  llm_model: string;
}

export interface SimplifiedOutput {
  summary: string;
  tests: TestResult[];
  normal_tests?: TestResult[];
  abnormal_tests: TestResult[];
  abnormal_count: number;
  total_tests: number;
  normal_count?: number;
  reassuring_summary?: string;
  concerns_summary?: string;
  glossary: Record<string, string>;
  report_explanation: string;
  follow_up_questions: string[];
}

export interface ReportMetadata {
  id: string;
  original_filename: string;
  status: string;
  document_type?: string | null;
  abnormal_count: number;
  created_at: string;
  processed_at?: string | null;
  readability_score?: number | null;
}

export interface ProcessResponse {
  report_id?: string;
  file_path: string;
  status: string;
  document_type?: string;
  stages: Record<string, unknown>;
  errors: string[];
  raw_text?: string;
  structured_data?: StructuredData;
  evaluation?: ProcessEvaluation;
  simplified_output?: SimplifiedOutput;
  report_metadata?: ReportMetadata | null;
}

export interface ReportRecord extends ReportMetadata {
  file_path?: string;
  mime_type?: string | null;
  size?: number;
  raw_text?: string | null;
  structured_data?: StructuredData | null;
  simplified_output?: SimplifiedOutput | null;
  processing_result?: ProcessResponse | null;
  evaluation?: ProcessEvaluation | null;
  error_message?: string | null;
}

export interface JobRecord {
  job_id: string;
  kind: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message?: string | null;
  metadata?: Record<string, unknown>;
  result?: ProcessResponse | null;
  error?: string | null;
}

export interface FeedbackPayload {
  comprehension_score?: number;
  usefulness_score?: number;
  highlighting_score?: number;
  recommendation_score?: number;
  comments?: string;
}

export interface AuthUser {
  id: number;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  user: AuthUser;
  access_token: string;
  token_type: string;
}

export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  return request<UploadResponse>('/upload', {
    method: 'POST',
    body: formData,
  });
};

export const processReport = async (fileId: string): Promise<ProcessResponse> =>
  request<ProcessResponse>(`/process/${fileId}`, { method: 'POST' });

export const startProcessReportJob = async (fileId: string): Promise<JobRecord> =>
  request<JobRecord>(`/process/${fileId}/async`, { method: 'POST' });

export const getJob = async (jobId: string): Promise<JobRecord> =>
  request<JobRecord>(`/jobs/${jobId}`);

export const listReports = async (): Promise<ReportRecord[]> => {
  const payload = await request<{ reports: ReportRecord[] }>('/reports');
  return payload.reports;
};

export const getReport = async (reportId: string): Promise<ReportRecord> =>
  request<ReportRecord>(`/reports/${reportId}`);

export const getReportFileUrl = (reportId: string) =>
  buildAssetUrl(`${API_ROOT_URL}/api/reports/${reportId}/file`);

export const getReportPagePreviewUrl = (reportId: string, pageNumber: number) =>
  buildAssetUrl(`${API_ROOT_URL}/api/reports/${reportId}/pages/${pageNumber}/preview`);

export const deleteReport = async (reportId: string) =>
  request(`/reports/${reportId}`, { method: 'DELETE' });

export const submitFeedback = async (reportId: string, payload: FeedbackPayload) =>
  request(`/reports/${reportId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const listFeedback = async (reportId: string) =>
  request(`/reports/${reportId}/feedback`);

export const evaluateSimplification = async (referenceText: string, candidateText: string) =>
  request('/evaluation/simplification', {
    method: 'POST',
    body: JSON.stringify({
      reference_text: referenceText,
      candidate_text: candidateText,
    }),
  });

export const checkHealth = async () => request('/health');

export const registerUser = async (email: string, password: string) =>
  request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

export const loginUser = async (email: string, password: string) =>
  request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

export const getCurrentUser = async () => request<AuthUser>('/auth/me');

function buildAssetUrl(baseUrl: string) {
  const token = getStoredToken();
  if (!token) return baseUrl;
  const url = new URL(baseUrl, window.location.origin);
  url.searchParams.set('access_token', token);
  return url.toString();
}
