// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useOODA } from "@/hooks/useOODA";
import { useReconScan } from "@/hooks/useReconScan";
import { useToast } from "@/contexts/ToastContext";
import { PlannerPageSkeleton } from "@/components/ui/Skeleton";
import { TabBar } from "@/components/nav/TabBar";
import { MissionTab } from "@/components/planner/MissionTab";
import { AttackTab } from "@/components/planner/AttackTab";
import type { MissionStep } from "@/types/mission";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Target } from "@/types/target";
import type { ReconScanResult, ReconScanQueued } from "@/types/recon";
import type { ApiError } from "@/types/api";
import type { TechniqueWithStatus } from "@/types/technique";
import type { ToolRegistryEntry } from "@/types/tool";
import type { AttackPathResponse } from "@/types/attackPath";

const DEFAULT_OP_ID = "op-0001";

export default function PlannerPage() {
  const t = useTranslations("Planner");
  const tErrors = useTranslations("Errors");

  // --- Tab state ---
  const [activeTab, setActiveTab] = useState("mission");
  const PLANNER_TABS = useMemo(() => [
    { id: "mission", label: t("missionTab") },
    { id: "attack", label: t("attackTab") },
  ], [t]);

  const { operation } = useOperation(DEFAULT_OP_ID);
  const { addToast } = useToast();
  const ws = useWebSocket(DEFAULT_OP_ID);
  const { phase: oodaPhase } = useOODA(ws);
  const [isLoading, setIsLoading] = useState(true);
  const [steps, setSteps] = useState<MissionStep[]>([]);
  const [timeline, setTimeline] = useState<OODATimelineEntry[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [showOodaConfirm, setShowOodaConfirm] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetStatus, setResetStatus] = useState<"idle" | "resetting" | "done">("idle");

  // Phase 13: Recon UI state
  const [showAddTarget, setShowAddTarget] = useState(false);
  const { scanState, setScanState } = useReconScan(DEFAULT_OP_ID, ws, {
    onCompleted: async (data) => {
      refreshAllData();
      addToast(t("reconComplete", { factsWritten: data.factsWritten }), "success");
      // Fetch full scan result to populate ReconResultModal + update target card
      try {
        const fullResult = await api.get<ReconScanResult>(
          `/operations/${DEFAULT_OP_ID}/recon/scans/${data.scanId}`,
        );
        setReconResult(fullResult);
        if (data.targetId) {
          setTargetScans((prev) => ({ ...prev, [data.targetId]: fullResult }));
        }
      } catch {
        // Modal won't open but toast already informed the user
      }
    },
    onFailed: (error) => {
      addToast(error || tErrors("failedReconScan"), "error");
    },
  });
  const [reconResult, setReconResult] = useState<ReconScanResult | null>(null);
  const [targetScans, setTargetScans] = useState<Record<string, ReconScanResult>>({});
  const [terminalTarget, setTerminalTarget] = useState<Target | null>(null);
  const [deletingTarget, setDeletingTarget] = useState<Target | null>(null);

  // --- ATT&CK tab state ---
  const [techniques, setTechniques] = useState<TechniqueWithStatus[]>([]);
  const [selectedTech, setSelectedTech] = useState<TechniqueWithStatus | null>(null);
  const [attackPath, setAttackPath] = useState<AttackPathResponse | null>(null);
  const [allTools, setAllTools] = useState<ToolRegistryEntry[]>([]);
  const [compact, setCompact] = useState(true);

  async function fetchTargetScans(tgts: Target[]) {
    const scans: Record<string, ReconScanResult> = {};
    await Promise.all(
      tgts.map((tgt) =>
        api
          .get<ReconScanResult | null>(
            `/operations/${DEFAULT_OP_ID}/recon/scans/by-target/${tgt.id}`,
          )
          .then((r) => { if (r) scans[tgt.id] = r; })
          .catch(() => {})
      ),
    );
    setTargetScans(scans);
  }

  function refreshAllData() {
    api.get<MissionStep[]>(`/operations/${DEFAULT_OP_ID}/mission/steps`).then(setSteps).catch(() => addToast(tErrors("failedLoadSteps"), "error"));
    api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`).then(setTimeline).catch(() => addToast(tErrors("failedLoadTimeline"), "error"));
    api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`).then((tgts) => { setTargets(tgts); fetchTargetScans(tgts); }).catch(() => addToast(tErrors("failedLoadTargets"), "error"));
    api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`).then(setTechniques).catch(() => {});
  }

  function refreshTargets() {
    api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`)
      .then(setTargets)
      .catch(() => addToast(tErrors("failedLoadTargets"), "error"));
  }

  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      api.get<MissionStep[]>(`/operations/${DEFAULT_OP_ID}/mission/steps`).then(setSteps),
      api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`).then(setTimeline),
      api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`).then((tgts) => { setTargets(tgts); fetchTargetScans(tgts); }),
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`).then(setTechniques),
      api.getAttackPath(DEFAULT_OP_ID).then(setAttackPath).catch(() => setAttackPath(null)),
      api.get<ToolRegistryEntry[]>("/tools").then(setAllTools).catch(() => setAllTools([])),
    ]).catch(() => addToast(tErrors("failedLoadSteps"), "error"))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // WebSocket: refresh data on OODA, execution, reset, and recon events
  useEffect(() => {
    const unsubs = [
      ws.subscribe("ooda.phase", () => {
        refreshAllData();
      }),
      ws.subscribe("ooda.failed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        addToast((data.error as string) || tErrors("oodaFailed"), "error");
      }),
      ws.subscribe("ooda.completed", () => refreshAllData()),
      ws.subscribe("execution.update", () => refreshAllData()),
      ws.subscribe("operation.reset", () => refreshAllData()),
    ];
    return () => unsubs.forEach((fn) => fn());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws.subscribe]);

  async function handleReset() {
    setShowResetConfirm(false);
    setResetStatus("resetting");
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/reset`);
      setResetStatus("done");
      refreshAllData();
      setTimeout(() => setResetStatus("idle"), 2000);
    } catch {
      setResetStatus("idle");
      addToast(tErrors("failedResetOperation"), "error");
    }
  }

  const handleOodaTrigger = useCallback(async () => {
    setShowOodaConfirm(false);
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/ooda/trigger`);
      addToast(t("oodaStarted"), "info");
      // ooda.phase WebSocket events will trigger refreshAllData() automatically
    } catch (err) {
      const apiError = err as ApiError;
      addToast(apiError.detail || tErrors("failedTriggerOoda"), "error");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addToast]);

  async function handleExport() {
    try {
      const report = await api.get(`/operations/${DEFAULT_OP_ID}/report`);
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `athena-report-${new Date().toISOString().slice(0, 19).replace(/:/g, "")}.json`;
      a.click();
      URL.revokeObjectURL(url);
      addToast(t("reportExported"), "success");
    } catch {
      addToast(tErrors("failedExportReport"), "error");
    }
  }

  async function handleReconScan(targetId: string) {
    setScanState({ targetId, phase: null, step: 0, totalSteps: 0 });
    try {
      await api.post<ReconScanQueued>(
        `/operations/${DEFAULT_OP_ID}/recon/scan`,
        { target_id: targetId, enable_initial_access: true },
      );
      // 202 Accepted — background task started; WS events handle UI update
    } catch (err) {
      setScanState(null);
      const apiError = err as ApiError;
      addToast(apiError.detail || tErrors("failedReconScan"), "error");
    }
  }

  async function handleInitialAccess(targetId: string) {
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/recon/initial-access`, {
        target_id: targetId,
      });
      addToast(t("initialAccessStarted"), "info");
    } catch {
      addToast(tErrors("failedInitialAccess"), "error");
    }
  }

  async function handleOsintDiscover(targetId: string) {
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/osint/discover`, {
        target_id: targetId,
      });
      addToast(t("osintStarted"), "info");
    } catch {
      addToast(tErrors("failedOsint"), "error");
    }
  }

  async function handleSetActive(targetId: string, active: boolean) {
    try {
      const updated = await api.patch<Target[]>(
        `/operations/${DEFAULT_OP_ID}/targets/active`,
        { target_id: active ? targetId : "" },
      );
      setTargets(updated);
      addToast(active ? t("targetActivated") : t("targetDeactivated"), "info");
    } catch {
      addToast(tErrors("failedSetActive"), "error");
    }
  }

  function handleDeleteRequest(targetId: string) {
    const tgt = targets.find(t => t.id === targetId);
    if (!tgt) return;
    setDeletingTarget(tgt);
  }

  async function handleConfirmDelete() {
    if (!deletingTarget) return;
    const { id, hostname } = deletingTarget;
    setDeletingTarget(null);
    try {
      await api.delete(`/operations/${DEFAULT_OP_ID}/targets/${id}`);
      addToast(t("targetDeleted", { hostname }), "success");
      refreshTargets();
    } catch (err) {
      const apiError = err as ApiError;
      addToast(apiError.detail || tErrors("failedDeleteTarget"), "error");
    }
  }

  if (isLoading) return <PlannerPageSkeleton />;

  return (
    <div className="flex flex-col h-full space-y-3 athena-grid-bg">
      <TabBar tabs={PLANNER_TABS} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "mission" && (
        <MissionTab
          operationId={DEFAULT_OP_ID}
          codename={operation?.codename}
          steps={steps}
          timeline={timeline}
          targets={targets}
          oodaPhase={oodaPhase}
          resetStatus={resetStatus}
          scanState={scanState}
          targetScans={targetScans}
          reconResult={reconResult}
          terminalTarget={terminalTarget}
          deletingTarget={deletingTarget}
          showOodaConfirm={showOodaConfirm}
          showResetConfirm={showResetConfirm}
          showAddTarget={showAddTarget}
          onSetShowOodaConfirm={setShowOodaConfirm}
          onSetShowResetConfirm={setShowResetConfirm}
          onSetShowAddTarget={setShowAddTarget}
          onSetReconResult={setReconResult}
          onSetTerminalTarget={setTerminalTarget}
          onSetDeletingTarget={setDeletingTarget}
          onOodaTrigger={handleOodaTrigger}
          onReset={handleReset}
          onExport={handleExport}
          onReconScan={handleReconScan}
          onInitialAccess={handleInitialAccess}
          onSetActive={handleSetActive}
          onDeleteRequest={handleDeleteRequest}
          onConfirmDelete={handleConfirmDelete}
          onAddTargetSuccess={() => {
            setShowAddTarget(false);
            refreshTargets();
          }}
          onOsintDiscover={handleOsintDiscover}
        />
      )}

      {activeTab === "attack" && (
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
    </div>
  );
}
