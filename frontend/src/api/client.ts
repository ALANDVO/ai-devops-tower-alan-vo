const BASE_URL = '/api';

export interface User {
  email: string;
  role: string;
  permissions: string[];
}

export interface Pipeline {
  pipeline_id: string;
  service: string;
  stages: string[];
  last_build: any;
  build_count: number;
}

export interface Build {
  build_id: string;
  pipeline_id: string;
  service: string;
  branch: string;
  commit_sha: string;
  triggered_by: string;
  status: string;
  stages: any[];
  created_at: number;
  failed_stages?: string[];
  duration_seconds?: number;
}

export interface SLO {
  slo_id: string;
  service: string;
  name: string;
  objective: number;
  window_days: number;
}

export interface SLOBudget {
  slo_id: string;
  service: string;
  name: string;
  objective: number;
  actual_reliability: number;
  error_budget_remaining: number;
  budget_percentage: number;
  status: string;
}

export interface SLOBurnRate {
  slo_id: string;
  service: string;
  burn_rate: number;
  window: string;
  failures_in_window: number;
  total_in_window: number;
  thresholds: any[];
  active_alerts: any[];
  severity: string;
  objective: number;
}

export interface Incident {
  incident_id: string;
  title: string;
  severity: string;
  service: string;
  status: string;
  description: string;
  created_at: number;
  resolved_at: number | null;
  events: any[];
  root_cause: string | null;
  postmortem: string | null;
  on_call: string;
  duration_minutes?: number;
}

export interface Release {
  release_id: string;
  service: string;
  version: string;
  status: string;
  description: string;
  changelog: string[];
  created_at: number;
  notes: string | null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('devops_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || resp.statusText);
  }
  return resp.json();
}

export const api = {
  // Auth
  login: (email: string, role: string) =>
    request<{ access_token: string; token_type: string; expires_in: number }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, role }),
    }),
  me: () => request<User>('/auth/me'),

  // Pipelines
  pipelines: () => request<{ pipelines: Pipeline[]; count: number }>('/pipelines'),
  pipeline: (id: string) => request<Pipeline>(`/pipelines/${id}`),
  triggerPipeline: (id: string, branch?: string) =>
    request<{ build_id: string; status: string }>(`/pipelines/${id}/trigger`, { method: 'POST', body: JSON.stringify({ branch }) }),

  // Builds
  builds: (params?: { pipeline_id?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.pipeline_id) qs.set('pipeline_id', params.pipeline_id);
    if (params?.status) qs.set('status', params.status);
    const q = qs.toString();
    return request<{ builds: Build[]; count: number }>(`/builds${q ? '?' + q : ''}`);
  },
  build: (id: string) => request<Build>(`/builds/${id}`),
  analyzeBuild: (id: string) => request<{ build_id: string; analysis: string }>(`/builds/${id}/analyze`, { method: 'POST' }),

  // SLO
  slos: () => request<{ slos: SLO[]; count: number }>('/slo'),
  sloBudget: (id: string) => request<SLOBudget>(`/slo/${id}/budget`),
  sloBurnRate: (id: string) => request<SLOBurnRate>(`/slo/${id}/burn-rate`),

  // Incidents
  incidents: (params?: { severity?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.severity) qs.set('severity', params.severity);
    if (params?.status) qs.set('status', params.status);
    const q = qs.toString();
    return request<{ incidents: Incident[]; count: number }>(`/incidents${q ? '?' + q : ''}`);
  },
  createIncident: (data: any) =>
    request<Incident>('/incidents', { method: 'POST', body: JSON.stringify(data) }),
  analyzeIncident: (id: string) =>
    request<{ incident_id: string; root_cause: string }>(`/incidents/${id}/analyze`, { method: 'POST' }),
  postmortem: (id: string) =>
    request<{ incident_id: string; postmortem: string }>(`/incidents/${id}/postmortem`, { method: 'POST' }),
  releases: (params?: { service?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.service) qs.set('service', params.service);
    if (params?.status) qs.set('status', params.status);
    const q = qs.toString();
    return request<{ releases: Release[]; count: number }>(`/releases${q ? '?' + q : ''}`);
  },
  release: (id: string) => request<Release>(`/releases/${id}`),
  generateNotes: (id: string) =>
    request<{ release_id: string; notes: string }>(`/releases/${id}/notes`, { method: 'POST' }),
  promoteRelease: (id: string, environment: string) =>
    request<{ release_id: string; status: string; environment: string }>(`/releases/${id}/promote`, { method: 'POST', body: JSON.stringify({ environment }) }),

  // Alerts
  alerts: () => request<{ alerts: any[]; count: number }>('/alerts'),

  // Health
  health: () => request<{ status: string; service: string; version: string }>('/health'),
};
