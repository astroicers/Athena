// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/atoms/Button";
import type { ToolRegistryCreate } from "@/types/tool";

interface AddToolModalProps {
  isOpen: boolean;
  onSubmit: (data: ToolRegistryCreate) => Promise<void>;
  onCancel: () => void;
}

const CATEGORY_OPTIONS = [
  "reconnaissance",
  "enumeration",
  "vulnerability_scanning",
  "credential_access",
  "exploitation",
  "execution",
];

const RISK_OPTIONS = ["low", "medium", "high", "critical"];

export function AddToolModal({ isOpen, onSubmit, onCancel }: AddToolModalProps) {
  const t = useTranslations("Tools");
  const tCommon = useTranslations("Common");
  const tKind = useTranslations("ToolKind");
  const tCategory = useTranslations("ToolCategory");
  const tRisk = useTranslations("Risk");
  const [toolId, setToolId] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"tool" | "engine">("tool");
  const [category, setCategory] = useState("reconnaissance");
  const [riskLevel, setRiskLevel] = useState("low");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  function resetForm() {
    setToolId("");
    setName("");
    setKind("tool");
    setCategory("reconnaissance");
    setRiskLevel("low");
    setDescription("");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!toolId.trim()) {
      setError(t("toolIdRequired"));
      return;
    }
    if (!name.trim()) {
      setError(t("nameRequired"));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        toolId: toolId.trim(),
        name: name.trim(),
        kind,
        category,
        riskLevel,
        description: description.trim() || undefined,
      });
      resetForm();
    } catch (err) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || t("failedCreate"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
      <div className="bg-[#111827] border-2 border-[#1f2937] rounded-athena-lg p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <span className="text-xs font-mono text-[#9ca3af]">
            {t("newTool")}
          </span>
          <h2 className="text-lg font-mono font-bold text-[#e5e7eb] mt-1">
            {t("registerTool")}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Tool ID */}
          <div>
            <label className="block text-sm font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
              {t("toolId")} <span className="text-[#EF4444]">*</span>
            </label>
            <input
              type="text"
              value={toolId}
              onChange={(e) => setToolId(e.target.value)}
              placeholder="my-custom-scanner"
              className="w-full bg-[#0A0E17] border border-[#1f2937] rounded-athena-sm px-3 py-2 text-sm font-mono text-[#e5e7eb] placeholder-[#6b7280] focus:outline-none focus:border-[#3b82f6]"
            />
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
              {t("name")} <span className="text-[#EF4444]">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Custom Scanner"
              className="w-full bg-[#0A0E17] border border-[#1f2937] rounded-athena-sm px-3 py-2 text-sm font-mono text-[#e5e7eb] placeholder-[#6b7280] focus:outline-none focus:border-[#3b82f6]"
            />
          </div>

          {/* Kind */}
          <div>
            <label className="block text-sm font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
              {t("kind")}
            </label>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as "tool" | "engine")}
              className="w-full bg-[#0A0E17] border border-[#1f2937] rounded-athena-sm px-3 py-2 text-sm font-mono text-[#e5e7eb] focus:outline-none focus:border-[#3b82f6]"
            >
              <option value="tool">{tKind("tool")}</option>
              <option value="engine">{tKind("engine")}</option>
            </select>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
              {t("category")}
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-[#0A0E17] border border-[#1f2937] rounded-athena-sm px-3 py-2 text-sm font-mono text-[#e5e7eb] focus:outline-none focus:border-[#3b82f6]"
            >
              {CATEGORY_OPTIONS.map((cat) => (
                <option key={cat} value={cat}>
                  {tCategory(cat as any)}
                </option>
              ))}
            </select>
          </div>

          {/* Risk Level */}
          <div>
            <label className="block text-sm font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
              {t("riskLevel")}
            </label>
            <select
              value={riskLevel}
              onChange={(e) => setRiskLevel(e.target.value)}
              className="w-full bg-[#0A0E17] border border-[#1f2937] rounded-athena-sm px-3 py-2 text-sm font-mono text-[#e5e7eb] focus:outline-none focus:border-[#3b82f6]"
            >
              {RISK_OPTIONS.map((level) => (
                <option key={level} value={level}>
                  {tRisk(level as any)}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
              {t("descriptionOptional")}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the tool..."
              rows={3}
              className="w-full bg-[#0A0E17] border border-[#1f2937] rounded-athena-sm px-3 py-2 text-sm font-mono text-[#e5e7eb] placeholder-[#6b7280] focus:outline-none focus:border-[#3b82f6] resize-none"
            />
          </div>

          {error && (
            <p className="text-xs font-mono text-[#EF4444]">{error}</p>
          )}

          <div className="flex gap-3 justify-end pt-2">
            <Button
              variant="secondary"
              type="button"
              onClick={onCancel}
              disabled={submitting}
            >
              {tCommon("cancel")}
            </Button>
            <Button variant="primary" type="submit" disabled={submitting}>
              {submitting ? t("registering") : t("registerBtn")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
