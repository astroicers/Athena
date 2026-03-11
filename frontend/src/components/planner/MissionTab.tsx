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

import { useTranslations } from "next-intl";
import { Tooltip } from "@/components/ui/Tooltip";
import { DataTable, Column } from "@/components/data/DataTable";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import { HostNodeCard } from "@/components/cards/HostNodeCard";
import { EngagementPanel } from "@/components/planner/EngagementPanel";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { AddTargetModal } from "@/components/modal/AddTargetModal";
import { ReconResultModal } from "@/components/modal/ReconResultModal";
import { TerminalPanel } from "@/components/terminal/TerminalPanel";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { MissionStepStatus, RiskLevel } from "@/types/enums";
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
  onSetActive: (targetId: string, active: boolean) => void;
  onDeleteRequest: (targetId: string) => void;
  onConfirmDelete: () => void;
  onAddTargetSuccess: () => void;
  onOsintDiscover?: (targetId: string) => void;
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
  onSetActive,
  onDeleteRequest,
  onConfirmDelete,
  onAddTargetSuccess,
  onOsintDiscover,
}: MissionTabProps) {
  const t = useTranslations("Planner");
  const tCommon = useTranslations("Common");
  const tHints = useTranslations("Hints");
  const tTips = useTranslations("Tooltips");
  const tEmpty = useTranslations("EmptyStates");
  const tOoda = useTranslations("OODA");
  const tStatus = useTranslations("Status");

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

  return (
    <div className="flex-1 space-y-4 min-h-0 overflow-y-auto">
      {/* Mission Steps + Execute */}
      <div className="flex items-center justify-between">
        <SectionHeader>
          {t("missionSteps")} — {codename || "PHANTOM-EYE"}
        </SectionHeader>
        <div className="flex items-center gap-2">
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
            <span className="text-xs font-mono font-bold text-athena-accent bg-athena-accent/20 border border-athena-accent rounded-athena-sm px-3 py-1 animate-pulse">
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
                  onScan={onReconScan}
                  onSetActive={onSetActive}
                  onDelete={onDeleteRequest}
                  onViewScanResult={targetScans[tgt.id] ? () => onSetReconResult(targetScans[tgt.id]) : undefined}
                />
                <div className="flex gap-1 mt-1">
                  {onOsintDiscover && (
                    <button
                      onClick={() => onOsintDiscover(tgt.id)}
                      className="flex-1 text-sm font-mono text-athena-accent border border-athena-accent/40 rounded-athena-sm py-1 hover:bg-athena-accent/10 transition-colors uppercase tracking-wider"
                    >
                      {t("osintDiscover")}
                    </button>
                  )}
                  {tgt.isCompromised && (
                    <button
                      onClick={() => onSetTerminalTarget(tgt)}
                      className="flex-1 text-sm font-mono text-athena-success border border-athena-success/40 rounded-athena-sm py-1 hover:bg-athena-success/10 transition-colors uppercase tracking-wider"
                    >
                      {t("terminal")}
                    </button>
                  )}
                </div>
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
    </div>
  );
}
