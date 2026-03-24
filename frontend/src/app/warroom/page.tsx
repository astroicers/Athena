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
import { useTranslations } from "next-intl";
import { useOperationId } from "@/contexts/OperationContext";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useC5ISRData } from "@/hooks/useC5ISRData";
import { useReconScan } from "@/hooks/useReconScan";
import { ConstraintBanner } from "@/components/layout/ConstraintBanner";
import { TabBar } from "@/components/nav/TabBar";
import { ReconBlock } from "@/components/warroom/ReconBlock";
import { OODATimelineBlock } from "@/components/warroom/OODATimelineBlock";
import { DirectiveInput } from "@/components/warroom/DirectiveInput";
import { MissionObjective } from "@/components/warroom/MissionObjective";
import { StatusPanel } from "@/components/warroom/StatusPanel";
import { HostNodeCard } from "@/components/cards/HostNodeCard";
import { AddTargetModal } from "@/components/modal/AddTargetModal";
import { ReconResultModal } from "@/components/modal/ReconResultModal";
import { TerminalPanel } from "@/components/terminal/TerminalPanel";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { Tooltip } from "@/components/ui/Tooltip";
import { DataTable, Column } from "@/components/data/DataTable";
import { ObjectivesPanel } from "@/components/planner/ObjectivesPanel";
import { EngagementPanel } from "@/components/planner/EngagementPanel";
import { TargetSummaryPanel } from "@/components/planner/TargetSummaryPanel";
import { ExecutionEngine, MissionStepStatus, RiskLevel } from "@/types/enums";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Target } from "@/types/target";
import type { MissionStep } from "@/types/mission";
import type { ReconScanResult, ReconScanQueued } from "@/types/recon";
import type { ApiError } from "@/types/api";

/* ── Constants ── */

const POLL_MS = 15_000;

/* ── Types ── */

interface OodaIteration {
  id: string;
  iterationNumber: number;
  phase: string;
  observeSummary?: string;
  orientSummary?: string;
  decideSummary?: string;
  actSummary?: string;
  startedAt: string;
  completedAt?: string;
}

interface OodaDashboard {
  currentPhase: string;
  iterationCount: number;
  latestIteration?: OodaIteration;
  recentIterations?: OodaIteration[];
}

type WarRoomTab = "timeline" | "targets" | "mission";

const STEP_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [MissionStepStatus.COMPLETED]: "success",
  [MissionStepStatus.RUNNING]: "info",
  [MissionStepStatus.FAILED]: "error",
  [MissionStepStatus.QUEUED]: "warning",
  [MissionStepStatus.SKIPPED]: "info",
};

type StepRow = MissionStep & Record<string, unknown>;

/* ── Main Content ── */

function WarRoomContent() {
  const t = useTranslations("WarRoom");
  const tErrors = useTranslations("Errors");
  const tCommon = useTranslations("Common");
  const tHints = useTranslations("Hints");
  const tTips = useTranslations("Tooltips");
  const tEmpty = useTranslations("EmptyStates");
  const tStatus = useTranslations("Status");
  const operationId = useOperationId();
  const { addToast } = useToast();

  /* ── Tab state ── */
  const [activeTab, setActiveTab] = useState<WarRoomTab>("timeline");
  const TABS = useMemo(() => [
    { id: "timeline", label: t("tabTimeline") },
    { id: "targets", label: t("tabTargets") },
    { id: "mission", label: t("tabMission") },
  ], [t]);

  /* ── Shared state ── */
  const [dashboard, setDashboard] = useState<OodaDashboard | null>(null);
  const [timeline, setTimeline] = useState<OODATimelineEntry[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [autoMode, setAutoMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ── Targets tab state ── */
  const [showAddTarget, setShowAddTarget] = useState(false);
  const [reconResult, setReconResult] = useState<ReconScanResult | null>(null);
  const [targetScans, setTargetScans] = useState<Record<string, ReconScanResult>>({});
  const [terminalTarget, setTerminalTarget] = useState<Target | null>(null);
  const [deletingTarget, setDeletingTarget] = useState<Target | null>(null);
  const [summaryTargetId, setSummaryTargetId] = useState<string | null>(null);

  /* ── Mission tab state ── */
  const [steps, setSteps] = useState<MissionStep[]>([]);
  const [showCreateStep, setShowCreateStep] = useState(false);
  const [newStep, setNewStep] = useState({
    stepNumber: 1,
    techniqueId: "",
    techniqueName: "",
    targetId: "",
    engine: ExecutionEngine.SSH as string,
  });
  const [creatingStep, setCreatingStep] = useState(false);
  const [editingStepId, setEditingStepId] = useState<string | null>(null);

  // WebSocket + C5ISR data hook
  const ws = useWebSocket(operationId);
  const { domains, constraints, override } = useC5ISRData(operationId, ws);

  // Recon scan hook
  const { scanState, setScanState } = useReconScan(operationId, ws, {
    onCompleted: async (data) => {
      fetchData();
      addToast(t("reconComplete", { factsWritten: data.factsWritten }), "success");
      try {
        const fullResult = await api.get<ReconScanResult>(
          `/operations/${operationId}/recon/scans/${data.scanId}`,
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

  /* ── Data fetching ── */

  async function fetchTargetScans(tgts: Target[]) {
    const scans: Record<string, ReconScanResult> = {};
    await Promise.all(
      tgts.map((tgt) =>
        api
          .get<ReconScanResult | null>(
            `/operations/${operationId}/recon/scans/by-target/${tgt.id}`,
          )
          .then((r) => { if (r) scans[tgt.id] = r; })
          .catch(() => {})
      ),
    );
    setTargetScans(scans);
  }

  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [dashData, timelineData, targetData, stepsData] = await Promise.allSettled([
        api.get<OodaDashboard>(
          `/operations/${operationId}/ooda/dashboard`,
        ),
        api.get<OODATimelineEntry[]>(
          `/operations/${operationId}/ooda/timeline`,
        ),
        api.get<Target[]>(
          `/operations/${operationId}/targets`,
        ),
        api.get<MissionStep[]>(
          `/operations/${operationId}/mission/steps`,
        ),
      ]);

      if (dashData.status === "fulfilled" && dashData.value) {
        setDashboard(dashData.value);
      }
      if (timelineData.status === "fulfilled" && timelineData.value) {
        setTimeline(
          Array.isArray(timelineData.value) ? timelineData.value : [],
        );
      }
      if (targetData.status === "fulfilled" && targetData.value) {
        const tgts = Array.isArray(targetData.value) ? targetData.value : [];
        setTargets(tgts);
        fetchTargetScans(tgts);
      }
      if (stepsData.status === "fulfilled" && stepsData.value) {
        setSteps(
          Array.isArray(stepsData.value) ? stepsData.value : [],
        );
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [operationId]);

  useEffect(() => {
    fetchData();
    timerRef.current = setInterval(fetchData, POLL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchData]);

  // WebSocket: refresh on relevant events
  useEffect(() => {
    const unsubs = [
      ws.subscribe("ooda.phase", () => fetchData()),
      ws.subscribe("ooda.completed", () => fetchData()),
      ws.subscribe("execution.update", () => fetchData()),
      ws.subscribe("operation.reset", () => fetchData()),
    ];
    return () => unsubs.forEach((fn) => fn());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws.subscribe]);

  /* ── Derived data (Timeline tab) ── */

  const rawIterations = dashboard?.recentIterations ?? (dashboard?.latestIteration ? [dashboard.latestIteration] : []);
  const iterations = rawIterations.map((iter) => {
    const entry = timeline.find(
      (e) => e.iterationNumber === iter.iterationNumber && e.targetHostname,
    );
    return {
      ...iter,
      targetHostname: entry?.targetHostname,
      targetIp: entry?.targetIp,
    };
  });
  const reconEntries = timeline.filter((e) => e.iterationNumber === 0);

  const targetStats = targets.map((tgt) => ({
    id: tgt.id,
    hostname: tgt.hostname,
    ipAddress: tgt.ipAddress,
    isCompromised: tgt.isCompromised,
    privilegeLevel: tgt.privilegeLevel ?? "none",
    iterationCount: iterations.filter((iter) => {
      const entry = timeline.find(
        (e) => e.iterationNumber === iter.iterationNumber && e.phase === "act",
      );
      return entry?.targetId === tgt.id;
    }).length,
  }));

  const bannerData = {
    active: (constraints?.hardLimits?.length ?? 0) > 0,
    messages: constraints?.hardLimits?.map((l) => l.suggestedAction) ?? [],
    domains: constraints?.hardLimits?.map((l) => l.domain) ?? [],
  };

  const noiseLevel = 32;
  const riskLevel = "LOW";
  const matrixAction = "GO";
  const confidence = 0.78;

  /* ── Handlers: Timeline ── */

  const handleDirective = useCallback(
    async (directive: string) => {
      if (!operationId || !dashboard?.latestIteration) return;
      try {
        await api.post(
          `/operations/${operationId}/ooda/${dashboard.latestIteration.id}/directive`,
          { directive },
        );
        fetchData();
      } catch {
        // silent
      }
    },
    [operationId, dashboard, fetchData],
  );

  /* ── Handlers: Targets ── */

  async function handleReconScan(targetId: string) {
    setScanState({ targetId, phase: null, step: 0, totalSteps: 0 });
    try {
      await api.post<ReconScanQueued>(
        `/operations/${operationId}/recon/scan`,
        { target_id: targetId, enable_initial_access: true },
      );
    } catch (err) {
      setScanState(null);
      const apiError = err as ApiError;
      addToast(apiError.detail || tErrors("failedReconScan"), "error");
    }
  }

  async function handleInitialAccess(targetId: string) {
    try {
      await api.post(`/operations/${operationId}/recon/initial-access`, {
        target_id: targetId,
      });
      addToast(t("initialAccessStarted"), "info");
    } catch {
      addToast(tErrors("failedInitialAccess"), "error");
    }
  }

  async function handleOsintDiscover(targetId: string) {
    try {
      await api.post(`/operations/${operationId}/osint/discover`, {
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
        `/operations/${operationId}/targets/active`,
        { target_id: active ? targetId : "" },
      );
      setTargets(updated);
      addToast(active ? t("targetActivated") : t("targetDeactivated"), "info");
    } catch {
      addToast(tErrors("failedSetActive"), "error");
    }
  }

  function handleDeleteRequest(targetId: string) {
    const tgt = targets.find(tg => tg.id === targetId);
    if (!tgt) return;
    setDeletingTarget(tgt);
  }

  async function handleConfirmDelete() {
    if (!deletingTarget) return;
    const { id, hostname } = deletingTarget;
    setDeletingTarget(null);
    try {
      await api.delete(`/operations/${operationId}/targets/${id}`);
      addToast(t("targetDeleted", { hostname }), "success");
      refreshTargets();
    } catch (err) {
      const apiError = err as ApiError;
      addToast(apiError.detail || tErrors("failedDeleteTarget"), "error");
    }
  }

  function refreshTargets() {
    api.get<Target[]>(`/operations/${operationId}/targets`)
      .then((tgts) => { setTargets(tgts); fetchTargetScans(tgts); })
      .catch(() => addToast(tErrors("failedLoadTargets"), "error"));
  }

  /* ── Handlers: Mission ── */

  function refreshSteps() {
    api.get<MissionStep[]>(`/operations/${operationId}/mission/steps`)
      .then(setSteps)
      .catch(() => addToast(tErrors("failedLoadSteps"), "error"));
  }

  async function handleCreateStep(e: React.FormEvent) {
    e.preventDefault();
    if (!newStep.techniqueId.trim() || !newStep.techniqueName.trim() || !newStep.targetId) return;
    setCreatingStep(true);
    const selectedTarget = targets.find((tgt) => tgt.id === newStep.targetId);
    try {
      await api.post(
        `/operations/${operationId}/mission/steps`,
        {
          stepNumber: newStep.stepNumber,
          techniqueId: newStep.techniqueId.trim(),
          techniqueName: newStep.techniqueName.trim(),
          targetId: newStep.targetId,
          targetLabel: selectedTarget?.hostname || selectedTarget?.ipAddress || newStep.targetId,
          engine: newStep.engine,
        },
      );
      addToast(t("stepCreated"), "success");
      setShowCreateStep(false);
      setNewStep({
        stepNumber: (steps.length > 0 ? Math.max(...steps.map((s) => s.stepNumber)) + 1 : 1) + 1,
        techniqueId: "",
        techniqueName: "",
        targetId: "",
        engine: ExecutionEngine.SSH,
      });
      refreshSteps();
    } catch {
      addToast(t("failedCreateStep"), "error");
    } finally {
      setCreatingStep(false);
    }
  }

  async function handleStepStatusChange(stepId: string, newStatus: string) {
    try {
      await api.patch(
        `/operations/${operationId}/mission/steps/${stepId}`,
        { status: newStatus },
      );
      addToast(t("stepUpdated"), "success");
      setEditingStepId(null);
      refreshSteps();
    } catch {
      addToast(t("failedUpdateStep"), "error");
    }
  }

  /* ── Mission step table columns ── */

  const STEP_COLUMNS: Column<StepRow>[] = [
    { key: "stepNumber", header: t("colStep"), sortable: true, width: 60 },
    {
      key: "techniqueId",
      header: t("colTechnique"),
      width: 280,
      render: (r) => (
        <span>
          <span className="text-[var(--color-accent)] font-semibold">{r.techniqueId}</span>{" "}
          <span className="text-[var(--color-text-tertiary)]">{r.techniqueName}</span>
        </span>
      ),
    },
    { key: "targetLabel", header: t("colTarget") },
    { key: "engine", header: t("colEngine"), render: (r) => String(r.engine).toUpperCase() },
    {
      key: "status",
      header: t("colStatus"),
      sortable: true,
      width: 100,
      render: (r) =>
        editingStepId === r.id ? (
          <select
            value={r.status}
            onChange={(e) => handleStepStatusChange(r.id, e.target.value)}
            onBlur={() => setTimeout(() => setEditingStepId(null), 150)}
            autoFocus
            className="bg-[var(--color-bg-primary)] border border-[var(--color-accent)] rounded-[var(--radius)] px-2 py-1 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
          >
            {Object.values(MissionStepStatus).map((s) => (
              <option key={s} value={s}>{tStatus(s as Parameters<typeof tStatus>[0])}</option>
            ))}
          </select>
        ) : (
          <button onClick={() => setEditingStepId(r.id)} className="cursor-pointer">
            <Badge variant={STEP_VARIANT[r.status] || "info"}>
              {tStatus(String(r.status) as Parameters<typeof tStatus>[0])}
            </Badge>
          </button>
        ),
    },
  ];

  /* ── Shared styles ── */

  const inputStyles =
    "w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-[var(--radius)] px-2.5 py-1.5 text-xs font-mono text-[var(--color-text-primary)] placeholder-[var(--color-text-secondary)] focus:outline-none focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]";

  const labelStyles =
    "block text-xs font-mono text-[var(--color-text-secondary)] uppercase tracking-wider mb-0.5";

  /* ── Loading state ── */

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm font-mono text-athena-text-tertiary">
          {t("title")}...
        </p>
      </div>
    );
  }

  /* ── Render ── */

  return (
    <div className="flex flex-col h-full overflow-hidden bg-athena-bg">
      {/* Constraint Banner */}
      <ConstraintBanner constraints={bannerData} onOverride={override} />

      {/* Tab Bar */}
      <TabBar tabs={TABS} activeTab={activeTab} onChange={(id) => setActiveTab(id as WarRoomTab)} />

      {/* ═══════════ TIMELINE TAB ═══════════ */}
      {activeTab === "timeline" && (
        <div className="flex flex-1 min-h-0">
          {/* Main: Vertical Campaign Timeline */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="font-mono text-xs font-bold text-athena-text-tertiary uppercase tracking-widest">
                  {t("campaignTimeline")}
                </h2>
                {dashboard && (
                  <span className="font-mono text-xs text-athena-accent font-bold">
                    {t("oodaIteration", { num: dashboard.iterationCount })}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setAutoMode(!autoMode)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-[var(--radius)] text-xs font-mono font-semibold transition-colors ${
                    autoMode
                      ? "bg-athena-accent-bg text-athena-accent border border-[var(--color-accent)]/25"
                      : "bg-athena-surface text-athena-text-tertiary border border-[var(--color-border)]"
                  }`}
                >
                  <span className={`w-2.5 h-2.5 rounded-full ${autoMode ? "bg-athena-accent" : "bg-athena-text-tertiary"}`} />
                  {autoMode ? t("autoMode") : t("manualMode")}
                </button>
              </div>
            </div>

            {/* Recon Block */}
            {reconEntries.length > 0 && (
              <ReconBlock entries={reconEntries} />
            )}

            {/* OODA Iteration Blocks */}
            {iterations.map((iter, idx) => {
              const isCurrent = idx === iterations.length - 1 && !iter.completedAt;
              return (
                <div key={iter.id}>
                  {/* Connector line */}
                  {idx > 0 || reconEntries.length > 0 ? (
                    <div className="flex justify-center py-1">
                      <div className="w-px h-4 bg-athena-border" />
                    </div>
                  ) : null}

                  {/* OODA Block */}
                  <OODATimelineBlock
                    iteration={iter}
                    c5isrDomains={domains}
                    constraints={constraints ?? undefined}
                    isCurrent={isCurrent}
                    timelineEntries={timeline}
                  />

                  {/* Directive Input (after completed iterations) */}
                  {iter.completedAt && (
                    <div className="mt-2">
                      <DirectiveInput
                        iterationId={iter.id}
                        autoMode={autoMode}
                        onToggleAutoMode={() => setAutoMode(!autoMode)}
                        onSubmit={handleDirective}
                      />
                    </div>
                  )}
                </div>
              );
            })}

            {/* Connector to Mission */}
            {iterations.length > 0 && (
              <div className="flex justify-center py-1">
                <div className="w-px h-4 bg-athena-border" />
              </div>
            )}

            {/* Mission Objective */}
            <MissionObjective
              objective="Domain Admin on corp.local"
              targetsCompromised={iterations.filter((i) => i.completedAt).length}
              targetsTotal={5}
            />
          </div>

          {/* Right: Status Panel */}
          <StatusPanel
            c5isrDomains={domains}
            noiseLevel={noiseLevel}
            riskLevel={riskLevel}
            matrixAction={matrixAction}
            confidence={confidence}
            targets={targetStats}
          />
        </div>
      )}

      {/* ═══════════ TARGETS TAB ═══════════ */}
      {activeTab === "targets" && (
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Header + Add Target */}
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
          <p className="text-xs font-mono text-[var(--color-text-tertiary)] -mt-2 ml-0.5">{tHints("targetHosts")}</p>

          {/* Target cards grid */}
          {targets.length === 0 ? (
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] p-4 text-center">
              <span className="text-xs font-mono text-[var(--color-text-tertiary)] whitespace-pre-line">{tEmpty("plannerGuide")}</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {targets.map((tgt) => (
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
                  {/* Per-target action buttons */}
                  <div className="flex gap-1.5 mt-1.5">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleOsintDiscover(tgt.id)}
                      className="flex-1 text-xs text-[var(--color-accent)] border-[var(--color-accent)]/[0.25] bg-transparent hover:bg-[var(--color-accent)]/10 uppercase tracking-wider"
                    >
                      {t("osintDiscover")}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleInitialAccess(tgt.id)}
                      disabled={scanState?.targetId === tgt.id}
                      className="flex-1 text-xs text-[var(--color-warning)] border-[var(--color-warning)]/[0.25] bg-transparent hover:bg-[var(--color-warning)]/[0.12] uppercase tracking-wider"
                    >
                      {t("initialAccess")}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        setSummaryTargetId((prev) =>
                          prev === tgt.id ? null : tgt.id,
                        )
                      }
                      className="flex-1 text-xs bg-[var(--color-accent)]/[0.12] border-[var(--color-accent)]/[0.40] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 uppercase tracking-wider"
                    >
                      {t("aiSummary")}
                    </Button>
                    {tgt.isCompromised && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setTerminalTarget(tgt)}
                        className="flex-1 text-xs text-[var(--color-success)] border-[var(--color-success)]/[0.25] bg-transparent hover:bg-[var(--color-success)]/10 uppercase tracking-wider"
                      >
                        {t("terminal")}
                      </Button>
                    )}
                  </div>
                  {/* AI Summary Panel */}
                  {summaryTargetId === tgt.id && (
                    <div className="mt-2.5">
                      <TargetSummaryPanel
                        operationId={operationId}
                        targetId={tgt.id}
                        hostname={tgt.hostname}
                        onClose={() => setSummaryTargetId(null)}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Modals for Targets */}
          <HexConfirmModal
            isOpen={deletingTarget !== null}
            title={t("deleteTarget", { hostname: deletingTarget?.hostname ?? "" })}
            riskLevel={RiskLevel.HIGH}
            onConfirm={handleConfirmDelete}
            onCancel={() => setDeletingTarget(null)}
          />

          <AddTargetModal
            isOpen={showAddTarget}
            operationId={operationId}
            onSuccess={() => {
              setShowAddTarget(false);
              refreshTargets();
            }}
            onCancel={() => setShowAddTarget(false)}
          />

          <ReconResultModal
            isOpen={reconResult !== null}
            operationId={operationId}
            result={reconResult}
            onClose={() => setReconResult(null)}
          />

          {terminalTarget && (
            <TerminalPanel
              operationId={operationId}
              targetId={terminalTarget.id}
              targetName={terminalTarget.hostname || terminalTarget.ipAddress}
              targetIp={terminalTarget.ipAddress}
              onClose={() => setTerminalTarget(null)}
            />
          )}
        </div>
      )}

      {/* ═══════════ MISSION TAB ═══════════ */}
      {activeTab === "mission" && (
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* Mission Steps Header */}
          <div className="flex items-center justify-between">
            <h2 className="font-mono text-[13px] font-bold text-[var(--color-text-primary)] tracking-wide uppercase">
              {t("missionSteps")}
            </h2>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowCreateStep(true)}
              icon={
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              }
            >
              {t("createStep")}
            </Button>
          </div>
          <p className="text-xs font-mono text-[var(--color-text-tertiary)] -mt-3 ml-0.5">{tHints("missionSteps")}</p>
          <DataTable columns={STEP_COLUMNS} data={steps as StepRow[]} keyField="id" emptyMessage={t("noSteps")} />

          {/* Objectives */}
          <ObjectivesPanel operationId={operationId} />

          {/* Engagement / ROE */}
          <EngagementPanel operationId={operationId} />

          {/* Create Step Modal */}
          {showCreateStep && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] p-4 max-w-md w-full mx-4">
                <div className="mb-3">
                  <span className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">{t("missionSteps")}</span>
                  <h2 className="text-sm font-mono font-bold text-[var(--color-text-primary)] mt-0.5">{t("createStep")}</h2>
                </div>
                <form onSubmit={handleCreateStep} className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={labelStyles}>{t("stepNumber")}</label>
                      <input
                        type="number"
                        min={1}
                        value={newStep.stepNumber}
                        onChange={(e) => setNewStep((s) => ({ ...s, stepNumber: Number(e.target.value) }))}
                        className={inputStyles}
                      />
                    </div>
                    <div>
                      <label className={labelStyles}>{t("engine")}</label>
                      <select
                        value={newStep.engine}
                        onChange={(e) => setNewStep((s) => ({ ...s, engine: e.target.value }))}
                        className={inputStyles}
                      >
                        <option value={ExecutionEngine.SSH}>{t("engineSsh")}</option>
                        <option value={ExecutionEngine.PERSISTENT_SSH}>{t("enginePersistentSsh")}</option>
                        <option value={ExecutionEngine.C2}>{t("engineC2")}</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className={labelStyles}>
                      {t("techniqueId")} <span className="text-[var(--color-error)]">*</span>
                    </label>
                    <input
                      type="text"
                      value={newStep.techniqueId}
                      onChange={(e) => setNewStep((s) => ({ ...s, techniqueId: e.target.value }))}
                      placeholder="T1059.001"
                      className={inputStyles}
                    />
                  </div>
                  <div>
                    <label className={labelStyles}>
                      {t("techniqueName")} <span className="text-[var(--color-error)]">*</span>
                    </label>
                    <input
                      type="text"
                      value={newStep.techniqueName}
                      onChange={(e) => setNewStep((s) => ({ ...s, techniqueName: e.target.value }))}
                      placeholder="PowerShell"
                      className={inputStyles}
                    />
                  </div>
                  <div>
                    <label className={labelStyles}>
                      {t("targetId")} <span className="text-[var(--color-error)]">*</span>
                    </label>
                    <select
                      value={newStep.targetId}
                      onChange={(e) => setNewStep((s) => ({ ...s, targetId: e.target.value }))}
                      className={inputStyles}
                    >
                      <option value="">--</option>
                      {targets.map((tgt) => (
                        <option key={tgt.id} value={tgt.id}>
                          {tgt.hostname || tgt.ipAddress}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex gap-3 justify-end pt-2">
                    <Button variant="secondary" type="button" onClick={() => setShowCreateStep(false)} disabled={creatingStep}>
                      {tCommon("cancel")}
                    </Button>
                    <Button
                      variant="secondary"
                      type="submit"
                      disabled={creatingStep || !newStep.techniqueId.trim() || !newStep.techniqueName.trim() || !newStep.targetId}
                    >
                      {creatingStep ? t("creating") : t("createStep")}
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Page wrapper ── */

export default function WarRoomPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-sm font-mono text-athena-text-tertiary">
            Loading War Room...
          </p>
        </div>
      }
    >
      <WarRoomContent />
    </Suspense>
  );
}
