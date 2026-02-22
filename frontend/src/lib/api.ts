import type {
  Project,
  Job,
  Export,
  StatsOverview,
  CostEntry,
  TemplateInfo,
  TemplateDetail,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Projects
  getProjects: () => request<Project[]>("/api/projects"),
  getProject: (id: number) => request<Project>(`/api/projects/${id}`),
  createProject: (data: { name: string; description?: string }) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteProject: (id: number) =>
    request<void>(`/api/projects/${id}`, { method: "DELETE" }),

  // Jobs
  getJobs: (projectId: number) =>
    request<Job[]>(`/api/projects/${projectId}/jobs`),
  getJob: (id: number) => request<Job>(`/api/jobs/${id}`),
  createJob: (
    projectId: number,
    data: { urls: string[]; config?: Record<string, unknown> }
  ) =>
    request<Job>(`/api/projects/${projectId}/jobs`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  cancelJob: (id: number) =>
    request<Job>(`/api/jobs/${id}/cancel`, { method: "POST" }),

  // Exports
  getExports: (jobId: number) =>
    request<Export[]>(`/api/jobs/${jobId}/exports`),
  getDatasetCard: (exportId: number) =>
    fetch(`${API_BASE}/api/exports/${exportId}/card`).then((r) => r.text()),
  getDownloadUrl: (exportId: number) =>
    `${API_BASE}/api/exports/${exportId}/download`,

  // Stats
  getOverview: () => request<StatsOverview>("/api/stats/overview"),
  getCosts: (limit?: number) =>
    request<CostEntry[]>(
      `/api/stats/costs${limit ? `?limit=${limit}` : ""}`
    ),

  // Templates
  getTemplates: () => request<TemplateInfo[]>("/api/templates"),
  getTemplate: (type: string) =>
    request<TemplateDetail>(`/api/templates/${type}`),
};
