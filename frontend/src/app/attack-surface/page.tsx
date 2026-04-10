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

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { api } from "@/lib/api";
import { TabBar } from "@/components/nav/TabBar";
import { AttackTab } from "@/components/planner/AttackTab";
import { AttackGraphTab } from "@/components/planner/AttackGraphTab";
import { Skeleton } from "@/components/ui/Skeleton";
import type { TechniqueWithStatus } from "@/types/technique";
import type { AttackPathResponse } from "@/types/attackPath";
import type { ToolRegistryEntry } from "@/types/tool";

/* ── Polling interval (ms) ── */
const POLL_INTERVAL = 30_000;

/* ── Loading skeleton for the page ── */
function AttackSurfaceSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="h-10 bg-[var(--color-bg-primary)] border-b border-[var(--color-border)]">
        <Skeleton className="h-full w-48 ml-6" />
      </div>
      <div className="flex-1 p-6 space-y-4">
        <Skeleton className="h-24 w-full rounded-[var(--radius)]" />
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-3">
            <Skeleton className="h-64 w-full rounded-[var(--radius)]" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-32 rounded-[var(--radius)]" />
            <Skeleton className="h-32 rounded-[var(--radius)]" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Main content ── */
function AttackSurfaceContent() {
  const t = useTranslations("AttackSurface");
  const operationId = useOperationId();

  /* ── Tab state from URL query ── */
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") === "graph" ? "graph" : "techniques";
  const [activeTab, setActiveTab] = useState(initialTab);

  const TABS = useMemo(
    () => [
      { id: "techniques", label: t("tabTechniques") },
      { id: "graph", label: t("tabGraph") },
    ],
    [t],
  );

  /* ── Data state for AttackTab ── */
  const [techniques, setTechniques] = useState<TechniqueWithStatus[]>([]);
  const [selectedTech, setSelectedTech] = useState<TechniqueWithStatus | null>(null);
  const [attackPath, setAttackPath] = useState<AttackPathResponse | null>(null);
  const [allTools, setAllTools] = useState<ToolRegistryEntry[]>([]);
  const [compact, setCompact] = useState(true);

  /* ── Loading / error ── */
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ── Fetch data ── */
  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [techs, path, tools] = await Promise.all([
        api.get<TechniqueWithStatus[]>(`/operations/${operationId}/techniques`),
        api.getAttackPath(operationId).catch(() => null),
        api.get<ToolRegistryEntry[]>("/tools").catch(() => [] as ToolRegistryEntry[]),
      ]);
      setTechniques(techs);
      setAttackPath(path);
      setAllTools(tools);
      setError(null);
    } catch {
      setError(t("errorLoad"));
    }
  }, [operationId, t]);

  /* ── Initial load ── */
  useEffect(() => {
    setIsLoading(true);
    fetchData().finally(() => setIsLoading(false));
  }, [fetchData]);

  /* ── Poll techniques every 30 seconds ── */
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!operationId) return;
    pollRef.current = setInterval(async () => {
      try {
        const techs = await api.get<TechniqueWithStatus[]>(
          `/operations/${operationId}/techniques`,
        );
        setTechniques(techs);
      } catch {
        // Silently ignore polling errors
      }
    }, POLL_INTERVAL);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [operationId]);

  /* ── Loading state ── */
  if (isLoading) {
    return <AttackSurfaceSkeleton />;
  }

  /* ── Error state ── */
  if (error) {
    return (
      <div className="flex flex-col h-full">
        <TabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />
        <div className="flex-1 flex items-center justify-center">
          <span className="font-mono text-athena-floor text-[var(--color-error)]">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <TabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "techniques" && (
        <AttackTab
          techniques={techniques}
          selectedTech={selectedTech}
          attackPath={attackPath}
          allTools={allTools}
          compact={compact}
          onSetSelectedTech={setSelectedTech}
          onSetCompact={setCompact}
        />
      )}

      {activeTab === "graph" && <AttackGraphTab />}
    </div>
  );
}

export default function AttackSurfacePage() {
  return (
    <Suspense fallback={<AttackSurfaceSkeleton />}>
      <AttackSurfaceContent />
    </Suspense>
  );
}
