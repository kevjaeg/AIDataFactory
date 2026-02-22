"use client";

import { use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Plus,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  DollarSign,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useProject } from "@/hooks/useProjects";
import { useJobs } from "@/hooks/useJobs";

const statusConfig = {
  pending: { icon: Clock, color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
  running: { icon: Loader2, color: "text-[#00d4ff]", bg: "bg-[#00d4ff]/20" },
  completed: { icon: CheckCircle2, color: "text-[#00ff88]", bg: "bg-[#00ff88]/20" },
  failed: { icon: XCircle, color: "text-[#ff3366]", bg: "bg-[#ff3366]/20" },
  cancelled: { icon: XCircle, color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
};

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const projectId = parseInt(id, 10);
  const { project, loading: projectLoading } = useProject(projectId);
  const { jobs, loading: jobsLoading } = useJobs(projectId);

  if (projectLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="size-8 animate-spin text-[#00d4ff]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <Link
          href="/projects"
          className="mb-4 inline-flex items-center gap-1 text-sm text-[#6b7280] transition-colors hover:text-[#00d4ff]"
        >
          <ArrowLeft className="size-4" />
          Back to Projects
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
              {project?.name || `Project #${projectId}`}
            </h1>
            {project?.description && (
              <p className="mt-1 text-sm text-[#6b7280]">
                {project.description}
              </p>
            )}
          </div>
          <Link href={`/projects/${projectId}/new-job`}>
            <Button className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs uppercase tracking-wider">
              <Plus className="size-4" />
              New Job
            </Button>
          </Link>
        </div>
      </div>

      {/* Jobs List */}
      <GlassPanel>
        <h2 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
          Pipeline Jobs
        </h2>
        {jobsLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-16 animate-pulse rounded-md bg-[rgba(255,255,255,0.03)]"
              />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <p className="py-8 text-center text-sm text-[#6b7280]">
            No jobs yet. Start a new pipeline run.
          </p>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => {
              const config = statusConfig[job.status];
              const StatusIcon = config.icon;

              return (
                <Link
                  key={job.id}
                  href={`/jobs/${job.id}`}
                  className="flex items-center gap-4 rounded-md bg-[rgba(255,255,255,0.03)] p-4 transition-all duration-200 hover:bg-[rgba(0,212,255,0.05)] hover:glow-cyan"
                >
                  <StatusIcon
                    className={`size-5 shrink-0 ${config.color} ${job.status === "running" ? "animate-spin" : ""}`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium text-[#e0e0e0]">
                        Job #{job.id}
                      </span>
                      <Badge
                        className={`${config.bg} ${config.color} border-none text-xs`}
                      >
                        {job.status}
                      </Badge>
                      {job.stage && (
                        <span className="font-mono text-xs text-[#6b7280]">
                          Stage: {job.stage}
                        </span>
                      )}
                    </div>
                    {(job.status === "running" || job.status === "pending") && (
                      <div className="mt-2 flex items-center gap-2">
                        <Progress
                          value={job.progress}
                          className="h-1.5 flex-1 bg-[rgba(0,212,255,0.1)]"
                        />
                        <span className="font-mono text-xs text-[#00d4ff]">
                          {job.progress}%
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className="flex items-center gap-1 font-mono text-xs text-[#ff8c00]">
                      <DollarSign className="size-3" />
                      {job.cost_total.toFixed(4)}
                    </span>
                    <span className="text-xs text-[#6b7280]">
                      {new Date(job.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </GlassPanel>
    </div>
  );
}
