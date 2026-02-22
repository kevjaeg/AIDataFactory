"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Rocket,
  Zap,
  ChevronDown,
  ChevronRight,
  Globe,
  FileText,
  Sparkles,
  Shield,
  Package,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

const stageConfigs = [
  {
    key: "scraping",
    label: "Spider (Scraping)",
    icon: Globe,
    description: "Configure web scraping parameters",
  },
  {
    key: "processing",
    label: "Refiner (Processing)",
    icon: FileText,
    description: "Content extraction and chunking settings",
  },
  {
    key: "generation",
    label: "Factory (Generation)",
    icon: Sparkles,
    description: "LLM generation configuration",
  },
  {
    key: "quality",
    label: "Inspector (Quality)",
    icon: Shield,
    description: "Quality check thresholds",
  },
  {
    key: "export",
    label: "Shipper (Export)",
    icon: Package,
    description: "Export format and options",
  },
];

export default function NewJobPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const projectId = parseInt(id, 10);
  const router = useRouter();
  const [urls, setUrls] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set());

  const toggleStage = (key: string) => {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleSubmit = async (quickStart = false) => {
    const urlList = urls
      .split("\n")
      .map((u) => u.trim())
      .filter((u) => u.length > 0);

    if (urlList.length === 0) {
      setError("Please enter at least one URL.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const job = await api.createJob(projectId, {
        urls: urlList,
        config: quickStart ? {} : undefined,
      });
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create job"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Back + Header */}
      <div>
        <Link
          href={`/projects/${projectId}`}
          className="mb-4 inline-flex items-center gap-1 text-sm text-[#6b7280] transition-colors hover:text-[#00d4ff]"
        >
          <ArrowLeft className="size-4" />
          Back to Project
        </Link>
        <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
          NEW PIPELINE JOB
        </h1>
        <p className="mt-1 text-sm text-[#6b7280]">
          Configure and launch a new data pipeline run
        </p>
      </div>

      {/* URL Input */}
      <GlassPanel glow="cyan">
        <h2 className="mb-3 font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
          Target URLs
        </h2>
        <Textarea
          placeholder={"https://example.com/page1\nhttps://example.com/page2\nhttps://example.com/page3"}
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          rows={6}
          className="border-[rgba(0,212,255,0.2)] bg-[rgba(255,255,255,0.05)] font-mono text-sm text-[#e0e0e0] placeholder:text-[#6b7280]/60 focus:border-[#00d4ff]"
        />
        <p className="mt-2 text-xs text-[#6b7280]">
          Enter one URL per line. These will be scraped and processed through
          the pipeline.
        </p>
      </GlassPanel>

      {/* Stage Configs (Accordion) */}
      <GlassPanel>
        <h2 className="mb-3 font-mono text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
          Stage Configuration (Optional)
        </h2>
        <div className="space-y-2">
          {stageConfigs.map((stage) => (
            <div
              key={stage.key}
              className="overflow-hidden rounded-md border border-[rgba(0,212,255,0.1)]"
            >
              <button
                onClick={() => toggleStage(stage.key)}
                className="flex w-full items-center gap-3 bg-[rgba(255,255,255,0.03)] px-4 py-3 text-left transition-colors hover:bg-[rgba(0,212,255,0.05)]"
              >
                <stage.icon className="size-4 text-[#00d4ff] opacity-60" />
                <span className="flex-1 font-mono text-sm text-[#e0e0e0]">
                  {stage.label}
                </span>
                {expandedStages.has(stage.key) ? (
                  <ChevronDown className="size-4 text-[#6b7280]" />
                ) : (
                  <ChevronRight className="size-4 text-[#6b7280]" />
                )}
              </button>
              {expandedStages.has(stage.key) && (
                <div className="border-t border-[rgba(0,212,255,0.1)] bg-[rgba(255,255,255,0.02)] px-4 py-3">
                  <p className="text-xs text-[#6b7280]">
                    {stage.description}. Default configuration will be used.
                    Advanced configuration coming soon.
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </GlassPanel>

      {/* Error */}
      {error && (
        <GlassPanel glow="red" className="animate-fade-in">
          <p className="text-sm text-[#ff3366]">{error}</p>
        </GlassPanel>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          onClick={() => handleSubmit(true)}
          disabled={submitting}
          className="bg-[#00ff88] text-[#0a0a0f] hover:bg-[#00ff88]/80 font-mono text-xs uppercase tracking-wider"
        >
          <Zap className="size-4" />
          {submitting ? "Launching..." : "Quick Start"}
        </Button>
        <Button
          onClick={() => handleSubmit(false)}
          disabled={submitting}
          variant="outline"
          className="border-[rgba(0,212,255,0.3)] text-[#00d4ff] hover:bg-[rgba(0,212,255,0.1)] font-mono text-xs uppercase tracking-wider"
        >
          <Rocket className="size-4" />
          Launch with Config
        </Button>
      </div>
    </div>
  );
}
