// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useState } from "react";
import { Button } from "@/components/atoms/Button";
import type { ToolRegistryCreate } from "@/types/tool";

interface AddToolModalProps {
  isOpen: boolean;
  onSubmit: (data: ToolRegistryCreate) => Promise<void>;
  onCancel: () => void;
}

const CATEGORY_OPTIONS = [
  "recon",
  "exploit",
  "post-exploit",
  "lateral-movement",
  "persistence",
  "exfiltration",
  "c2",
  "credential-access",
  "defense-evasion",
  "other",
];

const RISK_OPTIONS = ["low", "medium", "high", "critical"];

export function AddToolModal({ isOpen, onSubmit, onCancel }: AddToolModalProps) {
  const [toolId, setToolId] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"tool" | "engine">("tool");
  const [category, setCategory] = useState("recon");
  const [riskLevel, setRiskLevel] = useState("low");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  function resetForm() {
    setToolId("");
    setName("");
    setKind("tool");
    setCategory("recon");
    setRiskLevel("low");
    setDescription("");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!toolId.trim()) {
      setError("Tool ID is required.");
      return;
    }
    if (!name.trim()) {
      setError("Name is required.");
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
      setError(detail || "Failed to create tool. Please check the values and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
      <div className="bg-athena-surface border-2 border-athena-border rounded-athena-lg p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <span className="text-xs font-mono text-athena-text-secondary">
            NEW TOOL
          </span>
          <h2 className="text-lg font-mono font-bold text-athena-text mt-1">
            Register Tool
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Tool ID */}
          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Tool ID <span className="text-athena-error">*</span>
            </label>
            <input
              type="text"
              value={toolId}
              onChange={(e) => setToolId(e.target.value)}
              placeholder="my-custom-scanner"
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent"
            />
          </div>

          {/* Name */}
          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Name <span className="text-athena-error">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Custom Scanner"
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent"
            />
          </div>

          {/* Kind */}
          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Kind
            </label>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as "tool" | "engine")}
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text focus:outline-none focus:border-athena-accent"
            >
              <option value="tool">tool</option>
              <option value="engine">engine</option>
            </select>
          </div>

          {/* Category */}
          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text focus:outline-none focus:border-athena-accent"
            >
              {CATEGORY_OPTIONS.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Risk Level */}
          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Risk Level
            </label>
            <select
              value={riskLevel}
              onChange={(e) => setRiskLevel(e.target.value)}
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text focus:outline-none focus:border-athena-accent"
            >
              {RISK_OPTIONS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the tool..."
              rows={3}
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent resize-none"
            />
          </div>

          {error && (
            <p className="text-xs font-mono text-athena-error">{error}</p>
          )}

          <div className="flex gap-3 justify-end pt-2">
            <Button
              variant="secondary"
              type="button"
              onClick={onCancel}
              disabled={submitting}
            >
              CANCEL
            </Button>
            <Button variant="primary" type="submit" disabled={submitting}>
              {submitting ? "REGISTERING..." : "REGISTER TOOL"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
