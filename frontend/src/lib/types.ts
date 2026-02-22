// Match backend Pydantic schemas

export interface Project {
  id: number;
  name: string;
  description: string | null;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;
  project_id: number;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  stage: string | null;
  config: JobConfig;
  progress: number;
  error: string | null;
  cost_total: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface JobConfig {
  urls: string[];
  scraping?: Record<string, unknown>;
  processing?: Record<string, unknown>;
  generation?: Record<string, unknown>;
  quality?: Record<string, unknown>;
  export?: Record<string, unknown>;
}

export interface Export {
  id: number;
  job_id: number;
  format: string;
  file_path: string;
  record_count: number;
  version: string;
  dataset_card: string | null;
  created_at: string;
}

export interface StatsOverview {
  total_projects: number;
  total_jobs: number;
  active_jobs: number;
  total_examples: number;
  total_cost: number;
}

export interface CostEntry {
  job_id: number;
  project_id: number;
  cost_total: number;
  completed_at: string | null;
}

export interface TemplateInfo {
  name: string;
  template_type: string;
  has_system_prompt: boolean;
}

export interface TemplateDetail extends TemplateInfo {
  system_prompt: string;
  output_schema: Record<string, unknown>;
}

export interface PipelineProgress {
  stage: string;
  progress: number;
  status: "running" | "completed" | "failed";
  error?: string;
}

// --- HuggingFace Push ---

export interface HFPushRequest {
  repo_id: string;
  private: boolean;
}

export interface HFPushResponse {
  repo_id: string;
  url: string;
  files_uploaded: number;
}

// --- Custom Templates ---

export interface CustomTemplate {
  id: number;
  name: string;
  template_type: string;
  system_prompt: string;
  user_prompt_template: string;
  output_schema: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CustomTemplateCreate {
  name: string;
  template_type: string;
  system_prompt: string;
  user_prompt_template: string;
  output_schema?: Record<string, unknown> | null;
}

// --- Job Comparison ---

export interface JobComparisonItem {
  job_id: number;
  status: string;
  template_type: string | null;
  total_examples: number;
  passed_examples: number;
  failed_examples: number;
  avg_quality_score: number;
  cost_total: number;
  pass_rate: number;
}

export interface JobComparison {
  jobs: JobComparisonItem[];
}

// --- Settings ---

export interface SettingsResponse {
  openai_api_key_configured: boolean;
  huggingface_token_configured: boolean;
  generation_model: string;
  generation_max_concurrent: number;
  generation_examples_per_chunk: number;
  quality_min_score: number;
  quality_checks: string[];
  processing_chunk_size: number;
  processing_chunk_strategy: string;
  processing_chunk_overlap: number;
  scraping_max_concurrent: number;
  scraping_rate_limit: number;
  export_format: string;
}
