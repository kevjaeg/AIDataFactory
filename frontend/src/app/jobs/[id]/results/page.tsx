"use client";

import { use, useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  FileText,
  CheckCircle2,
  Loader2,
  Package,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useJob } from "@/hooks/useJobs";
import { api } from "@/lib/api";
import type { Export } from "@/lib/types";

export default function JobResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const jobId = parseInt(id, 10);
  const { job, loading: jobLoading } = useJob(jobId);
  const [exports, setExports] = useState<Export[]>([]);
  const [loading, setLoading] = useState(true);
  const [datasetCard, setDatasetCard] = useState<string | null>(null);
  const [selectedExport, setSelectedExport] = useState<number | null>(null);

  useEffect(() => {
    api
      .getExports(jobId)
      .then(setExports)
      .catch(() => {
        // API not available
      })
      .finally(() => setLoading(false));
  }, [jobId]);

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

  if (jobLoading || loading) {
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
          href={`/jobs/${jobId}`}
          className="mb-4 inline-flex items-center gap-1 text-sm text-[#6b7280] transition-colors hover:text-[#00d4ff]"
        >
          <ArrowLeft className="size-4" />
          Back to Job
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
            RESULTS — JOB #{jobId}
          </h1>
          {job?.status === "completed" && (
            <Badge className="bg-[#00ff88]/20 text-[#00ff88] border-none text-xs">
              <CheckCircle2 className="size-3" />
              Completed
            </Badge>
          )}
        </div>
      </div>

      {/* Quality Overview */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <GlassPanel glow="green">
          <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
            Pipeline Status
          </p>
          <p className="mt-2 font-mono text-xl font-bold text-[#00ff88]">
            {job?.status === "completed" ? "SUCCESS" : job?.status?.toUpperCase() || "UNKNOWN"}
          </p>
        </GlassPanel>
        <GlassPanel>
          <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
            Exports Generated
          </p>
          <p className="mt-2 font-mono text-xl font-bold text-[#00d4ff]">
            {exports.length}
          </p>
        </GlassPanel>
        <GlassPanel>
          <p className="text-xs font-medium uppercase tracking-wider text-[#6b7280]">
            Total Records
          </p>
          <p className="mt-2 font-mono text-xl font-bold text-[#e0e0e0]">
            {exports.reduce((sum, e) => sum + e.record_count, 0).toLocaleString()}
          </p>
        </GlassPanel>
      </div>

      {/* Exports List */}
      <GlassPanel>
        <h2 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
          Export Files
        </h2>
        {exports.length === 0 ? (
          <p className="py-8 text-center text-sm text-[#6b7280]">
            No exports available for this job.
          </p>
        ) : (
          <div className="space-y-3">
            {exports.map((exp) => (
              <div key={exp.id}>
                <div className="flex items-center gap-4 rounded-md bg-[rgba(255,255,255,0.03)] p-4">
                  <Package className="size-5 shrink-0 text-[#00d4ff] opacity-60" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium text-[#e0e0e0]">
                        Export #{exp.id}
                      </span>
                      <Badge className="bg-[#00d4ff]/20 text-[#00d4ff] border-none text-xs">
                        {exp.format.toUpperCase()}
                      </Badge>
                      <span className="font-mono text-xs text-[#6b7280]">
                        v{exp.version}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-[#6b7280]">
                      {exp.record_count.toLocaleString()} records |{" "}
                      {new Date(exp.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleViewCard(exp.id)}
                      className="text-[#6b7280] hover:text-[#00d4ff] font-mono text-xs"
                    >
                      <FileText className="size-4" />
                      Card
                    </Button>
                    <a
                      href={api.getDownloadUrl(exp.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Button
                        size="sm"
                        className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs"
                      >
                        <Download className="size-4" />
                        Download
                      </Button>
                    </a>
                  </div>
                </div>

                {/* Dataset Card Viewer */}
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
