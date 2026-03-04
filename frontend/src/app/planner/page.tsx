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

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Tooltip } from "@/components/ui/Tooltip";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useToast } from "@/contexts/ToastContext";
import { PageLoading } from "@/components/ui/PageLoading";
import { DataTable, Column } from "@/components/data/DataTable";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import { HostNodeCard } from "@/components/cards/HostNodeCard";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { AddTargetModal } from "@/components/modal/AddTargetModal";
import { ReconResultModal } from "@/components/modal/ReconResultModal";
import { TerminalPanel } from "@/components/terminal/TerminalPanel";
import { MissionStepStatus, RiskLevel, OODAPhase } from "@/types/enums";
import type { MissionStep } from "@/types/mission";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Target } from "@/types/target";
import type { ReconScanResult, ReconScanQueued } from "@/types/recon";
import type { ApiError } from "@/types/api";

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

  const STEP_COLUMNS: Column<StepRow>[] = [
    { key: "stepNumber", header: "#", sortable: true },
    { key: "techniqueId", header: "Technique", render: (r) => (
      <span><span className="text-athena-accent">{r.techniqueId}</span> {r.techniqueName}</span>
    )},
    { key: "targetLabel", header: "Target" },
    { key: "engine", header: "Engine", render: (r) => String(r.engine).toUpperCase() },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (r) => (
        <Badge variant={STEP_VARIANT[r.status] || "info"}>
          {String(r.status).toUpperCase()}
        </Badge>
      ),
    },
  ];

  const { operation } = useOperation(DEFAULT_OP_ID);
  const { addToast } = useToast();
  const ws = useWebSocket(DEFAULT_OP_ID);
  const [isLoading, setIsLoading] = useState(true);
  const [steps, setSteps] = useState<MissionStep[]>([]);
  const [timeline, setTimeline] = useState<OODATimelineEntry[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [showConfirm, setShowConfirm] = useState(false);
  const [oodaPhase, setOodaPhase] = useState<string | null>(null);
  const [showOodaConfirm, setShowOodaConfirm] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetStatus, setResetStatus] = useState<"idle" | "resetting" | "done">("idle");

  // Phase 13: Recon UI state
  const [showAddTarget, setShowAddTarget] = useState(false);
  const [scanningTargetId, setScanningTargetId] = useState<string | null>(null);
  const [reconResult, setReconResult] = useState<ReconScanResult | null>(null);
  const [terminalTarget, setTerminalTarget] = useState<Target | null>(null);
  const [deletingTarget, setDeletingTarget] = useState<Target | null>(null);

  function refreshAllData() {
    api.get<MissionStep[]>(`/operations/${DEFAULT_OP_ID}/mission/steps`).then(setSteps).catch(() => addToast(tErrors("failedLoadSteps"), "error"));
    api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`).then(setTimeline).catch(() => addToast(tErrors("failedLoadTimeline"), "error"));
    api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`).then(setTargets).catch(() => addToast(tErrors("failedLoadTargets"), "error"));
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
      api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`).then(setTargets),
    ]).catch(() => addToast(tErrors("failedLoadSteps"), "error"))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // WebSocket: refresh data on OODA, execution, reset, and recon events
  useEffect(() => {
    const unsubs = [
      ws.subscribe("ooda.phase", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        setOodaPhase((data.phase as string) ?? null);
        refreshAllData();
      }),
      ws.subscribe("ooda.failed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        setOodaPhase(null);
        addToast((data.error as string) || tErrors("oodaFailed"), "error");
      }),
      ws.subscribe("execution.update", () => refreshAllData()),
      ws.subscribe("operation.reset", () => refreshAllData()),
      ws.subscribe("recon.completed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        refreshTargets();
        setScanningTargetId(null);
        addToast(
          t("reconComplete", { factsWritten: (data.facts_written as number) ?? 0 }),
          "success",
        );
      }),
      ws.subscribe("recon.failed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        setScanningTargetId(null);
        addToast(
          (data.error as string) || tErrors("failedReconScan"),
          "error",
        );
      }),
    ];
    return () => unsubs.forEach((fn) => fn());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws.subscribe]);

  function handleExecute() {
    setShowConfirm(false);
    api.post(`/operations/${DEFAULT_OP_ID}/mission/execute`)
      .catch(() => addToast(tErrors("failedExecuteMission"), "error"));
  }

  async function handleReset() {
    setShowResetConfirm(false);
    setResetStatus("resetting");
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/reset`);
      setResetStatus("done");
      setOodaPhase(null);
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
    setScanningTargetId(targetId);
    try {
      await api.post<ReconScanQueued>(
        `/operations/${DEFAULT_OP_ID}/recon/scan`,
        { target_id: targetId, enable_initial_access: true },
      );
      // 202 Accepted — background task started; WS events handle UI update
    } catch (err) {
      setScanningTargetId(null);
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
    const hostname = deletingTarget.hostname;
    setDeletingTarget(null);
    try {
      await api.delete(`/operations/${DEFAULT_OP_ID}/targets/${deletingTarget.id}`);
      addToast(t("targetDeleted", { hostname }), "success");
      refreshTargets();
    } catch (err) {
      const apiError = err as ApiError;
      addToast(apiError.detail || tErrors("failedDeleteTarget"), "error");
    }
  }

  if (isLoading) return <PageLoading />;

  return (
    <div className="space-y-4">
      {/* Mission Steps + Execute */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
          {t("missionSteps")} — {operation?.codename || "PHANTOM-EYE"}
        </h2>
        <div className="flex items-center gap-2">
          {resetStatus === "done" && (
            <span className="text-[10px] font-mono text-athena-success">{t("resetOk")}</span>
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
            <span className="text-[10px] font-mono text-athena-accent animate-pulse">
              {oodaPhase.toUpperCase()}...
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
          <Tooltip text={tTips("executeMission")}>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowConfirm(true)}
              disabled={targets.length === 0}
              icon={
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              }
            >
              {t("executeMission")}
            </Button>
          </Tooltip>
        </div>
      </div>
      <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-3 ml-1">{tHints("missionSteps")}</p>
      <DataTable columns={STEP_COLUMNS} data={steps as StepRow[]} keyField="id" emptyMessage={t("noSteps")} />

      {/* OODA Timeline + Host Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <OODATimeline entries={timeline} />
          <p className="text-[10px] font-mono text-athena-text-secondary/60 mt-1 ml-1">{tHints("oodaTimeline")}</p>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
              {t("targetHosts")}
            </h3>
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
          </div>
          <p className="text-[10px] font-mono text-athena-text-secondary/60 -mt-2 ml-1">{tHints("targetHosts")}</p>
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
                  isScanning={scanningTargetId === tgt.id}
                  onScan={handleReconScan}
                  onSetActive={handleSetActive}
                  onDelete={handleDeleteRequest}
                />
                {tgt.isCompromised && (
                  <button
                    onClick={() => setTerminalTarget(tgt)}
                    className="mt-1 w-full text-[10px] font-mono text-athena-success border border-athena-success/40 rounded-athena-sm py-1 hover:bg-athena-success/10 transition-colors uppercase tracking-wider"
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
        isOpen={showConfirm}
        title="Execute Mission Plan"
        riskLevel={RiskLevel.HIGH}
        onConfirm={handleExecute}
        onCancel={() => setShowConfirm(false)}
      />

      <HexConfirmModal
        isOpen={showOodaConfirm}
        title="Trigger OODA Cycle"
        riskLevel={RiskLevel.MEDIUM}
        onConfirm={handleOodaTrigger}
        onCancel={() => setShowOodaConfirm(false)}
      />

      <HexConfirmModal
        isOpen={showResetConfirm}
        title="Reset Operation"
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
  );
}
