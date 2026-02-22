"use client";

import { useState, useEffect } from "react";
import {
  Download,
  Package,
  FileText,
  Loader2,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { Export, Project } from "@/lib/types";

interface ExportWithProject extends Export {
  projectName?: string;
}

export default function ExportsPage() {
  const [exports, setExports] = useState<ExportWithProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [datasetCard, setDatasetCard] = useState<string | null>(null);
  const [selectedExport, setSelectedExport] = useState<number | null>(null);

  useEffect(() => {
    // Fetch all projects, then all jobs per project, then exports per job
    api
      .getProjects()
      .then(async (projects: Project[]) => {
        const allExports: ExportWithProject[] = [];
        for (const project of projects) {
          try {
            const jobs = await api.getJobs(project.id);
            for (const job of jobs) {
              if (job.status === "completed") {
                try {
                  const jobExports = await api.getExports(job.id);
                  allExports.push(
                    ...jobExports.map((e) => ({
                      ...e,
                      projectName: project.name,
                    }))
                  );
                } catch {
                  // skip
                }
              }
            }
          } catch {
            // skip
          }
        }
        setExports(
          allExports.sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          )
        );
      })
      .catch(() => {
        // API not available
      })
      .finally(() => setLoading(false));
  }, []);

  const handleViewCard = async (exportId: number) => {
    if (selectedExport === exportId) {
      setSelectedExport(null);
      setDatasetCard(null);
      return;
    }
    try {
      const card = await api.getDatasetCard(exportId);
      setDatasetCard(card);
      setSelectedExport(exportId);
    } catch {
      setDatasetCard("Failed to load dataset card.");
      setSelectedExport(exportId);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
          EXPORTS
        </h1>
        <p className="mt-1 text-sm text-[#6b7280]">
          Download center for generated datasets
        </p>
      </div>

      {/* Exports Table */}
      <GlassPanel>
        {loading ? (
          <div className="flex h-48 items-center justify-center">
            <Loader2 className="size-8 animate-spin text-[#00d4ff]" />
          </div>
        ) : exports.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Package className="mb-3 size-12 text-[#6b7280] opacity-40" />
            <p className="text-sm text-[#6b7280]">
              No exports available yet. Complete a pipeline job to generate
              datasets.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 border-b border-[rgba(0,212,255,0.1)] px-4 pb-2 font-mono text-xs font-semibold uppercase tracking-wider text-[#6b7280]">
              <div className="col-span-1">ID</div>
              <div className="col-span-2">Job</div>
              <div className="col-span-2">Project</div>
              <div className="col-span-1">Format</div>
              <div className="col-span-2">Records</div>
              <div className="col-span-2">Date</div>
              <div className="col-span-2 text-right">Actions</div>
            </div>

            {/* Table Rows */}
            {exports.map((exp) => (
              <div key={exp.id}>
                <div className="grid grid-cols-12 items-center gap-4 rounded-md bg-[rgba(255,255,255,0.03)] px-4 py-3 transition-colors hover:bg-[rgba(0,212,255,0.05)]">
                  <div className="col-span-1 font-mono text-sm text-[#e0e0e0]">
                    #{exp.id}
                  </div>
                  <div className="col-span-2 font-mono text-sm text-[#6b7280]">
                    Job #{exp.job_id}
                  </div>
                  <div className="col-span-2 truncate text-sm text-[#e0e0e0]">
                    {exp.projectName || "Unknown"}
                  </div>
                  <div className="col-span-1">
                    <Badge className="bg-[#00d4ff]/20 text-[#00d4ff] border-none text-xs">
                      {exp.format.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="col-span-2 font-mono text-sm text-[#e0e0e0]">
                    {exp.record_count.toLocaleString()}
                  </div>
                  <div className="col-span-2 text-xs text-[#6b7280]">
                    {new Date(exp.created_at).toLocaleDateString()}
                  </div>
                  <div className="col-span-2 flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleViewCard(exp.id)}
                      className="text-[#6b7280] hover:text-[#00d4ff]"
                    >
                      <FileText className="size-3.5" />
                    </Button>
                    <a
                      href={api.getDownloadUrl(exp.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Button
                        size="xs"
                        className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80"
                      >
                        <Download className="size-3.5" />
                      </Button>
                    </a>
                  </div>
                </div>

                {/* Dataset Card */}
                {selectedExport === exp.id && datasetCard && (
                  <div className="mt-2 rounded-md border border-[rgba(0,212,255,0.1)] bg-[rgba(255,255,255,0.02)] p-4 animate-fade-in">
                    <h3 className="mb-2 font-mono text-xs font-semibold uppercase tracking-wider text-[#6b7280]">
                      Dataset Card
                    </h3>
                    <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs text-[#e0e0e0]/80">
                      {datasetCard}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </GlassPanel>
    </div>
  );
}
