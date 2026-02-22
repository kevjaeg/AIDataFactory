"use client";

import { useState } from "react";
import {
  Key,
  Save,
  Globe,
  FileText,
  Sparkles,
  Shield,
  Package,
  Server,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("");
  const [apiUrl, setApiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  );
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // In a real app, this would persist settings
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
          SETTINGS
        </h1>
        <p className="mt-1 text-sm text-[#6b7280]">
          Configure your AI Data Factory instance
        </p>
      </div>

      {/* API Configuration */}
      <GlassPanel>
        <div className="flex items-center gap-2 mb-4">
          <Server className="size-4 text-[#00d4ff]" />
          <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
            API Configuration
          </h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[#6b7280]">
              Backend API URL
            </label>
            <Input
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="border-[rgba(0,212,255,0.2)] bg-[rgba(255,255,255,0.05)] font-mono text-sm text-[#e0e0e0] placeholder:text-[#6b7280] focus:border-[#00d4ff]"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[#6b7280]">
              OpenAI API Key
            </label>
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="border-[rgba(0,212,255,0.2)] bg-[rgba(255,255,255,0.05)] font-mono text-sm text-[#e0e0e0] placeholder:text-[#6b7280] focus:border-[#00d4ff]"
            />
            <p className="mt-1 text-xs text-[#6b7280]">
              Your API key is stored locally and used for LLM generation stages.
            </p>
          </div>
        </div>
      </GlassPanel>

      {/* Default Pipeline Configuration */}
      <GlassPanel>
        <div className="flex items-center gap-2 mb-4">
          <Key className="size-4 text-[#ff8c00]" />
          <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#ff8c00]">
            Default Pipeline Configuration
          </h2>
        </div>
        <div className="space-y-4">
          {[
            {
              icon: Globe,
              label: "Spider (Scraping)",
              fields: [
                { key: "max_depth", label: "Max Depth", default: "2" },
                { key: "timeout", label: "Timeout (s)", default: "30" },
              ],
            },
            {
              icon: FileText,
              label: "Refiner (Processing)",
              fields: [
                { key: "chunk_size", label: "Chunk Size (tokens)", default: "512" },
                { key: "overlap", label: "Overlap (tokens)", default: "50" },
              ],
            },
            {
              icon: Sparkles,
              label: "Factory (Generation)",
              fields: [
                { key: "model", label: "Model", default: "gpt-4o-mini" },
                { key: "batch_size", label: "Batch Size", default: "5" },
              ],
            },
            {
              icon: Shield,
              label: "Inspector (Quality)",
              fields: [
                { key: "min_score", label: "Min Quality Score", default: "0.7" },
                { key: "checks", label: "Check Types", default: "all" },
              ],
            },
            {
              icon: Package,
              label: "Shipper (Export)",
              fields: [
                { key: "format", label: "Default Format", default: "jsonl" },
                { key: "version", label: "Version Prefix", default: "v1" },
              ],
            },
          ].map((stage) => (
            <div
              key={stage.label}
              className="rounded-md border border-[rgba(0,212,255,0.1)] p-4"
            >
              <div className="mb-3 flex items-center gap-2">
                <stage.icon className="size-4 text-[#00d4ff] opacity-60" />
                <span className="font-mono text-xs font-medium text-[#e0e0e0]">
                  {stage.label}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {stage.fields.map((field) => (
                  <div key={field.key}>
                    <label className="mb-1 block text-xs text-[#6b7280]">
                      {field.label}
                    </label>
                    <Input
                      defaultValue={field.default}
                      className="h-8 border-[rgba(0,212,255,0.15)] bg-[rgba(255,255,255,0.03)] font-mono text-xs text-[#e0e0e0] focus:border-[#00d4ff]"
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </GlassPanel>

      {/* Save */}
      <div className="flex items-center gap-3">
        <Button
          onClick={handleSave}
          className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs uppercase tracking-wider"
        >
          <Save className="size-4" />
          Save Settings
        </Button>
        {saved && (
          <span className="animate-fade-in font-mono text-xs text-[#00ff88]">
            Settings saved successfully.
          </span>
        )}
      </div>
    </div>
  );
}
