"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  GitCompareArrows,
  Loader2,
  CheckCircle2,
  BarChart3,
  DollarSign,
  Target,
  ArrowLeft,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Job, JobComparisonItem } from "@/lib/types";

const statusColors: Record<string, { color: string; bg: string }> = {
  pending: { color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
  running: { color: "text-[#00d4ff]", bg: "bg-[#00d4ff]/20" },
  completed: { color: "text-[#00ff88]", bg: "bg-[#00ff88]/20" },
  failed: { color: "text-[#ff3366]", bg: "bg-[#ff3366]/20" },
  cancelled: { color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
};

interface JobWithProject extends Job {
  project_name: string;
}

export default function JobComparePage() {
  // --- State ---
  const [availableJobs, setAvailableJobs] = useState<JobWithProject[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [comparing, setComparing] = useState(false);
  const [results, setResults] = useState<JobComparisonItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // --- Fetch all completed jobs across projects ---
  useEffect(() => {
    let cancelled = false;

    async function fetchJobs() {
      try {
        const projects = await api.getProjects();
        const jobArrays = await Promise.all(
          projects.map(async (p) => {
            const jobs = await api.getJobs(p.id);
            return jobs
              .filter((j) => j.status === "completed")
              .map((j) => ({ ...j, project_name: p.name }));
          })
        );
        if (!cancelled) {
          setAvailableJobs(jobArrays.flat());
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load jobs"
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingJobs(false);
        }
      }
    }

    fetchJobs();
    return () => {
      cancelled = true;
    };
  }, []);

  // --- Handlers ---
  const toggleJob = useCallback((jobId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else if (next.size < 10) {
        next.add(jobId);
      }
      return next;
    });
  }, []);

  const handleCompare = useCallback(async () => {
    if (selectedIds.size < 2) return;
    setComparing(true);
    setError(null);
    setResults(null);

    try {
      const ids = Array.from(selectedIds);
      const data = await api.compareJobs(ids);
      setResults(data.jobs);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Comparison failed"
      );
    } finally {
      setComparing(false);
    }
  }, [selectedIds]);

  // --- Find the best values for highlighting ---
  const bestQuality = results
    ? Math.max(...results.map((r) => r.avg_quality_score))
    : 0;
  const bestPassRate = results
    ? Math.max(...results.map((r) => r.pass_rate))
    : 0;

  // --- Render ---
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/"
          className="mb-4 inline-flex items-center gap-1 text-sm text-[#6b7280] transition-colors hover:text-[#00d4ff]"
        >
          <ArrowLeft className="size-4" />
          Back to Dashboard
        </Link>
        <div className="flex items-center gap-3">
          <GitCompareArrows className="size-7 text-[#00d4ff]" />
          <h1 className="font-mono text-2xl font-bold uppercase tracking-wider text-[#00d4ff] text-glow-cyan">
            Compare Jobs
          </h1>
        </div>
      </div>

      {/* Step 1: Job Selection */}
      <GlassPanel>
        <h2 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
          Step 1 — Select Jobs to Compare
        </h2>

        {loadingJobs ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="size-6 animate-spin text-[#00d4ff]" />
            <span className="ml-2 font-mono text-sm text-[#6b7280]">
              Loading completed jobs...
            </span>
          </div>
        ) : availableJobs.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <p className="font-mono text-sm text-[#6b7280]">
              No completed jobs found. Run some pipelines first.
            </p>
          </div>
        ) : (
          <>
            <p className="mb-3 text-xs text-[#6b7280]">
              Select 2-10 completed jobs to compare ({selectedIds.size}{" "}
              selected)
            </p>
            <div className="space-y-1">
              {availableJobs.map((job) => {
                const isSelected = selectedIds.has(job.id);
                const sc = statusColors[job.status] ?? statusColors.pending;
                return (
                  <label
                    key={job.id}
                    className={`flex cursor-pointer items-center gap-3 rounded px-3 py-2 transition-colors ${
                      isSelected
                        ? "bg-[rgba(0,212,255,0.08)] border border-[rgba(0,212,255,0.3)]"
                        : "bg-[rgba(255,255,255,0.03)] border border-transparent hover:bg-[rgba(255,255,255,0.06)]"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleJob(job.id)}
                      className="size-4 accent-[#00d4ff]"
                    />
                    <span className="font-mono text-sm font-bold text-[#e0e0e0]">
                      Job #{job.id}
                    </span>
                    <Badge
                      className={`${sc.bg} ${sc.color} border-none text-xs`}
                    >
                      {job.status}
                    </Badge>
                    <span className="font-mono text-xs text-[#6b7280]">
                      {job.project_name}
                    </span>
                    <span className="ml-auto font-mono text-xs text-[#ff8c00]">
                      ${job.cost_total.toFixed(4)}
                    </span>
                  </label>
                );
              })}
            </div>
            <div className="mt-4 flex justify-end">
              <Button
                onClick={handleCompare}
                disabled={selectedIds.size < 2 || comparing}
                className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs uppercase tracking-wider disabled:opacity-40"
              >
                {comparing ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <GitCompareArrows className="size-4" />
                )}
                {comparing ? "Comparing..." : "Compare"}
              </Button>
            </div>
          </>
        )}
      </GlassPanel>

      {/* Error */}
      {error && (
        <GlassPanel glow="red">
          <p className="font-mono text-sm text-[#ff3366]">{error}</p>
        </GlassPanel>
      )}

      {/* Step 2: Comparison Results */}
      {results && results.length > 0 && (
        <>
          <div className="flex items-center gap-3">
            <BarChart3 className="size-5 text-[#00d4ff]" />
            <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
              Step 2 — Comparison Results
            </h2>
          </div>

          {/* Side-by-side Job Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {results.map((item) => {
              const sc =
                statusColors[item.status] ?? statusColors.pending;
              const isBestQuality =
                item.avg_quality_score === bestQuality &&
                bestQuality > 0;
              const isBestPass =
                item.pass_rate === bestPassRate && bestPassRate > 0;

              return (
                <GlassPanel
                  key={item.job_id}
                  glow={isBestQuality ? "green" : "none"}
                  className="space-y-4"
                >
                  {/* Card Header */}
                  <div className="flex items-center justify-between">
                    <h3 className="font-mono text-lg font-bold text-[#e0e0e0]">
                      Job #{item.job_id}
                    </h3>
                    <Badge
                      className={`${sc.bg} ${sc.color} border-none text-xs`}
                    >
                      {item.status}
                    </Badge>
                  </div>

                  {/* Template Type */}
                  {item.template_type && (
                    <div className="flex items-center gap-2">
                      <Target className="size-4 text-[#6b7280]" />
                      <span className="font-mono text-xs text-[#6b7280]">
                        {item.template_type}
                      </span>
                    </div>
                  )}

                  {/* Examples */}
                  <div className="space-y-1 rounded bg-[rgba(255,255,255,0.03)] p-3">
                    <div className="flex justify-between font-mono text-xs">
                      <span className="text-[#6b7280]">Total Examples</span>
                      <span className="text-[#e0e0e0]">
                        {item.total_examples}
                      </span>
                    </div>
                    <div className="flex justify-between font-mono text-xs">
                      <span className="text-[#6b7280]">Passed</span>
                      <span className="text-[#00ff88]">
                        <CheckCircle2 className="mr-1 inline size-3" />
                        {item.passed_examples}
                      </span>
                    </div>
                    <div className="flex justify-between font-mono text-xs">
                      <span className="text-[#6b7280]">Failed</span>
                      <span className="text-[#ff3366]">
                        {item.failed_examples}
                      </span>
                    </div>
                  </div>

                  {/* Quality Score Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-[#6b7280]">Quality Score</span>
                      <span
                        className={`font-mono ${
                          isBestQuality
                            ? "text-[#00ff88] font-bold"
                            : "text-[#00d4ff]"
                        }`}
                      >
                        {(item.avg_quality_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-[rgba(255,255,255,0.1)]">
                      <div
                        className={`h-2 rounded-full ${
                          isBestQuality ? "bg-[#00ff88]" : "bg-[#00d4ff]"
                        }`}
                        style={{
                          width: `${item.avg_quality_score * 100}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Pass Rate Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-[#6b7280]">Pass Rate</span>
                      <span
                        className={`font-mono ${
                          isBestPass
                            ? "text-[#00ff88] font-bold"
                            : "text-[#00d4ff]"
                        }`}
                      >
                        {(item.pass_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-[rgba(255,255,255,0.1)]">
                      <div
                        className={`h-2 rounded-full ${
                          isBestPass ? "bg-[#00ff88]" : "bg-[#00d4ff]"
                        }`}
                        style={{ width: `${item.pass_rate * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Cost */}
                  <div className="flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] pt-3">
                    <div className="flex items-center gap-1">
                      <DollarSign className="size-4 text-[#ff8c00]" />
                      <span className="text-xs text-[#6b7280]">Cost</span>
                    </div>
                    <span className="font-mono text-sm font-bold text-[#ff8c00]">
                      ${item.cost_total.toFixed(4)}
                    </span>
                  </div>
                </GlassPanel>
              );
            })}
          </div>

          {/* Aggregated Bar Charts */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Quality Score Comparison */}
            <GlassPanel>
              <h3 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
                <BarChart3 className="mr-2 inline size-4 text-[#00d4ff]" />
                Quality Score Comparison
              </h3>
              <div className="space-y-3">
                {results.map((item) => {
                  const isBest =
                    item.avg_quality_score === bestQuality &&
                    bestQuality > 0;
                  return (
                    <div key={item.job_id} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-mono text-[#e0e0e0]">
                          Job #{item.job_id}
                        </span>
                        <span
                          className={`font-mono ${
                            isBest
                              ? "text-[#00ff88] font-bold"
                              : "text-[#00d4ff]"
                          }`}
                        >
                          {(item.avg_quality_score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-3 rounded-full bg-[rgba(255,255,255,0.1)]">
                        <div
                          className={`h-3 rounded-full transition-all duration-500 ${
                            isBest ? "bg-[#00ff88]" : "bg-[#00d4ff]"
                          }`}
                          style={{
                            width: `${item.avg_quality_score * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassPanel>

            {/* Pass Rate Comparison */}
            <GlassPanel>
              <h3 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
                <Target className="mr-2 inline size-4 text-[#00ff88]" />
                Pass Rate Comparison
              </h3>
              <div className="space-y-3">
                {results.map((item) => {
                  const isBest =
                    item.pass_rate === bestPassRate && bestPassRate > 0;
                  return (
                    <div key={item.job_id} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-mono text-[#e0e0e0]">
                          Job #{item.job_id}
                        </span>
                        <span
                          className={`font-mono ${
                            isBest
                              ? "text-[#00ff88] font-bold"
                              : "text-[#00d4ff]"
                          }`}
                        >
                          {(item.pass_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-3 rounded-full bg-[rgba(255,255,255,0.1)]">
                        <div
                          className={`h-3 rounded-full transition-all duration-500 ${
                            isBest ? "bg-[#00ff88]" : "bg-[#00d4ff]"
                          }`}
                          style={{
                            width: `${item.pass_rate * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassPanel>
          </div>
        </>
      )}
    </div>
  );
}
