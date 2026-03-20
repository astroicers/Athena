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
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import { Tooltip } from "@/components/ui/Tooltip";
import { DataTable, Column } from "@/components/data/DataTable";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import { HostNodeCard } from "@/components/cards/HostNodeCard";
import { EngagementPanel } from "@/components/planner/EngagementPanel";
import { ObjectivesPanel } from "@/components/planner/ObjectivesPanel";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { AddTargetModal } from "@/components/modal/AddTargetModal";
import { ReconResultModal } from "@/components/modal/ReconResultModal";
import { TerminalPanel } from "@/components/terminal/TerminalPanel";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { TargetSummaryPanel } from "@/components/planner/TargetSummaryPanel";
import { ExecutionEngine, MissionStepStatus, RiskLevel } from "@/types/enums";
import type { MissionStep } from "@/types/mission";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Target } from "@/types/target";
import type { ReconScanResult } from "@/types/recon";

const STEP_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [MissionStepStatus.COMPLETED]: "success",
  [MissionStepStatus.RUNNING]: "info",
  [MissionStepStatus.FAILED]: "error",
  [MissionStepStatus.QUEUED]: "warning",
  [MissionStepStatus.SKIPPED]: "info",
};

type StepRow = MissionStep & Record<string, unknown>;

export interface MissionTabProps {
  operationId: string;
  codename: string | undefined;
  steps: MissionStep[];
  timeline: OODATimelineEntry[];
  targets: Target[];
  oodaPhase: string | null;
  resetStatus: "idle" | "resetting" | "done";
  scanState: { targetId: string; phase: string | null; step: number; totalSteps: number } | null;
  targetScans: Record<string, ReconScanResult>;
  reconResult: ReconScanResult | null;
  terminalTarget: Target | null;
  deletingTarget: Target | null;
  showOodaConfirm: boolean;
  showResetConfirm: boolean;
  showAddTarget: boolean;
  onSetShowOodaConfirm: (v: boolean) => void;
  onSetShowResetConfirm: (v: boolean) => void;
  onSetShowAddTarget: (v: boolean) => void;
  onSetReconResult: (v: ReconScanResult | null) => void;
  onSetTerminalTarget: (v: Target | null) => void;
  onSetDeletingTarget: (v: Target | null) => void;
  onOodaTrigger: () => void;
  onReset: () => void;
  onExport: () => void;
  onReconScan: (targetId: string) => void;
  onInitialAccess?: (targetId: string) => void;
  onSetActive: (targetId: string, active: boolean) => void;
  onDeleteRequest: (targetId: string) => void;
  onConfirmDelete: () => void;
  onAddTargetSuccess: () => void;
  onOsintDiscover?: (targetId: string) => void;
  onRefreshSteps?: () => void;
}

export function MissionTab({
  operationId,
  codename,
  steps,
  timeline,
  targets,
  oodaPhase,
  resetStatus,
  scanState,
  targetScans,
  reconResult,
  terminalTarget,
  deletingTarget,
  showOodaConfirm,
  showResetConfirm,
  showAddTarget,
  onSetShowOodaConfirm,
  onSetShowResetConfirm,
  onSetShowAddTarget,
  onSetReconResult,
  onSetTerminalTarget,
  onSetDeletingTarget,
  onOodaTrigger,
  onReset,
  onExport,
  onReconScan,
  onInitialAccess,
  onSetActive,
  onDeleteRequest,
  onConfirmDelete,
  onAddTargetSuccess,
  onOsintDiscover,
  onRefreshSteps,
}: MissionTabProps) {
  const t = useTranslations("Planner");
  const tCommon = useTranslations("Common");
  const tHints = useTranslations("Hints");
  const tTips = useTranslations("Tooltips");
  const tEmpty = useTranslations("EmptyStates");
  const tOoda = useTranslations("OODA");
  const tStatus = useTranslations("Status");

  const { addToast } = useToast();

  // AI Summary panel state — tracks which target is being summarised
  const [summaryTargetId, setSummaryTargetId] = useState<string | null>(null);

  // Create Step modal state
  const [showCreateStep, setShowCreateStep] = useState(false);
  const [newStep, setNewStep] = useState({
    stepNumber: steps.length > 0 ? Math.max(...steps.map((s) => s.stepNumber)) + 1 : 1,
    techniqueId: "",
    techniqueName: "",
    targetId: "",
    engine: ExecutionEngine.SSH as string,
  });
  const [creatingStep, setCreatingStep] = useState(false);

  // Inline status edit state
  const [editingStepId, setEditingStepId] = useState<string | null>(null);

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
      setNewStep({ stepNumber: (steps.length > 0 ? Math.max(...steps.map((s) => s.stepNumber)) + 1 : 1) + 1, techniqueId: "", techniqueName: "", targetId: "", engine: ExecutionEngine.SSH });
      onRefreshSteps?.();
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
      onRefreshSteps?.();
    } catch {
      addToast(t("failedUpdateStep"), "error");
    }
  }

  const inputStyles =
    "w-full bg-athena-bg border border-athena-border rounded-athena px-3 py-2 text-sm font-mono text-athena-text-light placeholder-athena-text-secondary focus:outline-none focus:border-athena-accent";

  const labelStyles =
    "block text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-1";

  const STEP_COLUMNS: Column<StepRow>[] = [
    { key: "stepNumber", header: t("colStep"), sortable: true, width: 60 },
    { key: "techniqueId", header: t("colTechnique"), width: 280, render: (r) => (
      <span><span className="text-athena-accent font-semibold">{r.techniqueId}</span> <span className="text-athena-text-tertiary">{r.techniqueName}</span></span>
    )},
    { key: "targetLabel", header: t("colTarget") },
    { key: "engine", header: t("colEngine"), render: (r) => String(r.engine).toUpperCase() },
    {
      key: "status",
      header: t("colStatus"),
      sortable: true,
      width: 100,
      render: (r) => (
        editingStepId === r.id ? (
          <select
            value={r.status}
            onChange={(e) => handleStepStatusChange(r.id, e.target.value)}
            onBlur={() => setTimeout(() => setEditingStepId(null), 150)}
            autoFocus
            className="bg-athena-bg border border-athena-accent rounded-athena px-2 py-1 text-xs font-mono text-athena-text-light focus:outline-none focus:ring-2 focus:ring-athena-accent"
          >
            {Object.values(MissionStepStatus).map((s) => (
              <option key={s} value={s}>{tStatus(s as any)}</option>
            ))}
          </select>
        ) : (
          <button onClick={() => setEditingStepId(r.id)} className="cursor-pointer">
            <Badge variant={STEP_VARIANT[r.status] || "info"}>
              {tStatus(String(r.status) as any)}
            </Badge>
          </button>
        )
      ),
    },
  ];

  return (
    <div className="flex-1 space-y-4 min-h-0 overflow-y-auto pt-6 pb-4 px-6">
      {/* Mission Steps + Execute */}
      <div className="flex items-center justify-between">
        <SectionHeader>
          {t("missionSteps")} — {codename || "PHANTOM-EYE"}
        </SectionHeader>
        <div className="flex items-center gap-2">
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
          {resetStatus === "done" && (
            <span className="text-sm font-mono text-athena-success">{t("resetOk")}</span>
          )}
          <Tooltip text={tTips("reset")}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onSetShowResetConfirm(true)}
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
            <span className="text-xs font-mono font-bold text-athena-accent bg-athena-accent-bg border border-athena-accent/25 rounded-athena px-3 py-1 animate-pulse">
              {tOoda(oodaPhase as "observe" | "orient" | "decide" | "act")}...
            </span>
          )}
          <Tooltip text={tTips("oodaCycle")}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onSetShowOodaConfirm(true)}
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
              onClick={onExport}
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
      <p className="text-xs font-mono text-athena-text-tertiary -mt-3 ml-1">{tHints("missionSteps")}</p>
      <DataTable columns={STEP_COLUMNS} data={steps as StepRow[]} keyField="id" emptyMessage={t("noSteps")} />

      {/* Objectives */}
      <ObjectivesPanel operationId={operationId} />

      {/* OODA Timeline + Host Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <OODATimeline entries={timeline} />
          <p className="text-xs font-mono text-athena-text-tertiary mt-1 ml-1">{tHints("oodaTimeline")}</p>
        </div>
        <div className="space-y-3">
          <SectionHeader
            level="card"
            trailing={
              <Tooltip text={tTips("addTarget")}>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onSetShowAddTarget(true)}
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
          <p className="text-xs font-mono text-athena-text-secondary -mt-2 ml-1">{tHints("targetHosts")}</p>
          {targets.length === 0 ? (
            <div className="bg-athena-surface border border-white/5 rounded-athena p-6 text-center">
              <span className="text-xs font-mono text-athena-text-tertiary whitespace-pre-line">{tEmpty("plannerGuide")}</span>
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
                  onScan={onReconScan}
                  onSetActive={onSetActive}
                  onDelete={onDeleteRequest}
                  onViewScanResult={targetScans[tgt.id] ? () => onSetReconResult(targetScans[tgt.id]) : undefined}
                />
                <div className="flex gap-1 mt-1">
                  {onOsintDiscover && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onOsintDiscover(tgt.id)}
                      className="flex-1 text-xs text-athena-accent border-athena-accent/25 bg-transparent hover:bg-athena-accent/10 uppercase tracking-wider"
                    >
                      {t("osintDiscover")}
                    </Button>
                  )}
                  {onInitialAccess && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onInitialAccess(tgt.id)}
                      disabled={scanState?.targetId === tgt.id}
                      className="flex-1 text-xs text-athena-warning border-athena-warning/25 bg-transparent hover:bg-athena-warning-bg uppercase tracking-wider"
                    >
                      {t("initialAccess")}
                    </Button>
                  )}
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      setSummaryTargetId((prev) =>
                        prev === tgt.id ? null : tgt.id,
                      )
                    }
                    className="flex-1 text-xs text-athena-text-tertiary hover:text-athena-text-light uppercase tracking-wider"
                  >
                    {t("aiSummary")}
                  </Button>
                  {tgt.isCompromised && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onSetTerminalTarget(tgt)}
                      className="flex-1 text-xs text-athena-success border-athena-success/25 bg-transparent hover:bg-athena-success/10 uppercase tracking-wider"
                    >
                      {t("terminal")}
                    </Button>
                  )}
                </div>
                {summaryTargetId === tgt.id && (
                  <div className="mt-2">
                    <TargetSummaryPanel
                      operationId={operationId}
                      targetId={tgt.id}
                      hostname={tgt.hostname}
                      onClose={() => setSummaryTargetId(null)}
                    />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Engagement / ROE */}
      <EngagementPanel operationId={operationId} />

      <HexConfirmModal
        isOpen={showOodaConfirm}
        title={t("confirmOoda")}
        riskLevel={RiskLevel.MEDIUM}
        onConfirm={onOodaTrigger}
        onCancel={() => onSetShowOodaConfirm(false)}
      />

      <HexConfirmModal
        isOpen={showResetConfirm}
        title={t("confirmReset")}
        riskLevel={RiskLevel.HIGH}
        onConfirm={onReset}
        onCancel={() => onSetShowResetConfirm(false)}
      />

      <HexConfirmModal
        isOpen={deletingTarget !== null}
        title={t("deleteTarget", { hostname: deletingTarget?.hostname ?? "" })}
        riskLevel={RiskLevel.HIGH}
        onConfirm={onConfirmDelete}
        onCancel={() => onSetDeletingTarget(null)}
      />

      <AddTargetModal
        isOpen={showAddTarget}
        operationId={operationId}
        onSuccess={onAddTargetSuccess}
        onCancel={() => onSetShowAddTarget(false)}
      />

      <ReconResultModal
        isOpen={reconResult !== null}
        operationId={operationId}
        result={reconResult}
        onClose={() => onSetReconResult(null)}
      />

      {terminalTarget && (
        <TerminalPanel
          operationId={operationId}
          targetId={terminalTarget.id}
          targetName={terminalTarget.hostname || terminalTarget.ipAddress}
          targetIp={terminalTarget.ipAddress}
          onClose={() => onSetTerminalTarget(null)}
        />
      )}

      {/* Create Step Modal */}
      {showCreateStep && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-athena-surface border border-athena-border rounded-athena p-6 max-w-md w-full mx-4">
            <div className="mb-4">
              <span className="text-xs font-mono text-athena-text-secondary">{t("missionSteps")}</span>
              <h2 className="text-base font-mono font-bold text-athena-text-light mt-1">{t("createStep")}</h2>
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
                  {t("techniqueId")} <span className="text-athena-error">*</span>
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
                  {t("techniqueName")} <span className="text-athena-error">*</span>
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
                  {t("targetId")} <span className="text-athena-error">*</span>
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
  );
}
