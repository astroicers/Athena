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

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";

interface Objective {
  id: string;
  objective: string;
  category: string;
  priority: number;
  status: string;
  evidence: string | null;
  createdAt: string;
  achievedAt: string | null;
}

const CATEGORY_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  tactical: "warning",
  strategic: "info",
  compliance: "success",
};

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  pending: "warning",
  achieved: "success",
};

export function ObjectivesPanel({ operationId }: { operationId: string }) {
  const t = useTranslations("Objectives");
  const tCommon = useTranslations("Common");
  const { addToast } = useToast();

  const [objectives, setObjectives] = useState<Objective[]>([]);
  const [loading, setLoading] = useState(true);

  // Add form state
  const [showForm, setShowForm] = useState(false);
  const [objective, setObjective] = useState("");
  const [category, setCategory] = useState("tactical");
  const [priority, setPriority] = useState(3);
  const [submitting, setSubmitting] = useState(false);

  const fetchObjectives = useCallback(async () => {
    try {
      const data = await api.get<Objective[]>(
        `/operations/${operationId}/objectives`,
      );
      setObjectives(data);
    } catch {
      setObjectives([]);
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchObjectives();
  }, [fetchObjectives]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!objective.trim()) return;
    setSubmitting(true);
    try {
      const result = await api.post<{ id: string; status: string }>(
        `/operations/${operationId}/objectives`,
        { objective: objective.trim(), category, priority },
      );
      // Prepend the new objective to the list
      setObjectives((prev) => [
        {
          id: result.id,
          objective: objective.trim(),
          category,
          priority,
          status: result.status,
          evidence: null,
          createdAt: new Date().toISOString(),
          achievedAt: null,
        },
        ...prev,
      ]);
      setObjective("");
      setCategory("tactical");
      setPriority(3);
      setShowForm(false);
      addToast(t("added"), "success");
    } catch {
      addToast(t("failedAdd"), "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleStatus(obj: Objective) {
    const newStatus = obj.status === "achieved" ? "pending" : "achieved";
    try {
      await api.patch(
        `/operations/${operationId}/objectives/${obj.id}`,
        { status: newStatus },
      );
      setObjectives((prev) =>
        prev.map((o) =>
          o.id === obj.id ? { ...o, status: newStatus } : o,
        ),
      );
      addToast(t("updated"), "success");
    } catch {
      addToast(t("failedUpdate"), "error");
    }
  }

  const inputStyles =
    "w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-[var(--radius)] px-2.5 py-1.5 text-xs font-mono text-[var(--color-text-primary)] placeholder-[var(--color-text-secondary)] focus:outline-none focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]";

  const labelStyles =
    "block text-xs font-mono text-[var(--color-text-secondary)] uppercase tracking-wider mb-0.5";

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-6 w-32 bg-[var(--color-bg-surface)] rounded-[var(--radius)] mb-2" />
        <div className="h-20 bg-[var(--color-bg-surface)] rounded-[var(--radius)]" />
      </div>
    );
  }

  return (
    <div>
      <SectionHeader
        level="card"
        trailing={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowForm(!showForm)}
            icon={
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            }
          >
            {t("addObjective")}
          </Button>
        }
      >
        {t("title")}
      </SectionHeader>

      {/* Add Objective Form */}
      {showForm && (
        <form onSubmit={handleAdd} className="mt-2 border border-[var(--color-border)] rounded-[var(--radius)] bg-[var(--color-bg-surface)] p-3 space-y-2">
          <div>
            <label className={labelStyles}>
              {t("objective")} <span className="text-[var(--color-error)]">*</span>
            </label>
            <input
              type="text"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder={t("objectivePlaceholder")}
              className={inputStyles}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelStyles}>{t("category")}</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className={inputStyles}
              >
                <option value="tactical">{t("tactical")}</option>
                <option value="strategic">{t("strategic")}</option>
                <option value="compliance">{t("compliance")}</option>
              </select>
            </div>
            <div>
              <label className={labelStyles}>{t("priority")}</label>
              <input
                type="number"
                min={1}
                max={5}
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
                className={inputStyles}
              />
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <Button variant="secondary" type="button" size="sm" onClick={() => setShowForm(false)} disabled={submitting}>
              {tCommon("cancel")}
            </Button>
            <Button variant="secondary" type="submit" size="sm" disabled={submitting || !objective.trim()}>
              {submitting ? t("adding") : t("addObjective")}
            </Button>
          </div>
        </form>
      )}

      {/* Objectives List */}
      {objectives.length === 0 ? (
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] p-4 text-center mt-2">
          <span className="text-xs font-mono text-[var(--color-text-tertiary)]">
            {t("noObjectives")}
          </span>
        </div>
      ) : (
        <div className="mt-2 space-y-2">
          {objectives.map((obj) => (
            <div
              key={obj.id}
              className="border border-[var(--color-border)] rounded-[var(--radius)] bg-[var(--color-bg-surface)] px-3 py-2 flex items-center gap-2"
            >
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-mono ${obj.status === "achieved" ? "text-[var(--color-text-tertiary)] line-through" : "text-[var(--color-text-primary)]"}`}>
                  {obj.objective}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant={CATEGORY_VARIANT[obj.category] ?? "info"}>
                    {t(obj.category as "tactical" | "strategic" | "compliance")}
                  </Badge>
                  <span className="text-xs font-mono text-[var(--color-text-tertiary)]">
                    P{obj.priority}
                  </span>
                </div>
              </div>
              <button
                onClick={() => handleToggleStatus(obj)}
                className="shrink-0"
              >
                <Badge variant={STATUS_VARIANT[obj.status] ?? "info"}>
                  {t(obj.status as "achieved" | "pending")}
                </Badge>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
