"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import type { Job, Project } from "@/lib/types";

const statusConfig = {
  pending: { icon: Clock, color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
  running: { icon: Loader2, color: "text-[#00d4ff]", bg: "bg-[#00d4ff]/20" },
  completed: { icon: CheckCircle2, color: "text-[#00ff88]", bg: "bg-[#00ff88]/20" },
  failed: { icon: XCircle, color: "text-[#ff3366]", bg: "bg-[#ff3366]/20" },
  cancelled: { icon: XCircle, color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
};

export function ActiveJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getProjects(), api.getOverview()])
      .then(async ([projectList]) => {
        setProjects(projectList);
        // Fetch jobs from all projects and merge
        const allJobs: Job[] = [];
        for (const p of projectList) {
          try {
            const pJobs = await api.getJobs(p.id);
            allJobs.push(...pJobs);
          } catch {
            // skip projects that fail
          }
        }
        // Show active jobs (running/pending) first, then recent completed
        const active = allJobs
          .filter((j) => j.status === "running" || j.status === "pending")
          .sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          );
        const recent = allJobs
          .filter((j) => j.status !== "running" && j.status !== "pending")
          .sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          )
          .slice(0, 3);
        setJobs([...active, ...recent]);
      })
      .catch(() => {
        // API not available
      })
      .finally(() => setLoading(false));
  }, []);

  const getProjectName = (projectId: number) => {
    return projects.find((p) => p.id === projectId)?.name || `Project #${projectId}`;
  };

  if (loading) {
    return (
      <GlassPanel className="animate-pulse">
        <h2 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
          Active Jobs
        </h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded-md bg-[rgba(255,255,255,0.03)]"
            />
          ))}
        </div>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel>
      <h2 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
        Active Jobs
      </h2>
      {jobs.length === 0 ? (
        <p className="py-8 text-center text-sm text-[#6b7280]">
          No jobs yet. Create a project and start a pipeline run.
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
                className="flex items-center gap-4 rounded-md bg-[rgba(255,255,255,0.03)] p-3 transition-all duration-200 hover:bg-[rgba(0,212,255,0.05)] hover:glow-cyan"
              >
                <StatusIcon
                  className={`size-5 shrink-0 ${config.color} ${job.status === "running" ? "animate-spin" : ""}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-mono text-sm font-medium text-[#e0e0e0]">
                      Job #{job.id}
                    </span>
                    <span className="truncate text-xs text-[#6b7280]">
                      {getProjectName(job.project_id)}
                    </span>
                  </div>
                  {(job.status === "running" || job.status === "pending") && (
                    <div className="mt-1.5 flex items-center gap-2">
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
                <div className="flex items-center gap-2">
                  {job.stage && (
                    <span className="font-mono text-xs text-[#6b7280]">
                      {job.stage}
                    </span>
                  )}
                  <Badge
                    className={`${config.bg} ${config.color} border-none text-xs`}
                  >
                    {job.status}
                  </Badge>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </GlassPanel>
  );
}
