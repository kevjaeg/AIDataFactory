"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FolderKanban,
  Plus,
  Calendar,
  Briefcase,
  ArrowRight,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useProjects } from "@/hooks/useProjects";
import { api } from "@/lib/api";

export default function ProjectsPage() {
  const { projects, loading, refetch } = useProjects();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await api.createProject({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setName("");
      setDescription("");
      setShowForm(false);
      refetch();
    } catch {
      // handle error
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
            PROJECTS
          </h1>
          <p className="mt-1 text-sm text-[#6b7280]">
            Manage your data pipeline projects
          </p>
        </div>
        <Button
          onClick={() => setShowForm(!showForm)}
          className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs uppercase tracking-wider"
        >
          <Plus className="size-4" />
          New Project
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <GlassPanel glow="cyan" className="animate-fade-in">
          <h3 className="mb-4 font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
            Create New Project
          </h3>
          <div className="space-y-3">
            <Input
              placeholder="Project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border-[rgba(0,212,255,0.2)] bg-[rgba(255,255,255,0.05)] text-[#e0e0e0] placeholder:text-[#6b7280] focus:border-[#00d4ff]"
            />
            <Textarea
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="border-[rgba(0,212,255,0.2)] bg-[rgba(255,255,255,0.05)] text-[#e0e0e0] placeholder:text-[#6b7280] focus:border-[#00d4ff]"
            />
            <div className="flex gap-2">
              <Button
                onClick={handleCreate}
                disabled={!name.trim() || creating}
                className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs"
              >
                {creating ? "Creating..." : "Create Project"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => setShowForm(false)}
                className="text-[#6b7280] hover:text-[#e0e0e0] font-mono text-xs"
              >
                Cancel
              </Button>
            </div>
          </div>
        </GlassPanel>
      )}

      {/* Project List */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <GlassPanel key={i} className="animate-pulse">
              <div className="h-24 rounded bg-[rgba(255,255,255,0.03)]" />
            </GlassPanel>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <GlassPanel className="py-12 text-center">
          <FolderKanban className="mx-auto mb-3 size-12 text-[#6b7280] opacity-40" />
          <p className="text-sm text-[#6b7280]">
            No projects yet. Create your first project to get started.
          </p>
        </GlassPanel>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <GlassPanel className="group h-full cursor-pointer transition-all duration-300 hover:glow-cyan">
                <div className="flex items-start justify-between">
                  <FolderKanban className="size-5 text-[#00d4ff] opacity-60" />
                  <ArrowRight className="size-4 text-[#6b7280] opacity-0 transition-all group-hover:translate-x-1 group-hover:opacity-100" />
                </div>
                <h3 className="mt-3 font-mono text-base font-semibold text-[#e0e0e0] group-hover:text-[#00d4ff]">
                  {project.name}
                </h3>
                {project.description && (
                  <p className="mt-1 text-sm text-[#6b7280] line-clamp-2">
                    {project.description}
                  </p>
                )}
                <div className="mt-4 flex items-center gap-4 text-xs text-[#6b7280]">
                  <span className="flex items-center gap-1">
                    <Calendar className="size-3" />
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <Briefcase className="size-3" />
                    ID: {project.id}
                  </span>
                </div>
              </GlassPanel>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
