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
import { ConstraintBanner } from "@/components/layout/ConstraintBanner";
import { TabBar } from "@/components/nav/TabBar";
import { OODATimelineBlock } from "@/components/warroom/OODATimelineBlock";
import { CommandBar } from "@/components/warroom/CommandBar";
import { ModeControl } from "@/components/warroom/ModeControl";
import { MissionObjective } from "@/components/warroom/MissionObjective";
import { StatusPanel } from "@/components/warroom/StatusPanel";
import { AddTargetModal } from "@/components/modal/AddTargetModal";
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
import { TargetDetailPanel } from "@/components/warroom/TargetDetailPanel";
import { BriefTab } from "@/components/warroom/BriefTab";
import { ExecutionEngine, MissionStepStatus, RiskLevel } from "@/types/enums";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Target } from "@/types/target";
import type { MissionStep } from "@/types/mission";
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

type WarRoomTab = "timeline" | "targets" | "mission" | "brief";

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
    { id: "brief", label: t("tabBrief") },
  ], [t]);

  /* ── Shared state ── */
  const [dashboard, setDashboard] = useState<OodaDashboard | null>(null);
  const [timeline, setTimeline] = useState<OODATimelineEntry[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [autoMode, setAutoMode] = useState(false);
  const [relayAvailable, setRelayAvailable] = useState(false);
  const [pivotIterations, setPivotIterations] = useState<Record<number, { from: string; to: string }>>({});
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ── Targets tab state ── */
  const [showAddTarget, setShowAddTarget] = useState(false);
  const [terminalTarget, setTerminalTarget] = useState<Target | null>(null);
  const [deletingTarget, setDeletingTarget] = useState<Target | null>(null);
  const [summaryTargetId, setSummaryTargetId] = useState<string | null>(null);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);
  const [targetFacts, setTargetFacts] = useState<Array<{ trait: string; value: string; category: string }>>([]);

  /* ── Objectives state ── */
  const [objectives, setObjectives] = useState<Array<{ id: string; objective: string; status: string }>>([]);

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

  /* ── Data fetching ── */

  const fetchData = useCallback(async () => {
    if (!operationId) return;
    try {
      const [dashData, timelineData, targetData, stepsData, objData] = await Promise.allSettled([
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
        api.get<Array<{ id: string; objective: string; status: string }>>(
          `/operations/${operationId}/objectives`,
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
      }
      if (stepsData.status === "fulfilled" && stepsData.value) {
        setSteps(
          Array.isArray(stepsData.value) ? stepsData.value : [],
        );
      }
      if (objData.status === "fulfilled" && objData.value) {
        setObjectives(
          Array.isArray(objData.value) ? objData.value : [],
        );
      }
      // Sync auto-mode status from backend
      try {
        const autoStatus = await api.get<{ running: boolean; relay_available?: boolean }>(
          `/operations/${operationId}/ooda/auto-status`,
        );
        setAutoMode(autoStatus.running ?? false);
        setRelayAvailable(autoStatus.relay_available ?? false);
      } catch {
        // auto-status endpoint may not exist for new operations
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
      ws.subscribe("brief.updated", () => {
        const w = window as unknown as Record<string, unknown>;
        if (typeof w.__briefRefresh === "function") (w.__briefRefresh as () => void)();
      }),
      ws.subscribe("ooda.pivot", (data) => {
        const d = data as { iteration?: number; from_technique?: string; to_technique?: string };
        if (d.iteration != null && d.from_technique && d.to_technique) {
          setPivotIterations((prev) => ({
            ...prev,
            [d.iteration!]: { from: d.from_technique!, to: d.to_technique! },
          }));
        }
      }),
    ];
    return () => unsubs.forEach((fn) => fn());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws.subscribe]);

  /* ── Selected target + facts fetch ── */

  const selectedTarget = targets.find((tg) => tg.id === selectedTargetId) ?? null;

  useEffect(() => {
    if (selectedTargetId && operationId) {
      api
        .get<Array<{ trait: string; value: string; category: string }>>(
          `/operations/${operationId}/facts?target_id=${selectedTargetId}`,
        )
        .then((data) => setTargetFacts(Array.isArray(data) ? data : []))
        .catch(() => setTargetFacts([]));
    } else {
      setTargetFacts([]);
    }
  }, [selectedTargetId, operationId]);

  /* ── Derived data (Timeline tab) ─────────────────────────────────
   *
   * Every `.map`/`.filter` entry point below is guarded with
   * `Array.isArray(...)` and optional chaining on record fields.
   * The backend is mostly well-typed, but WebSocket-driven refreshes
   * and polling races occasionally deliver empty objects or partial
   * records. Without these guards, a single bad shape would throw
   * during render and the Next.js error boundary would take over the
   * whole War Room page.
   */

  const rawIterations = Array.isArray(dashboard?.recentIterations)
    ? dashboard!.recentIterations
    : (dashboard?.latestIteration ? [dashboard.latestIteration] : []);

  const safeTimeline = Array.isArray(timeline) ? timeline : [];

  const iterations = rawIterations.map((iter) => {
    const entry = safeTimeline.find(
      (e) => e?.iterationNumber === iter?.iterationNumber && e?.targetHostname,
    );
    return {
      ...iter,
      targetHostname: entry?.targetHostname,
      targetIp: entry?.targetIp,
    };
  });

  const targetStats = (Array.isArray(targets) ? targets : [])
    .filter((tgt): tgt is NonNullable<typeof tgt> => !!tgt && typeof tgt.id === "string")
    .map((tgt) => ({
      id: tgt.id,
      hostname: tgt.hostname ?? "",
      ipAddress: tgt.ipAddress ?? "",
      isCompromised: !!tgt.isCompromised,
      privilegeLevel: tgt.privilegeLevel ?? "none",
      iterationCount: iterations.filter((iter) => {
        const entry = safeTimeline.find(
          (e) => e?.iterationNumber === iter?.iterationNumber && e?.phase === "act",
        );
        return entry?.targetId === tgt.id;
      }).length,
    }));

  const hardLimits = Array.isArray(constraints?.hardLimits)
    ? constraints!.hardLimits
    : [];
  const bannerData = {
    active: hardLimits.length > 0,
    messages: hardLimits
      .map((l) => l?.suggestedAction ?? "")
      .filter((msg): msg is string => !!msg),
    domains: hardLimits
      .map((l) => l?.domain ?? "")
      .filter((d): d is string => !!d),
  };

  // Decision action derived from OODA phase
  const matrixAction = dashboard?.currentPhase === "decide" || dashboard?.currentPhase === "act" ? "GO" : "HOLD";

  /* ── Handlers: Timeline ── */

  const handleToggleAuto = useCallback(async () => {
    try {
      if (autoMode) {
        await api.delete(`/operations/${operationId}/ooda/auto-stop`);
        setAutoMode(false);
        addToast(t("autoStopped"), "success");
      } else {
        await api.post(`/operations/${operationId}/ooda/auto-start`);
        setAutoMode(true);
        addToast(t("autoStarted"), "success");
      }
    } catch {
      addToast(tErrors("failedAutoToggle"), "error");
    }
  }, [operationId, autoMode, addToast, t, tErrors]);

  const handleDirective = useCallback(
    async (directive: string) => {
      if (!operationId) return;
      try {
        await api.post(
          `/operations/${operationId}/ooda/directive`,
          { directive, scope: "next_cycle" },
        );
        addToast(t("directiveSent"), "success");
        fetchData();
      } catch {
        addToast(tErrors("failedDirective"), "error");
      }
    },
    [operationId, addToast, t, tErrors, fetchData],
  );

  /* ── Handlers: Targets ── */

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
      .then((tgts) => { setTargets(tgts); })
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
            className="bg-[var(--color-bg-primary)] border border-[var(--color-accent)] rounded-[var(--radius)] px-2 py-1 text-athena-floor font-mono text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
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
    "w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-[var(--radius)] px-2.5 py-1.5 text-athena-floor font-mono text-[var(--color-text-primary)] placeholder-[var(--color-text-secondary)] focus:outline-none focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]";

  const labelStyles =
    "block text-athena-floor font-mono text-[var(--color-text-secondary)] uppercase tracking-wider mb-0.5";

  /* ── Loading state ── */

  if (loading && !dashboard) {
    return (
      <main className="flex items-center justify-center h-full">
        <p className="text-athena-body font-mono text-athena-text-tertiary">
          {t("title")}...
        </p>
      </main>
    );
  }

  /* ── Render ── */

  return (
    <main className="flex flex-col h-full overflow-hidden bg-athena-bg">
      {/* Constraint Banner */}
      <ConstraintBanner constraints={bannerData} onOverride={override} />

      {/* Tab Bar + Mode Control */}
      <div className="flex items-center justify-between pr-4">
        <TabBar tabs={TABS} activeTab={activeTab} onChange={(id) => setActiveTab(id as WarRoomTab)} />
        <ModeControl isAutoMode={autoMode} onToggle={handleToggleAuto} />
      </div>

      {/* ═══════════ TIMELINE TAB ═══════════ */}
      {activeTab === "timeline" && (
        <div className="flex flex-1 min-h-0">
          {/* Main: Vertical Campaign Timeline */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="font-mono text-athena-floor font-bold text-athena-text-tertiary uppercase tracking-widest">
                  {t("campaignTimeline")}
                </h2>
                {dashboard && (
                  <span className="font-mono text-athena-floor text-athena-accent font-bold">
                    {t("oodaIteration", { num: dashboard.iterationCount })}
                  </span>
                )}
              </div>
              {/* Mode control moved to tab bar */}
            </div>

            {/* Empty state guide — shown when no iterations and no targets */}
            {iterations.length === 0 && targets.length === 0 && (
              <div className="border border-dashed border-[var(--color-border)] rounded-[var(--radius)] p-6 mt-2">
                <pre className="font-mono text-athena-floor text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed">
                  {tEmpty("plannerGuide")}
                </pre>
              </div>
            )}

            {/* OODA loading state — targets exist but no iterations yet */}
            {iterations.length === 0 && targets.length > 0 && (
              <div className="flex flex-col items-center justify-center py-16 gap-4">
                <div className="relative w-12 h-12">
                  <div className="absolute inset-0 rounded-full border-2 border-[var(--color-border)]" />
                  <div className="absolute inset-0 rounded-full border-2 border-t-[var(--color-accent)] animate-spin" />
                </div>
                <span className="font-mono text-athena-floor text-[var(--color-text-secondary)]">
                  OODA Observe — scanning targets...
                </span>
                <span className="font-mono text-[10px] text-[var(--color-text-tertiary)]">
                  {targets.length} target(s) queued
                </span>
              </div>
            )}

            {/* Mission Objective — pinned at top so it's always visible */}
            {objectives.length > 0 && (
              <MissionObjective
                objective={objectives[0].objective}
                targetsCompromised={targets.filter((tgt) => tgt.isCompromised).length}
                targetsTotal={targets.length}
              />
            )}

            {/* Connector from Mission to latest iteration */}
            {iterations.length > 0 && objectives.length > 0 && (
              <div className="flex justify-center py-1">
                <div className="w-px h-4 bg-athena-border" />
              </div>
            )}

            {/* OODA Iteration Blocks — newest first (idx=0 is most recent) */}
            {iterations.map((iter, idx) => {
              const isCurrent = idx === 0 && !iter.completedAt;
              return (
                <div key={iter.id}>
                  {/* Connector line */}
                  {idx > 0 ? (
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
                    pivotInfo={pivotIterations[iter.iterationNumber]}
                  />
                </div>
              );
            })}
          </div>

          {/* Right: Status Panel */}
          <StatusPanel
            c5isrDomains={domains}
            matrixAction={matrixAction}
            targets={targetStats}
            relayAvailable={relayAvailable}
          />
        </div>
      )}

      {/* ═══════════ TARGETS TAB ═══════════ */}
      {activeTab === "targets" && (
        <div className="flex flex-1 min-h-0">
          {/* Left: Target List (300px) */}
          <div className="w-[300px] shrink-0 border-r border-[var(--color-border)] overflow-y-auto p-3 space-y-2">
            {/* Add Target button */}
            <button
              onClick={() => setShowAddTarget(true)}
              className="w-full rounded-[var(--radius)] border border-dashed border-[var(--color-border)] px-3 py-2 text-athena-floor font-mono text-[var(--color-text-secondary)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] transition-colors"
            >
              + {t("addTarget")}
            </button>

            {/* Target cards */}
            {targets.length === 0 ? (
              <div className="text-center py-6">
                <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)] whitespace-pre-line">{tEmpty("plannerGuide")}</span>
              </div>
            ) : (
              targets.map((tgt) => (
                  <div
                    key={tgt.id}
                    onClick={() => setSelectedTargetId(tgt.id)}
                    className={`cursor-pointer rounded-[var(--radius)] p-3 border transition-colors ${
                      selectedTargetId === tgt.id
                        ? "border-l-[3px] border-l-[var(--color-accent)] border-[var(--color-border)] bg-[var(--color-bg-elevated)]"
                        : "border-[var(--color-border)] hover:bg-[var(--color-bg-surface)]"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                          tgt.isCompromised
                            ? "bg-[var(--color-error)]"
                            : tgt.isActive
                              ? "bg-[var(--color-success)]"
                              : "bg-[var(--color-text-tertiary)]"
                        }`}
                      />
                      <span className="text-athena-floor font-mono font-bold text-[var(--color-text-primary)] truncate">
                        {tgt.ipAddress}
                      </span>
                    </div>
                    {tgt.hostname && (
                      <span className="block text-athena-floor font-mono text-[var(--color-text-secondary)] mt-0.5 ml-[18px] truncate">
                        {tgt.hostname}
                      </span>
                    )}
                    <div className="flex items-center gap-3 mt-1 ml-[18px]">
                      <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)]">
                        {tgt.privilegeLevel ?? "N/A"}
                      </span>
                    </div>
                  </div>
              ))
            )}
          </div>

          {/* Right: Target Detail */}
          <div className="flex-1 overflow-y-auto">
            {selectedTarget ? (
              <TargetDetailPanel
                target={selectedTarget}
                facts={targetFacts}
                timelineEntries={timeline}
                onDeactivate={() => handleSetActive(selectedTarget.id, false)}
                onActivate={() => handleSetActive(selectedTarget.id, true)}
                onDelete={() => handleDeleteRequest(selectedTarget.id)}
                onOpenTerminal={selectedTarget?.isCompromised ? () => setTerminalTarget(selectedTarget) : undefined}
                terminalMode={
                  selectedTarget?.isCompromised
                    ? targetFacts.some((f) => f.trait === "credential.winrm") ? "winrm"
                    : targetFacts.some((f) => f.trait === "credential.ssh") ? "ssh"
                    : targetFacts.some((f) => f.trait === "credential.shell" && f.value?.startsWith("postgresql")) ? "psql"
                    : targetFacts.some((f) => f.trait === "credential.root_shell") ? "msf"
                    : undefined
                    : undefined
                }
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)]">
                  {t("selectTarget")}
                </span>
              </div>
            )}
          </div>

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

          {terminalTarget && (() => {
            const tMode =
              targetFacts.some((f) => f.trait === "credential.winrm") ? "winrm" as const
              : targetFacts.some((f) => f.trait === "credential.ssh") ? "ssh" as const
              : targetFacts.some((f) => f.trait === "credential.shell" && f.value?.startsWith("postgresql")) ? "psql" as const
              : targetFacts.some((f) => f.trait === "credential.root_shell") ? "msf" as const
              : undefined;
            const credUser = (() => {
              const wf = targetFacts.find((f) => f.trait === "credential.winrm");
              if (wf) return wf.value?.split(":")?.[0];
              const sf = targetFacts.find((f) => f.trait === "credential.ssh");
              if (sf) return sf.value?.split(":")?.[0];
              if (targetFacts.some((f) => f.trait === "credential.root_shell")) return "root";
              const pg = targetFacts.find((f) => f.trait === "credential.shell" && f.value?.startsWith("postgresql"));
              if (pg) return pg.value?.split(":")?.[1] ?? "postgres";
              return undefined;
            })();
            return (
              <TerminalPanel
                operationId={operationId}
                targetId={terminalTarget.id}
                targetName={terminalTarget.hostname || terminalTarget.ipAddress}
                targetIp={terminalTarget.ipAddress}
                onClose={() => setTerminalTarget(null)}
                terminalMode={tMode}
                credentialUser={credUser}
                privilegeLevel={terminalTarget.privilegeLevel ?? undefined}
              />
            );
          })()}
        </div>
      )}

      {/* ═══════════ MISSION TAB ═══════════ */}
      {activeTab === "mission" && (
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* Mission Steps Header */}
          <div className="flex items-center justify-between">
            <h2 className="font-mono text-athena-heading-card font-bold text-[var(--color-text-primary)] tracking-wide uppercase">
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
          <p className="text-athena-floor font-mono text-[var(--color-text-tertiary)] -mt-3 ml-0.5">{tHints("missionSteps")}</p>
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
                  <span className="text-athena-floor font-mono text-[var(--color-text-tertiary)] uppercase tracking-wider">{t("missionSteps")}</span>
                  <h2 className="text-athena-body font-mono font-bold text-[var(--color-text-primary)] mt-0.5">{t("createStep")}</h2>
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
                        <option value={ExecutionEngine.WINRM}>{t("engineWinrm")}</option>
                        <option value={ExecutionEngine.METASPLOIT}>{t("engineMetasploit")}</option>
                        <option value={ExecutionEngine.MOCK}>{t("engineMock")}</option>
                        <option value={ExecutionEngine.MCP}>{t("engineMcp")}</option>
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

      {/* ═══════════ BRIEF TAB ═══════════ */}
      {activeTab === "brief" && (
        <div className="flex-1 overflow-y-auto">
          <BriefTab operationId={operationId} />
        </div>
      )}

      {/* SPEC-052: Global Command Bar (bottom-fixed, cross-tab) */}
      <CommandBar
        operationId={operationId}
        isAutoMode={autoMode}
        onToggleMode={handleToggleAuto}
        onCycleTriggered={() => fetchData()}
        aiSuggestion={
          dashboard?.latestIteration?.orientSummary ?? undefined
        }
      />
    </main>
  );
}

/* ── Page wrapper ── */

export default function WarRoomPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <p className="text-athena-body font-mono text-athena-text-tertiary">
            Loading War Room...
          </p>
        </div>
      }
    >
      <WarRoomContent />
    </Suspense>
  );
}
