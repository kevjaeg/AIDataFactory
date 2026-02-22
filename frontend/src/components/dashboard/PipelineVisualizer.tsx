"use client";

import {
  Globe,
  FileText,
  Sparkles,
  Shield,
  Package,
  Check,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PipelineStage {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const stages: PipelineStage[] = [
  { key: "spider", label: "Spider", icon: Globe },
  { key: "refiner", label: "Refiner", icon: FileText },
  { key: "factory", label: "Factory", icon: Sparkles },
  { key: "inspector", label: "Inspector", icon: Shield },
  { key: "shipper", label: "Shipper", icon: Package },
];

type StageStatus = "pending" | "active" | "completed" | "failed";

interface PipelineVisualizerProps {
  currentStage: string | null;
  jobStatus: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
}

function getStageStatus(
  stageIndex: number,
  currentStage: string | null,
  jobStatus: string
): StageStatus {
  if (jobStatus === "completed") return "completed";
  if (jobStatus === "cancelled") return "pending";

  if (!currentStage) {
    if (jobStatus === "pending") return "pending";
    return "pending";
  }

  const currentIndex = stages.findIndex((s) => s.key === currentStage);

  if (jobStatus === "failed") {
    if (stageIndex < currentIndex) return "completed";
    if (stageIndex === currentIndex) return "failed";
    return "pending";
  }

  if (stageIndex < currentIndex) return "completed";
  if (stageIndex === currentIndex) return "active";
  return "pending";
}

function StageNode({
  stage,
  status,
  progress,
  isActive,
}: {
  stage: PipelineStage;
  status: StageStatus;
  progress: number;
  isActive: boolean;
}) {
  const Icon = stage.icon;

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Hexagonal Stage Node */}
      <div
        className={cn(
          "relative flex size-16 items-center justify-center rounded-lg transition-all duration-500",
          status === "pending" &&
            "border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.03)]",
          status === "active" &&
            "border border-[#00d4ff] bg-[rgba(0,212,255,0.1)] glow-cyan animate-pulse-glow",
          status === "completed" &&
            "border border-[#00ff88] bg-[rgba(0,255,136,0.1)] glow-green",
          status === "failed" &&
            "border border-[#ff3366] bg-[rgba(255,51,102,0.1)] glow-red"
        )}
      >
        <Icon
          className={cn(
            "size-7 transition-colors duration-500",
            status === "pending" && "text-[#6b7280]/40",
            status === "active" && "text-[#00d4ff]",
            status === "completed" && "text-[#00ff88]",
            status === "failed" && "text-[#ff3366]"
          )}
        />

        {/* Completed overlay */}
        {status === "completed" && (
          <div className="absolute -right-1 -top-1 flex size-5 items-center justify-center rounded-full bg-[#00ff88]">
            <Check className="size-3 text-[#0a0a0f]" />
          </div>
        )}

        {/* Failed overlay */}
        {status === "failed" && (
          <div className="absolute -right-1 -top-1 flex size-5 items-center justify-center rounded-full bg-[#ff3366]">
            <X className="size-3 text-white" />
          </div>
        )}
      </div>

      {/* Label */}
      <span
        className={cn(
          "font-mono text-xs font-medium tracking-wider transition-colors duration-500",
          status === "pending" && "text-[#6b7280]/50",
          status === "active" && "text-[#00d4ff] text-glow-cyan",
          status === "completed" && "text-[#00ff88]",
          status === "failed" && "text-[#ff3366]"
        )}
      >
        {stage.label}
      </span>

      {/* Progress below active stage */}
      {isActive && status === "active" && (
        <span className="font-mono text-xs text-[#00d4ff]">{progress}%</span>
      )}
    </div>
  );
}

function ConnectionLine({ status }: { status: "pending" | "active" | "completed" }) {
  return (
    <div className="flex flex-1 items-center px-1 pt-0 -mt-6">
      <svg className="h-2 w-full" viewBox="0 0 100 8" preserveAspectRatio="none">
        {/* Background line */}
        <line
          x1="0"
          y1="4"
          x2="100"
          y2="4"
          stroke={
            status === "completed"
              ? "#00ff88"
              : status === "active"
                ? "#00d4ff"
                : "rgba(255,255,255,0.1)"
          }
          strokeWidth="2"
          strokeDasharray={status === "active" ? "4 4" : "none"}
          strokeOpacity={status === "pending" ? 0.3 : 0.6}
        />
        {/* Animated flowing dots for active connection */}
        {status === "active" && (
          <line
            x1="0"
            y1="4"
            x2="100"
            y2="4"
            stroke="#00d4ff"
            strokeWidth="2"
            strokeDasharray="4 4"
            style={{
              animation: "flow-dots 1s linear infinite",
            }}
          />
        )}
      </svg>
    </div>
  );
}

function getConnectionStatus(
  stageIndex: number,
  currentStage: string | null,
  jobStatus: string
): "pending" | "active" | "completed" {
  if (jobStatus === "completed") return "completed";

  const currentIndex = stages.findIndex((s) => s.key === currentStage);

  if (stageIndex < currentIndex) return "completed";
  if (stageIndex === currentIndex) return "active";
  return "pending";
}

export function PipelineVisualizer({
  currentStage,
  jobStatus,
  progress,
}: PipelineVisualizerProps) {
  return (
    <div className="flex items-start justify-between gap-0">
      {stages.map((stage, index) => {
        const status = getStageStatus(index, currentStage, jobStatus);
        const isActive = stage.key === currentStage && jobStatus === "running";

        return (
          <div key={stage.key} className="flex flex-1 items-start">
            <div className="flex flex-1 flex-col items-center">
              <StageNode
                stage={stage}
                status={status}
                progress={progress}
                isActive={isActive}
              />
            </div>
            {index < stages.length - 1 && (
              <ConnectionLine
                status={getConnectionStatus(index, currentStage, jobStatus)}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
