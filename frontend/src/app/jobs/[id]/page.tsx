"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  DollarSign,
  Clock,
  Calendar,
  XCircle,
  ExternalLink,
  StopCircle,
  RotateCcw,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PipelineVisualizer } from "@/components/dashboard/PipelineVisualizer";
import { useJob } from "@/hooks/useJobs";
import { useSSE } from "@/hooks/useSSE";
import { api } from "@/lib/api";

const statusColors = {
  pending: { color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
  running: { color: "text-[#00d4ff]", bg: "bg-[#00d4ff]/20" },
  completed: { color: "text-[#00ff88]", bg: "bg-[#00ff88]/20" },
  failed: { color: "text-[#ff3366]", bg: "bg-[#ff3366]/20" },
  cancelled: { color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
};

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const jobId = parseInt(id, 10);
  const { job, loading, refetch } = useJob(jobId);
  const { progress, connected } = useSSE(
    job?.status === "running" ? jobId : null
  );

  // Use SSE progress if available, otherwise fallback to polled data
  const currentStage = progress?.stage || job?.stage || null;
  const currentProgress = progress?.progress ?? job?.progress ?? 0;
  const effectiveStatus = progress?.status === "completed" ? "completed" : job?.status ?? "pending";

  const router = useRouter();

  const handleCancel = async () => {
    try {
      await api.cancelJob(jobId);
      refetch();
    } catch {
      // handle error
    }
  };

  const handleRetry = async () => {
    try {
      const newJob = await api.retryJob(jobId);
      router.push(`/jobs/${newJob.id}`);
    } catch {
      // handle error
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="size-8 animate-spin text-[#00d4ff]" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-[#6b7280]">Job not found.</p>
      </div>
    );
  }

  const sc = statusColors[job.status];

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <Link
          href={`/projects/${job.project_id}`}
          className="mb-4 inline-flex items-center gap-1 text-sm text-[#6b7280] transition-colors hover:text-[#00d4ff]"
        >
          <ArrowLeft className="size-4" />
          Back to Project
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
              JOB #{job.id}
            </h1>
            <Badge className={`${sc.bg} ${sc.color} border-none text-xs`}>
              {effectiveStatus}
            </Badge>
            {connected && (
              <span className="flex items-center gap-1">
                <span className="inline-block size-2 animate-pulse rounded-full bg-[#00ff88]" />
                <span className="font-mono text-xs text-[#6b7280]">LIVE</span>
              </span>
            )}
          </div>
          <div className="flex gap-2">
            {job.status === "running" && (
              <Button
                onClick={handleCancel}
                variant="outline"
                className="border-[rgba(255,51,102,0.3)] text-[#ff3366] hover:bg-[rgba(255,51,102,0.1)] font-mono text-xs"
              >
                <StopCircle className="size-4" />
                Cancel
              </Button>
            )}
            {(job.status === "failed" || job.status === "cancelled") && (
              <Button
                onClick={handleRetry}
                variant="outline"
                className="border-[rgba(255,140,0,0.3)] text-[#ff8c00] hover:bg-[rgba(255,140,0,0.1)] font-mono text-xs"
              >
                <RotateCcw className="size-4" />
                Retry
              </Button>
            )}
            {job.status === "completed" && (
              <Link href={`/jobs/${job.id}/results`}>
                <Button className="bg-[#00ff88] text-[#0a0a0f] hover:bg-[#00ff88]/80 font-mono text-xs uppercase tracking-wider">
                  <ExternalLink className="size-4" />
                  View Results
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Pipeline Visualizer - THE HERO */}
      <GlassPanel glow={job.status === "running" ? "cyan" : "none"} className="py-8">
        <h2 className="mb-6 text-center font-mono text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
          Pipeline Progress
        </h2>
        <PipelineVisualizer
          currentStage={currentStage}
          jobStatus={job.status}
          progress={currentProgress}
        />
      </GlassPanel>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <GlassPanel>
          <div className="flex items-center gap-3">
            <DollarSign className="size-5 text-[#ff8c00]" />
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
                Total Cost
              </p>
              <p className="font-mono text-lg font-bold text-[#ff8c00]">
                ${job.cost_total.toFixed(4)}
              </p>
            </div>
          </div>
        </GlassPanel>

        <GlassPanel>
          <div className="flex items-center gap-3">
            <Clock className="size-5 text-[#00d4ff]" />
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
                Current Stage
              </p>
              <p className="font-mono text-lg font-bold text-[#00d4ff]">
                {currentStage || "Queued"}
              </p>
            </div>
          </div>
        </GlassPanel>

        <GlassPanel>
          <div className="flex items-center gap-3">
            <Calendar className="size-5 text-[#e0e0e0]" />
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
                Started
              </p>
              <p className="font-mono text-sm text-[#e0e0e0]">
                {job.started_at
                  ? new Date(job.started_at).toLocaleString()
                  : "Not started"}
              </p>
            </div>
          </div>
        </GlassPanel>

        <GlassPanel>
          <div className="flex items-center gap-3">
            <Calendar className="size-5 text-[#e0e0e0]" />
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
                Completed
              </p>
              <p className="font-mono text-sm text-[#e0e0e0]">
                {job.completed_at
                  ? new Date(job.completed_at).toLocaleString()
                  : "In progress"}
              </p>
            </div>
          </div>
        </GlassPanel>
      </div>

      {/* Error Display */}
      {job.error && (
        <GlassPanel glow="red" className="animate-fade-in">
          <div className="flex items-start gap-3">
            <XCircle className="mt-0.5 size-5 shrink-0 text-[#ff3366]" />
            <div>
              <h3 className="font-mono text-sm font-semibold text-[#ff3366]">
                Pipeline Error
              </h3>
              <p className="mt-1 font-mono text-sm text-[#e0e0e0]/80">
                {job.error}
              </p>
            </div>
          </div>
        </GlassPanel>
      )}

      {/* URLs */}
      <GlassPanel>
        <h2 className="mb-3 font-mono text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
          Target URLs ({job.config.urls.length})
        </h2>
        <div className="space-y-1">
          {job.config.urls.map((url, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded bg-[rgba(255,255,255,0.03)] px-3 py-1.5"
            >
              <span className="font-mono text-xs text-[#6b7280]">
                {i + 1}.
              </span>
              <span className="truncate font-mono text-xs text-[#e0e0e0]">
                {url}
              </span>
            </div>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}
