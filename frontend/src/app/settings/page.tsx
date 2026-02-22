"use client";

import { useState, useEffect } from "react";
import {
  Key,
  Save,
  Globe,
  FileText,
  Sparkles,
  Shield,
  Package,
  Server,
  Loader2,
  RotateCcw,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import type { SettingsResponse } from "@/lib/types";

const STORAGE_KEY = "adf-settings-overrides";

const COMMON_MODELS = [
  "gpt-4o-mini",
  "gpt-4o",
  "gpt-4-turbo",
  "gpt-3.5-turbo",
  "claude-3-5-sonnet-20241022",
  "claude-3-haiku-20240307",
];

interface SettingsOverrides {
  generation_model?: string;
  generation_max_concurrent?: number;
  generation_examples_per_chunk?: number;
  quality_min_score?: number;
  quality_checks?: string[];
  processing_chunk_size?: number;
  processing_chunk_strategy?: string;
  processing_chunk_overlap?: number;
  scraping_max_concurrent?: number;
  scraping_rate_limit?: number;
  export_format?: string;
}

function loadOverrides(): SettingsOverrides {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveOverrides(overrides: SettingsOverrides) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

export default function SettingsPage() {
  const [apiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // API key status from backend
  const [openaiConfigured, setOpenaiConfigured] = useState(false);
  const [hfConfigured, setHfConfigured] = useState(false);

  // Editable settings (merged: API defaults + localStorage overrides)
  const [model, setModel] = useState("gpt-4o-mini");
  const [maxConcurrentGen, setMaxConcurrentGen] = useState(3);
  const [examplesPerChunk, setExamplesPerChunk] = useState(5);
  const [minScore, setMinScore] = useState(0.7);
  const [qualityChecks, setQualityChecks] = useState("all");
  const [chunkSize, setChunkSize] = useState(512);
  const [chunkStrategy, setChunkStrategy] = useState("fixed");
  const [chunkOverlap, setChunkOverlap] = useState(50);
  const [scrapingConcurrent, setScrapingConcurrent] = useState(3);
  const [scrapingRateLimit, setScrapingRateLimit] = useState(2);
  const [exportFormat, setExportFormat] = useState("jsonl");

  // Store the original API defaults so we can reset
  const [apiDefaults, setApiDefaults] = useState<SettingsResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchSettings() {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getSettings();
        if (cancelled) return;

        setApiDefaults(data);
        setOpenaiConfigured(data.openai_api_key_configured);
        setHfConfigured(data.huggingface_token_configured);

        // Merge with localStorage overrides
        const overrides = loadOverrides();

        setModel(overrides.generation_model ?? data.generation_model);
        setMaxConcurrentGen(overrides.generation_max_concurrent ?? data.generation_max_concurrent);
        setExamplesPerChunk(overrides.generation_examples_per_chunk ?? data.generation_examples_per_chunk);
        setMinScore(overrides.quality_min_score ?? data.quality_min_score);
        setQualityChecks(
          overrides.quality_checks
            ? overrides.quality_checks.join(", ")
            : data.quality_checks.join(", ")
        );
        setChunkSize(overrides.processing_chunk_size ?? data.processing_chunk_size);
        setChunkStrategy(overrides.processing_chunk_strategy ?? data.processing_chunk_strategy);
        setChunkOverlap(overrides.processing_chunk_overlap ?? data.processing_chunk_overlap);
        setScrapingConcurrent(overrides.scraping_max_concurrent ?? data.scraping_max_concurrent);
        setScrapingRateLimit(overrides.scraping_rate_limit ?? data.scraping_rate_limit);
        setExportFormat(overrides.export_format ?? data.export_format);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load settings");

        // Still apply localStorage overrides even if API fails
        const overrides = loadOverrides();
        if (overrides.generation_model) setModel(overrides.generation_model);
        if (overrides.generation_max_concurrent != null) setMaxConcurrentGen(overrides.generation_max_concurrent);
        if (overrides.generation_examples_per_chunk != null) setExamplesPerChunk(overrides.generation_examples_per_chunk);
        if (overrides.quality_min_score != null) setMinScore(overrides.quality_min_score);
        if (overrides.quality_checks) setQualityChecks(overrides.quality_checks.join(", "));
        if (overrides.processing_chunk_size != null) setChunkSize(overrides.processing_chunk_size);
        if (overrides.processing_chunk_strategy) setChunkStrategy(overrides.processing_chunk_strategy);
        if (overrides.processing_chunk_overlap != null) setChunkOverlap(overrides.processing_chunk_overlap);
        if (overrides.scraping_max_concurrent != null) setScrapingConcurrent(overrides.scraping_max_concurrent);
        if (overrides.scraping_rate_limit != null) setScrapingRateLimit(overrides.scraping_rate_limit);
        if (overrides.export_format) setExportFormat(overrides.export_format);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchSettings();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = () => {
    const checksArray = qualityChecks
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const overrides: SettingsOverrides = {
      generation_model: model,
      generation_max_concurrent: maxConcurrentGen,
      generation_examples_per_chunk: examplesPerChunk,
      quality_min_score: minScore,
      quality_checks: checksArray,
      processing_chunk_size: chunkSize,
      processing_chunk_strategy: chunkStrategy,
      processing_chunk_overlap: chunkOverlap,
      scraping_max_concurrent: scrapingConcurrent,
      scraping_rate_limit: scrapingRateLimit,
      export_format: exportFormat,
    };

    saveOverrides(overrides);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    localStorage.removeItem(STORAGE_KEY);

    if (apiDefaults) {
      setModel(apiDefaults.generation_model);
      setMaxConcurrentGen(apiDefaults.generation_max_concurrent);
      setExamplesPerChunk(apiDefaults.generation_examples_per_chunk);
      setMinScore(apiDefaults.quality_min_score);
      setQualityChecks(apiDefaults.quality_checks.join(", "));
      setChunkSize(apiDefaults.processing_chunk_size);
      setChunkStrategy(apiDefaults.processing_chunk_strategy);
      setChunkOverlap(apiDefaults.processing_chunk_overlap);
      setScrapingConcurrent(apiDefaults.scraping_max_concurrent);
      setScrapingRateLimit(apiDefaults.scraping_rate_limit);
      setExportFormat(apiDefaults.export_format);
    }

    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const inputClass =
    "h-8 border-[rgba(0,212,255,0.15)] bg-[rgba(255,255,255,0.03)] font-mono text-xs text-[#e0e0e0] focus:border-[#00d4ff]";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
          SETTINGS
        </h1>
        <p className="mt-1 text-sm text-[#6b7280]">
          Configure your AI Data Factory instance
        </p>
      </div>

      {/* Loading State */}
      {loading && (
        <GlassPanel>
          <div className="flex items-center justify-center gap-3 py-8">
            <Loader2 className="size-5 text-[#00d4ff] animate-spin" />
            <span className="font-mono text-sm text-[#6b7280]">
              Loading settings from backend...
            </span>
          </div>
        </GlassPanel>
      )}

      {/* Error State */}
      {error && (
        <GlassPanel glow="red">
          <div className="flex items-center gap-2">
            <XCircle className="size-4 text-red-400" />
            <span className="font-mono text-xs text-red-400">
              {error} &mdash; showing local/default values
            </span>
          </div>
        </GlassPanel>
      )}

      {!loading && (
        <>
          {/* API Key Status */}
          <GlassPanel>
            <div className="flex items-center gap-2 mb-4">
              <Key className="size-4 text-[#00d4ff]" />
              <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
                API Key Status
              </h2>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-md border border-[rgba(0,212,255,0.1)] px-4 py-3">
                <div className="flex items-center gap-3">
                  <Sparkles className="size-4 text-[#e0e0e0] opacity-60" />
                  <span className="font-mono text-xs text-[#e0e0e0]">
                    OpenAI API Key
                  </span>
                </div>
                {openaiConfigured ? (
                  <Badge className="bg-[rgba(0,255,136,0.15)] text-[#00ff88] border-[rgba(0,255,136,0.3)] font-mono text-[10px] uppercase tracking-wider">
                    <CheckCircle2 className="size-3" />
                    Configured
                  </Badge>
                ) : (
                  <Badge className="bg-[rgba(255,68,68,0.15)] text-[#ff4444] border-[rgba(255,68,68,0.3)] font-mono text-[10px] uppercase tracking-wider">
                    <XCircle className="size-3" />
                    Not Set
                  </Badge>
                )}
              </div>
              <div className="flex items-center justify-between rounded-md border border-[rgba(0,212,255,0.1)] px-4 py-3">
                <div className="flex items-center gap-3">
                  <Package className="size-4 text-[#e0e0e0] opacity-60" />
                  <span className="font-mono text-xs text-[#e0e0e0]">
                    HuggingFace Token
                  </span>
                </div>
                {hfConfigured ? (
                  <Badge className="bg-[rgba(0,255,136,0.15)] text-[#00ff88] border-[rgba(0,255,136,0.3)] font-mono text-[10px] uppercase tracking-wider">
                    <CheckCircle2 className="size-3" />
                    Configured
                  </Badge>
                ) : (
                  <Badge className="bg-[rgba(255,68,68,0.15)] text-[#ff4444] border-[rgba(255,68,68,0.3)] font-mono text-[10px] uppercase tracking-wider">
                    <XCircle className="size-3" />
                    Not Set
                  </Badge>
                )}
              </div>
              <p className="text-[10px] text-[#6b7280] font-mono">
                API keys are configured via environment variables on the backend.
                They cannot be set from the UI.
              </p>
            </div>
          </GlassPanel>

          {/* API Configuration */}
          <GlassPanel>
            <div className="flex items-center gap-2 mb-4">
              <Server className="size-4 text-[#00d4ff]" />
              <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
                API Configuration
              </h2>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[#6b7280]">
                Backend API URL
              </label>
              <Input
                value={apiUrl}
                disabled
                className="border-[rgba(0,212,255,0.2)] bg-[rgba(255,255,255,0.05)] font-mono text-sm text-[#e0e0e0] placeholder:text-[#6b7280] focus:border-[#00d4ff] disabled:opacity-50"
              />
              <p className="mt-1 text-[10px] text-[#6b7280] font-mono">
                Set via NEXT_PUBLIC_API_URL environment variable
              </p>
            </div>
          </GlassPanel>

          {/* Pipeline Stage Configuration */}
          <GlassPanel>
            <div className="flex items-center gap-2 mb-4">
              <Key className="size-4 text-[#ff8c00]" />
              <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#ff8c00]">
                Pipeline Configuration
              </h2>
            </div>
            <div className="space-y-4">
              {/* Spider (Scraping) */}
              <div className="rounded-md border border-[rgba(0,212,255,0.1)] p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Globe className="size-4 text-[#00d4ff] opacity-60" />
                  <span className="font-mono text-xs font-medium text-[#e0e0e0]">
                    Spider (Scraping)
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Max Concurrent
                    </label>
                    <Input
                      type="number"
                      value={scrapingConcurrent}
                      onChange={(e) =>
                        setScrapingConcurrent(Number(e.target.value))
                      }
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Rate Limit (req/s)
                    </label>
                    <Input
                      type="number"
                      step="0.1"
                      value={scrapingRateLimit}
                      onChange={(e) =>
                        setScrapingRateLimit(Number(e.target.value))
                      }
                      className={inputClass}
                    />
                  </div>
                </div>
              </div>

              {/* Refiner (Processing) */}
              <div className="rounded-md border border-[rgba(0,212,255,0.1)] p-4">
                <div className="mb-3 flex items-center gap-2">
                  <FileText className="size-4 text-[#00d4ff] opacity-60" />
                  <span className="font-mono text-xs font-medium text-[#e0e0e0]">
                    Refiner (Processing)
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Chunk Size (tokens)
                    </label>
                    <Input
                      type="number"
                      value={chunkSize}
                      onChange={(e) => setChunkSize(Number(e.target.value))}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Overlap (tokens)
                    </label>
                    <Input
                      type="number"
                      value={chunkOverlap}
                      onChange={(e) => setChunkOverlap(Number(e.target.value))}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Strategy
                    </label>
                    <Select
                      value={chunkStrategy}
                      onValueChange={setChunkStrategy}
                    >
                      <SelectTrigger className="h-8 w-full border-[rgba(0,212,255,0.15)] bg-[rgba(255,255,255,0.03)] font-mono text-xs text-[#e0e0e0]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1a1a2e] border-[rgba(0,212,255,0.2)]">
                        <SelectItem value="fixed" className="font-mono text-xs text-[#e0e0e0]">
                          fixed
                        </SelectItem>
                        <SelectItem value="semantic" className="font-mono text-xs text-[#e0e0e0]">
                          semantic
                        </SelectItem>
                        <SelectItem value="sentence" className="font-mono text-xs text-[#e0e0e0]">
                          sentence
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Factory (Generation) */}
              <div className="rounded-md border border-[rgba(0,212,255,0.1)] p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles className="size-4 text-[#00d4ff] opacity-60" />
                  <span className="font-mono text-xs font-medium text-[#e0e0e0]">
                    Factory (Generation)
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Model
                    </label>
                    <Select value={model} onValueChange={setModel}>
                      <SelectTrigger className="h-8 w-full border-[rgba(0,212,255,0.15)] bg-[rgba(255,255,255,0.03)] font-mono text-xs text-[#e0e0e0]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1a1a2e] border-[rgba(0,212,255,0.2)]">
                        {COMMON_MODELS.map((m) => (
                          <SelectItem
                            key={m}
                            value={m}
                            className="font-mono text-xs text-[#e0e0e0]"
                          >
                            {m}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Max Concurrent
                    </label>
                    <Input
                      type="number"
                      value={maxConcurrentGen}
                      onChange={(e) =>
                        setMaxConcurrentGen(Number(e.target.value))
                      }
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Examples / Chunk
                    </label>
                    <Input
                      type="number"
                      value={examplesPerChunk}
                      onChange={(e) =>
                        setExamplesPerChunk(Number(e.target.value))
                      }
                      className={inputClass}
                    />
                  </div>
                </div>
              </div>

              {/* Inspector (Quality) */}
              <div className="rounded-md border border-[rgba(0,212,255,0.1)] p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Shield className="size-4 text-[#00d4ff] opacity-60" />
                  <span className="font-mono text-xs font-medium text-[#e0e0e0]">
                    Inspector (Quality)
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Min Quality Score
                    </label>
                    <Input
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={minScore}
                      onChange={(e) => setMinScore(Number(e.target.value))}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Quality Checks
                    </label>
                    <Input
                      value={qualityChecks}
                      onChange={(e) => setQualityChecks(e.target.value)}
                      placeholder="all, or comma-separated list"
                      className={inputClass}
                    />
                  </div>
                </div>
              </div>

              {/* Shipper (Export) */}
              <div className="rounded-md border border-[rgba(0,212,255,0.1)] p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Package className="size-4 text-[#00d4ff] opacity-60" />
                  <span className="font-mono text-xs font-medium text-[#e0e0e0]">
                    Shipper (Export)
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      Default Format
                    </label>
                    <Select value={exportFormat} onValueChange={setExportFormat}>
                      <SelectTrigger className="h-8 w-full border-[rgba(0,212,255,0.15)] bg-[rgba(255,255,255,0.03)] font-mono text-xs text-[#e0e0e0]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1a1a2e] border-[rgba(0,212,255,0.2)]">
                        <SelectItem value="jsonl" className="font-mono text-xs text-[#e0e0e0]">
                          jsonl
                        </SelectItem>
                        <SelectItem value="parquet" className="font-mono text-xs text-[#e0e0e0]">
                          parquet
                        </SelectItem>
                        <SelectItem value="csv" className="font-mono text-xs text-[#e0e0e0]">
                          csv
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>
          </GlassPanel>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Button
              onClick={handleSave}
              className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs uppercase tracking-wider"
            >
              <Save className="size-4" />
              Save Settings
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              className="border-[rgba(0,212,255,0.3)] text-[#00d4ff] hover:bg-[rgba(0,212,255,0.1)] font-mono text-xs uppercase tracking-wider"
            >
              <RotateCcw className="size-4" />
              Reset to Defaults
            </Button>
            {saved && (
              <span className="animate-fade-in font-mono text-xs text-[#00ff88]">
                Settings saved successfully.
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
