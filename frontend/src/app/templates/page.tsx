"use client";

import { useEffect, useState, useCallback } from "react";
import {
  FileCode2,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Lock,
  Save,
  X,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/glass-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { TemplateInfo, CustomTemplate, CustomTemplateCreate } from "@/lib/types";

interface FormState {
  name: string;
  template_type: string;
  system_prompt: string;
  user_prompt_template: string;
  output_schema: string;
}

const emptyForm: FormState = {
  name: "",
  template_type: "",
  system_prompt: "",
  user_prompt_template: "",
  output_schema: "",
};

export default function TemplatesPage() {
  const [builtInTemplates, setBuiltInTemplates] = useState<TemplateInfo[]>([]);
  const [customTemplates, setCustomTemplates] = useState<CustomTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Delete confirmation
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [builtIn, custom] = await Promise.all([
        api.getTemplates(),
        api.getCustomTemplates(),
      ]);
      setBuiltInTemplates(builtIn);
      setCustomTemplates(custom);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const openCreateForm = () => {
    setEditingId(null);
    setForm(emptyForm);
    setFormError(null);
    setShowForm(true);
  };

  const openEditForm = (template: CustomTemplate) => {
    setEditingId(template.id);
    setForm({
      name: template.name,
      template_type: template.template_type,
      system_prompt: template.system_prompt,
      user_prompt_template: template.user_prompt_template,
      output_schema: template.output_schema
        ? JSON.stringify(template.output_schema, null, 2)
        : "",
    });
    setFormError(null);
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm);
    setFormError(null);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.template_type.trim()) {
      setFormError("Name and template type are required.");
      return;
    }
    if (!form.system_prompt.trim()) {
      setFormError("System prompt is required.");
      return;
    }
    if (!form.user_prompt_template.trim()) {
      setFormError("User prompt template is required.");
      return;
    }

    let parsedSchema: Record<string, unknown> | null = null;
    if (form.output_schema.trim()) {
      try {
        parsedSchema = JSON.parse(form.output_schema.trim());
      } catch {
        setFormError("Output schema must be valid JSON.");
        return;
      }
    }

    const data: CustomTemplateCreate = {
      name: form.name.trim(),
      template_type: form.template_type.trim(),
      system_prompt: form.system_prompt,
      user_prompt_template: form.user_prompt_template,
      output_schema: parsedSchema,
    };

    setSaving(true);
    setFormError(null);
    try {
      if (editingId !== null) {
        await api.updateCustomTemplate(editingId, data);
      } else {
        await api.createCustomTemplate(data);
      }
      closeForm();
      await fetchTemplates();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save template");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeleting(true);
    try {
      await api.deleteCustomTemplate(id);
      setDeletingId(null);
      await fetchTemplates();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete template");
    } finally {
      setDeleting(false);
    }
  };

  const updateField = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const inputClasses =
    "border-[rgba(0,212,255,0.2)] bg-[rgba(255,255,255,0.05)] font-mono text-sm text-[#e0e0e0] placeholder:text-[#6b7280] focus:border-[#00d4ff]";
  const labelClasses = "mb-1.5 block text-xs font-medium text-[#6b7280]";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold tracking-wide text-[#00d4ff] text-glow-cyan">
            TEMPLATES
          </h1>
          <p className="mt-1 text-sm text-[#6b7280]">
            Manage built-in and custom LLM prompt templates
          </p>
        </div>
        <Button
          onClick={openCreateForm}
          className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs uppercase tracking-wider"
        >
          <Plus className="size-4" />
          New Template
        </Button>
      </div>

      {/* Global Error */}
      {error && (
        <GlassPanel glow="red" className="animate-fade-in">
          <div className="flex items-center justify-between">
            <p className="font-mono text-sm text-red-400">{error}</p>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => setError(null)}
              className="text-[#6b7280] hover:text-[#e0e0e0]"
            >
              <X className="size-3" />
            </Button>
          </div>
        </GlassPanel>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="size-8 animate-spin text-[#00d4ff]" />
          <span className="ml-3 font-mono text-sm text-[#6b7280]">
            Loading templates...
          </span>
        </div>
      ) : (
        <>
          {/* Built-in Templates */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <Lock className="size-4 text-[#00d4ff] opacity-60" />
              <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
                Built-in Templates
              </h2>
              <span className="font-mono text-xs text-[#6b7280]">
                (read-only)
              </span>
            </div>
            {builtInTemplates.length === 0 ? (
              <GlassPanel className="py-8 text-center">
                <p className="text-sm text-[#6b7280]">
                  No built-in templates found.
                </p>
              </GlassPanel>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {builtInTemplates.map((t) => (
                  <GlassPanel
                    key={t.name}
                    className="border border-[rgba(0,212,255,0.15)]"
                  >
                    <div className="flex items-start justify-between">
                      <FileCode2 className="size-5 text-[#00d4ff] opacity-60" />
                      <Badge
                        variant="outline"
                        className="border-[rgba(0,212,255,0.3)] text-[#00d4ff] font-mono text-[10px]"
                      >
                        Built-in
                      </Badge>
                    </div>
                    <h3 className="mt-3 font-mono text-base font-semibold text-[#e0e0e0]">
                      {t.name}
                    </h3>
                    <div className="mt-2 flex items-center gap-2 text-xs text-[#6b7280]">
                      <span>Type: {t.template_type}</span>
                      {t.has_system_prompt && (
                        <Badge
                          variant="secondary"
                          className="bg-[rgba(0,212,255,0.1)] text-[#00d4ff] text-[10px]"
                        >
                          system prompt
                        </Badge>
                      )}
                    </div>
                  </GlassPanel>
                ))}
              </div>
            )}
          </div>

          {/* Custom Templates */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <FileCode2 className="size-4 text-[#ff8c00] opacity-60" />
              <h2 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#ff8c00]">
                Custom Templates
              </h2>
            </div>
            {customTemplates.length === 0 ? (
              <GlassPanel className="py-8 text-center">
                <FileCode2 className="mx-auto mb-3 size-12 text-[#6b7280] opacity-40" />
                <p className="text-sm text-[#6b7280]">
                  No custom templates yet. Create one to get started.
                </p>
              </GlassPanel>
            ) : (
              <div className="space-y-3">
                {customTemplates.map((t) => (
                  <GlassPanel
                    key={t.id}
                    className="border border-[rgba(255,140,0,0.15)]"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileCode2 className="size-5 text-[#ff8c00] opacity-60" />
                        <div>
                          <h3 className="font-mono text-base font-semibold text-[#e0e0e0]">
                            {t.name}
                          </h3>
                          <div className="mt-1 flex items-center gap-3 text-xs text-[#6b7280]">
                            <span>Type: {t.template_type}</span>
                            <span>
                              Created:{" "}
                              {new Date(t.created_at).toLocaleDateString()}
                            </span>
                            {t.output_schema && (
                              <Badge
                                variant="secondary"
                                className="bg-[rgba(255,140,0,0.1)] text-[#ff8c00] text-[10px]"
                              >
                                schema
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {deletingId === t.id ? (
                          <div className="flex items-center gap-2 animate-fade-in">
                            <span className="font-mono text-xs text-red-400">
                              Delete?
                            </span>
                            <Button
                              size="xs"
                              onClick={() => handleDelete(t.id)}
                              disabled={deleting}
                              className="bg-red-600 text-white hover:bg-red-500 font-mono text-xs"
                            >
                              {deleting ? (
                                <Loader2 className="size-3 animate-spin" />
                              ) : (
                                "Yes"
                              )}
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => setDeletingId(null)}
                              className="text-[#6b7280] hover:text-[#e0e0e0] font-mono text-xs"
                            >
                              No
                            </Button>
                          </div>
                        ) : (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => openEditForm(t)}
                              className="text-[#00d4ff] hover:text-[#00d4ff] hover:bg-[rgba(0,212,255,0.1)] font-mono text-xs"
                            >
                              <Pencil className="size-3" />
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setDeletingId(t.id)}
                              className="text-red-400 hover:text-red-300 hover:bg-[rgba(255,0,0,0.1)] font-mono text-xs"
                            >
                              <Trash2 className="size-3" />
                              Delete
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </GlassPanel>
                ))}
              </div>
            )}
          </div>

          {/* Create / Edit Form */}
          {showForm && (
            <GlassPanel glow="cyan" className="animate-fade-in">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-mono text-sm font-semibold uppercase tracking-wider text-[#00d4ff]">
                  {editingId !== null ? "Edit Template" : "Create New Template"}
                </h3>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  onClick={closeForm}
                  className="text-[#6b7280] hover:text-[#e0e0e0]"
                >
                  <X className="size-4" />
                </Button>
              </div>

              {formError && (
                <div className="mb-4 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2">
                  <p className="font-mono text-xs text-red-400">{formError}</p>
                </div>
              )}

              <div className="space-y-4">
                {/* Name and Type row */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelClasses}>Name</label>
                    <Input
                      placeholder="my-custom-template"
                      value={form.name}
                      onChange={(e) => updateField("name", e.target.value)}
                      className={inputClasses}
                    />
                  </div>
                  <div>
                    <label className={labelClasses}>Template Type</label>
                    <Input
                      placeholder="qa, summarization, classification..."
                      value={form.template_type}
                      onChange={(e) =>
                        updateField("template_type", e.target.value)
                      }
                      className={inputClasses}
                    />
                  </div>
                </div>

                {/* System Prompt */}
                <div>
                  <label className={labelClasses}>System Prompt</label>
                  <Textarea
                    placeholder="You are a helpful assistant that..."
                    value={form.system_prompt}
                    onChange={(e) =>
                      updateField("system_prompt", e.target.value)
                    }
                    rows={4}
                    className={inputClasses}
                  />
                </div>

                {/* User Prompt Template */}
                <div>
                  <label className={labelClasses}>
                    User Prompt Template (Jinja2)
                  </label>
                  <Textarea
                    placeholder="Given the following text:\n{{ text }}\n\nGenerate..."
                    value={form.user_prompt_template}
                    onChange={(e) =>
                      updateField("user_prompt_template", e.target.value)
                    }
                    rows={6}
                    className={inputClasses}
                  />
                </div>

                {/* Output Schema */}
                <div>
                  <label className={labelClasses}>
                    Output Schema (JSON, optional)
                  </label>
                  <Textarea
                    placeholder='{"type": "object", "properties": {...}}'
                    value={form.output_schema}
                    onChange={(e) =>
                      updateField("output_schema", e.target.value)
                    }
                    rows={4}
                    className={inputClasses}
                  />
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-2 pt-2">
                  <Button
                    variant="ghost"
                    onClick={closeForm}
                    className="text-[#6b7280] hover:text-[#e0e0e0] font-mono text-xs"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-[#00d4ff] text-[#0a0a0f] hover:bg-[#00d4ff]/80 font-mono text-xs uppercase tracking-wider"
                  >
                    {saving ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Save className="size-4" />
                    )}
                    {saving
                      ? "Saving..."
                      : editingId !== null
                        ? "Update Template"
                        : "Save Template"}
                  </Button>
                </div>
              </div>
            </GlassPanel>
          )}
        </>
      )}
    </div>
  );
}
