from datetime import datetime
from pydantic import BaseModel, Field

from config import get_settings


# --- Config Sub-Schemas ---

class ScrapingConfig(BaseModel):
    max_concurrent: int = 3
    use_playwright: str = "auto"
    respect_robots_txt: bool = True
    rate_limit: float = 2.0

class ProcessingConfig(BaseModel):
    chunk_size: int = 512
    chunk_strategy: str = "recursive"
    chunk_overlap: int = 50

class GenerationConfig(BaseModel):
    template: str = "qa"
    model: str = Field(default_factory=lambda: get_settings().generation_model)
    examples_per_chunk: int = 3
    max_concurrent_llm: int = 5

class QualityConfig(BaseModel):
    min_score: float = 0.7
    checks: list[str] = ["toxicity", "readability", "format"]

class ExportConfig(BaseModel):
    format: str = "jsonl"

class PipelineConfig(BaseModel):
    scraping: ScrapingConfig = ScrapingConfig()
    processing: ProcessingConfig = ProcessingConfig()
    generation: GenerationConfig = GenerationConfig()
    quality: QualityConfig = QualityConfig()
    export: ExportConfig = ExportConfig()


# --- Project ---

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    config: dict | None = None

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict | None = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Job ---

class JobCreate(BaseModel):
    urls: list[str] = Field(..., min_length=1)
    config: PipelineConfig = PipelineConfig()

class JobResponse(BaseModel):
    id: int
    project_id: int
    status: str
    stage: str | None
    config: dict
    progress: float
    error: str | None
    cost_total: float
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Export ---

class ExportResponse(BaseModel):
    id: int
    job_id: int
    format: str
    file_path: str
    record_count: int
    version: str
    dataset_card: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Stats ---

class StatsOverview(BaseModel):
    total_projects: int
    total_jobs: int
    active_jobs: int
    total_examples: int
    total_cost: float
