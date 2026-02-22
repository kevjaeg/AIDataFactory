"use client";

import Link from "next/link";
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { Job } from "@/lib/types";

const statusConfig = {
  pending: { icon: Clock, color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
  running: { icon: Loader2, color: "text-[#00d4ff]", bg: "bg-[#00d4ff]/20" },
  completed: { icon: CheckCircle2, color: "text-[#00ff88]", bg: "bg-[#00ff88]/20" },
  failed: { icon: XCircle, color: "text-[#ff3366]", bg: "bg-[#ff3366]/20" },
  cancelled: { icon: XCircle, color: "text-[#6b7280]", bg: "bg-[#6b7280]/20" },
};

interface JobProgressCardProps {
  job: Job;
}

export function JobProgressCard({ job }: JobProgressCardProps) {
  const config = statusConfig[job.status];
  const StatusIcon = config.icon;

  return (
    <Link
      href={`/jobs/${job.id}`}
      className="flex items-center gap-3 rounded-md bg-[rgba(255,255,255,0.03)] p-3 transition-all duration-200 hover:bg-[rgba(0,212,255,0.05)]"
    >
      <StatusIcon
        className={`size-4 shrink-0 ${config.color} ${job.status === "running" ? "animate-spin" : ""}`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-[#e0e0e0]">
            Job #{job.id}
          </span>
          <Badge className={`${config.bg} ${config.color} border-none text-[10px]`}>
            {job.status}
          </Badge>
        </div>
        {(job.status === "running" || job.status === "pending") && (
          <Progress
            value={job.progress}
            className="mt-1.5 h-1 bg-[rgba(0,212,255,0.1)]"
          />
        )}
      </div>
      <span className="font-mono text-[10px] text-[#6b7280]">
        ${job.cost_total.toFixed(4)}
      </span>
    </Link>
  );
}
