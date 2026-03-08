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
import { Tooltip } from "@/components/ui/Tooltip";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useStageCounts } from "@/hooks/useStageCounts";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useOODA } from "@/hooks/useOODA";
import { useReconScan } from "@/hooks/useReconScan";
import { useToast } from "@/contexts/ToastContext";
import { PlannerPageSkeleton } from "@/components/ui/Skeleton";
import { DataTable, Column } from "@/components/data/DataTable";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import { HostNodeCard } from "@/components/cards/HostNodeCard";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { AddTargetModal } from "@/components/modal/AddTargetModal";
import { ReconResultModal } from "@/components/modal/ReconResultModal";
import { TerminalPanel } from "@/components/terminal/TerminalPanel";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { TabBar } from "@/components/nav/TabBar";
import { MITRECell } from "@/components/mitre/MITRECell";
import { KillChainIndicator } from "@/components/mitre/KillChainIndicator";
import { AttackPathTimeline } from "@/components/mitre/AttackPathTimeline";
import { TechniqueCard } from "@/components/cards/TechniqueCard";
import {
  TACTIC_ID_TO_SLUG,
  TACTIC_ORDER,
  normalizeTactic,
  tacticLabel,
  getToolsForTechnique,
} from "@/lib/mitre-mapping";
import { MissionStepStatus, RiskLevel, OODAPhase } from "@/types/enums";
import type { MissionStep } from "@/types/mission";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Target } from "@/types/target";
import type { ReconScanResult, ReconScanQueued } from "@/types/recon";
import type { ApiError } from "@/types/api";
import type { TechniqueWithStatus } from "@/types/technique";
import type { ToolRegistryEntry } from "@/types/tool";
import type { AttackPathResponse } from "@/types/attackPath";
import type { TechniqueStatus } from "@/types/enums";

const DEFAULT_OP_ID = "op-0001";

const STEP_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [MissionStepStatus.COMPLETED]: "success",
  [MissionStepStatus.RUNNING]: "info",
  [MissionStepStatus.FAILED]: "error",
  [MissionStepStatus.QUEUED]: "warning",
  [MissionStepStatus.SKIPPED]: "info",
};

type StepRow = MissionStep & Record<string, unknown>;

export default function PlannerPage() {
  const t = useTranslations("Planner");
  const tCommon = useTranslations("Common");
  const tHints = useTranslations("Hints");
  const tTips = useTranslations("Tooltips");
  const tEmpty = useTranslations("EmptyStates");
  const tErrors = useTranslations("Errors");
  const tOoda = useTranslations("OODA");
  const tStatus = useTranslations("Status");

  // --- Tab state ---
  const [activeTab, setActiveTab] = useState("mission");
  const PLANNER_TABS = useMemo(() => [
    { id: "mission", label: t("missionTab") },
    { id: "attack", label: t("attackTab") },
  ], [t]);

  const STEP_COLUMNS: Column<StepRow>[] = [
    { key: "stepNumber", header: t("colStep"), sortable: true },
    { key: "techniqueId", header: t("colTechnique"), render: (r) => (
      <span><span className="text-athena-accent">{r.techniqueId}</span> {r.techniqueName}</span>
    )},
    { key: "targetLabel", header: t("colTarget") },
    { key: "engine", header: t("colEngine"), render: (r) => String(r.engine).toUpperCase() },
    {
      key: "status",
      header: t("colStatus"),
      sortable: true,
      render: (r) => (
        <Badge variant={STEP_VARIANT[r.status] || "info"}>
          {tStatus(String(r.status) as any)}
        </Badge>
      ),
    },
  ];

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

  // --- ATT&CK tab computed data ---
  const grouped = useMemo(() => {
    const map = new Map<string, TechniqueWithStatus[]>();
    for (const tech of techniques) {
      const key = TACTIC_ID_TO_SLUG[tech.tacticId] || normalizeTactic(tech.tactic);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(tech);
    }
    return map;
  }, [techniques]);

  const orderedTactics = useMemo(() => {
    return TACTIC_ORDER.filter((tac) => grouped.has(tac));
  }, [grouped]);

  const stageCounts = useStageCounts(techniques);

  if (isLoading) return <PlannerPageSkeleton />;

  return (
    <div className="flex flex-col h-full space-y-3 athena-grid-bg">
      <TabBar tabs={PLANNER_TABS} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "mission" && (
      <div className="flex-1 space-y-4 min-h-0 overflow-y-auto">
      {/* Mission Steps + Execute */}
      <div className="flex items-center justify-between">
        <SectionHeader>
          {t("missionSteps")} — {operation?.codename || "PHANTOM-EYE"}
        </SectionHeader>
        <div className="flex items-center gap-2">
          {resetStatus === "done" && (
            <span className="text-sm font-mono text-athena-success">{t("resetOk")}</span>
          )}
          <Tooltip text={tTips("reset")}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowResetConfirm(true)}
              disabled={resetStatus === "resetting"}
              icon={
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 4v6h6" /><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                </svg>
              }
            >
              {resetStatus === "resetting" ? t("resetting") : tCommon("reset")}
            </Button>
          </Tooltip>
          {oodaPhase && (
            <span className="text-xs font-mono font-bold text-athena-accent bg-athena-accent/20 border border-athena-accent rounded-athena-sm px-3 py-1 animate-pulse">
              {tOoda(oodaPhase as "observe" | "orient" | "decide" | "act")}...
            </span>
          )}
          <Tooltip text={tTips("oodaCycle")}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowOodaConfirm(true)}
              disabled={targets.length === 0}
              icon={
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
              }
            >
              {t("oodaCycle")}
            </Button>
          </Tooltip>
          <Tooltip text={tTips("export")}>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExport}
              disabled={targets.length === 0}
              icon={
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                </svg>
              }
            >
              {tCommon("export")}
            </Button>
          </Tooltip>
        </div>
      </div>
      <p className="text-sm font-mono text-athena-text-secondary -mt-3 ml-1">{tHints("missionSteps")}</p>
      <DataTable columns={STEP_COLUMNS} data={steps as StepRow[]} keyField="id" emptyMessage={t("noSteps")} />

      {/* OODA Timeline + Host Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <OODATimeline entries={timeline} />
          <p className="text-sm font-mono text-athena-text-secondary mt-1 ml-1">{tHints("oodaTimeline")}</p>
        </div>
        <div className="space-y-3">
          <SectionHeader
            level="card"
            trailing={
              <Tooltip text={tTips("addTarget")}>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowAddTarget(true)}
                  icon={
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                  }
                >
                  {t("addTarget")}
                </Button>
              </Tooltip>
            }
          >
            {t("targetHosts")}
          </SectionHeader>
          <p className="text-sm font-mono text-athena-text-secondary -mt-2 ml-1">{tHints("targetHosts")}</p>
          {targets.length === 0 ? (
            <div className="border-2 border-dashed border-athena-border/50 rounded-athena-md p-4 text-center">
              <span className="text-xs font-mono text-athena-text-secondary whitespace-pre-line">{tEmpty("plannerGuide")}</span>
            </div>
          ) : (
            targets.map((tgt) => (
              <div key={tgt.id}>
                <HostNodeCard
                  id={tgt.id}
                  hostname={tgt.hostname}
                  ipAddress={tgt.ipAddress}
                  role={tgt.role}
                  isCompromised={tgt.isCompromised}
                  isActive={tgt.isActive}
                  privilegeLevel={tgt.privilegeLevel}
                  isScanning={scanState?.targetId === tgt.id}
                  scanPhase={scanState?.targetId === tgt.id ? scanState.phase : null}
                  scanStep={scanState?.targetId === tgt.id ? scanState.step : 0}
                  scanTotalSteps={scanState?.targetId === tgt.id ? scanState.totalSteps : 0}
                  os={targetScans[tgt.id]?.osGuess ?? null}
                  openPorts={targetScans[tgt.id]?.servicesFound}
                  services={targetScans[tgt.id]?.services?.map((s) => ({ port: s.port, service: s.service }))}
                  credentialFound={targetScans[tgt.id]?.initialAccess?.credential ?? null}
                  onScan={handleReconScan}
                  onSetActive={handleSetActive}
                  onDelete={handleDeleteRequest}
                  onViewScanResult={targetScans[tgt.id] ? () => setReconResult(targetScans[tgt.id]) : undefined}
                />
                {tgt.isCompromised && (
                  <button
                    onClick={() => setTerminalTarget(tgt)}
                    className="mt-1 w-full text-sm font-mono text-athena-success border border-athena-success/40 rounded-athena-sm py-1 hover:bg-athena-success/10 transition-colors uppercase tracking-wider"
                  >
                    {t("terminal")}
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <HexConfirmModal
        isOpen={showOodaConfirm}
        title={t("confirmOoda")}
        riskLevel={RiskLevel.MEDIUM}
        onConfirm={handleOodaTrigger}
        onCancel={() => setShowOodaConfirm(false)}
      />

      <HexConfirmModal
        isOpen={showResetConfirm}
        title={t("confirmReset")}
        riskLevel={RiskLevel.HIGH}
        onConfirm={handleReset}
        onCancel={() => setShowResetConfirm(false)}
      />

      <HexConfirmModal
        isOpen={deletingTarget !== null}
        title={t("deleteTarget", { hostname: deletingTarget?.hostname ?? "" })}
        riskLevel={RiskLevel.HIGH}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeletingTarget(null)}
      />

      <AddTargetModal
        isOpen={showAddTarget}
        operationId={DEFAULT_OP_ID}
        onSuccess={() => {
          setShowAddTarget(false);
          refreshTargets();
        }}
        onCancel={() => setShowAddTarget(false)}
      />

      <ReconResultModal
        isOpen={reconResult !== null}
        operationId={DEFAULT_OP_ID}
        result={reconResult}
        onClose={() => setReconResult(null)}
      />

      {terminalTarget && (
        <TerminalPanel
          operationId={DEFAULT_OP_ID}
          targetId={terminalTarget.id}
          targetName={terminalTarget.hostname || terminalTarget.ipAddress}
          targetIp={terminalTarget.ipAddress}
          onClose={() => setTerminalTarget(null)}
        />
      )}
      </div>
      )}

      {activeTab === "attack" && (
      <div className="flex-1 space-y-4 min-h-0 overflow-y-auto">
        {/* Attack Path Timeline */}
        <AttackPathTimeline data={attackPath} loading={false} />
        <p className="text-sm font-mono text-athena-text-secondary -mt-3 ml-1">{tHints("attackPath")}</p>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* ATT&CK Matrix */}
          <div className="lg:col-span-3">
            <SectionHeader
              className="mb-2"
              trailing={
                <button
                  onClick={() => setCompact(!compact)}
                  className="text-sm font-mono text-athena-text-secondary hover:text-athena-accent transition-colors px-2 py-0.5 border border-athena-border rounded-athena-sm"
                >
                  {compact ? t("expandView") : t("compactView")}
                </button>
              }
            >
              {t("mitreMatrix")}
            </SectionHeader>
            <p className="text-sm font-mono text-athena-text-secondary -mt-1 mb-2 ml-1">{tHints("mitreMatrix")}</p>
            <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3 overflow-x-auto">
              <div className="flex gap-2 min-w-max">
                {orderedTactics.map((tactic) => (
                  <div key={tactic} className={`${compact ? "w-20" : "w-28"} shrink-0`}>
                    <div className="text-sm font-mono text-athena-accent font-bold uppercase mb-2 truncate">
                      {tacticLabel(tactic)}
                    </div>
                    <div className="space-y-1">
                      {(grouped.get(tactic) || []).map((tech) => (
                        <MITRECell
                          key={tech.id}
                          mitreId={tech.mitreId}
                          name={tech.name}
                          status={tech.latestStatus as TechniqueStatus | null}
                          isSelected={selectedTech?.id === tech.id}
                          onClick={() => setSelectedTech(tech)}
                          compact={compact}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right sidebar — Kill Chain + Technique Card */}
          <div className="space-y-4">
            <KillChainIndicator stageCounts={stageCounts} />
            {selectedTech ? (
              <TechniqueCard
                technique={selectedTech}
                relatedTools={getToolsForTechnique(allTools, selectedTech.mitreId)}
              />
            ) : (
              <div className="border-2 border-dashed border-athena-border/50 rounded-athena-md p-4">
                <span className="text-xs font-mono text-athena-text-secondary">
                  {tEmpty("navigatorNoSelection")}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
