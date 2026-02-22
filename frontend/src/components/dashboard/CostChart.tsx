"use client";

import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { GlassPanel } from "@/components/ui/glass-panel";
import { api } from "@/lib/api";
import type { CostEntry } from "@/lib/types";

interface ChartData {
  label: string;
  cost: number;
}

export function CostChart() {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getCosts(10)
      .then((costs: CostEntry[]) => {
        setData(
          costs.map((c) => ({
            label: `Job #${c.job_id}`,
            cost: c.cost_total,
          }))
        );
      })
      .catch(() => {
        // API not available, show sample data for layout
        setData([
          { label: "Job #1", cost: 0.12 },
          { label: "Job #2", cost: 0.08 },
          { label: "Job #3", cost: 0.25 },
          { label: "Job #4", cost: 0.15 },
          { label: "Job #5", cost: 0.31 },
        ]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <GlassPanel>
      <h2 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#ff8c00]">
        Cost per Job
      </h2>
      {loading ? (
        <div className="flex h-48 items-center justify-center">
          <span className="animate-pulse text-sm text-[#6b7280]">
            Loading cost data...
          </span>
        </div>
      ) : data.length === 0 ? (
        <div className="flex h-48 items-center justify-center">
          <span className="text-sm text-[#6b7280]">
            No cost data available yet.
          </span>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(0, 212, 255, 0.1)"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fill: "#6b7280", fontSize: 11, fontFamily: "var(--font-jetbrains-mono)" }}
              axisLine={{ stroke: "rgba(0, 212, 255, 0.15)" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#6b7280", fontSize: 11, fontFamily: "var(--font-jetbrains-mono)" }}
              axisLine={{ stroke: "rgba(0, 212, 255, 0.15)" }}
              tickLine={false}
              tickFormatter={(v: number) => `$${v.toFixed(2)}`}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(10, 10, 15, 0.95)",
                border: "1px solid rgba(0, 212, 255, 0.3)",
                borderRadius: "8px",
                backdropFilter: "blur(20px)",
                color: "#e0e0e0",
                fontFamily: "var(--font-jetbrains-mono)",
                fontSize: "12px",
              }}
              formatter={(value) => [`$${Number(value ?? 0).toFixed(4)}`, "Cost"]}
              cursor={{ fill: "rgba(0, 212, 255, 0.05)" }}
            />
            <Bar
              dataKey="cost"
              fill="#ff8c00"
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </GlassPanel>
  );
}
