"use client";

import { useState, useEffect } from "react";
import {
  FolderKanban,
  Activity,
  Database,
  DollarSign,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { api } from "@/lib/api";
import type { StatsOverview as StatsOverviewType } from "@/lib/types";

const defaultStats: StatsOverviewType = {
  total_projects: 0,
  total_jobs: 0,
  active_jobs: 0,
  total_examples: 0,
  total_cost: 0,
};

export function StatsOverview() {
  const [stats, setStats] = useState<StatsOverviewType>(defaultStats);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getOverview()
      .then(setStats)
      .catch(() => {
        // API not available yet, use defaults
      })
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    {
      label: "Total Projects",
      value: stats.total_projects,
      icon: FolderKanban,
      color: "text-[#e0e0e0]",
      glow: "none" as const,
    },
    {
      label: "Active Jobs",
      value: stats.active_jobs,
      icon: Activity,
      color: "text-[#00d4ff]",
      glow: "cyan" as const,
    },
    {
      label: "Total Examples",
      value: stats.total_examples.toLocaleString(),
      icon: Database,
      color: "text-[#00ff88]",
      glow: "none" as const,
    },
    {
      label: "Total Cost",
      value: `$${stats.total_cost.toFixed(2)}`,
      icon: DollarSign,
      color: "text-[#ff8c00]",
      glow: "none" as const,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <GlassPanel
          key={card.label}
          glow={card.glow}
          className="animate-fade-in transition-all duration-300 hover:glow-cyan"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
                {card.label}
              </p>
              <p
                className={`mt-2 font-mono text-2xl font-bold ${card.color} ${loading ? "animate-pulse" : ""}`}
              >
                {loading ? "---" : card.value}
              </p>
            </div>
            <card.icon className={`size-8 ${card.color} opacity-40`} />
          </div>
        </GlassPanel>
      ))}
    </div>
  );
}
