"use client";

import { StatsOverview } from "@/components/dashboard/StatsOverview";
import { ActiveJobs } from "@/components/dashboard/ActiveJobs";
import { CostChart } from "@/components/dashboard/CostChart";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
            DASHBOARD
          </h1>
          <p className="mt-1 text-sm text-[#6b7280]">
            System overview and pipeline monitoring
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block size-2 animate-pulse-glow rounded-full bg-[#00ff88]" />
          <span className="font-mono text-xs text-[#6b7280]">SYSTEM ONLINE</span>
        </div>
      </div>

      {/* Stat Cards */}
      <StatsOverview />

      {/* Active Jobs + Cost Chart */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ActiveJobs />
        <CostChart />
      </div>
    </div>
  );
}
