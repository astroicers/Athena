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

export default function PlannerPage() {
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

  function refreshAllData() {
    api.get<MissionStep[]>(`/operations/${DEFAULT_OP_ID}/mission/steps`).then(setSteps).catch(() => addToast("Failed to load steps", "error"));
    api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`).then(setTimeline).catch(() => addToast("Failed to load timeline", "error"));
    api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`).then(setTargets).catch(() => addToast("Failed to load targets", "error"));
  }

  function refreshTargets() {
    api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`)
      .then(setTargets)
      .catch(() => addToast("Failed to load targets", "error"));
  }

  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      api.get<MissionStep[]>(`/operations/${DEFAULT_OP_ID}/mission/steps`).then(setSteps),
      api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`).then(setTimeline),
      api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`).then(setTargets),
    ]).catch(() => addToast("Failed to load mission data", "error"))
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
        addToast((data.error as string) || "OODA cycle failed", "error");
      }),
      ws.subscribe("execution.update", () => refreshAllData()),
      ws.subscribe("operation.reset", () => refreshAllData()),
      ws.subscribe("recon.completed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        refreshTargets();
        setScanningTargetId(null);
        addToast(
          `Recon complete — ${data.facts_written ?? 0} facts written`,
          "success",
        );
      }),
      ws.subscribe("recon.failed", (raw: unknown) => {
        const data = raw as Record<string, unknown>;
        setScanningTargetId(null);
        addToast(
          (data.error as string) || "Recon scan failed",
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
      .catch(() => addToast("Failed to execute mission", "error"));
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
      addToast("Failed to reset operation", "error");
    }
  }

  const handleOodaTrigger = useCallback(async () => {
    setShowOodaConfirm(false);
    try {
      await api.post(`/operations/${DEFAULT_OP_ID}/ooda/trigger`);
      addToast("OODA cycle started", "info");
      // ooda.phase WebSocket events will trigger refreshAllData() automatically
    } catch (err) {
      const apiError = err as ApiError;
      addToast(apiError.detail || "Failed to trigger OODA cycle", "error");
    }
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
      addToast("Report exported", "success");
    } catch {
      addToast("Failed to export report", "error");
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
      addToast(apiError.detail || "Failed to start recon scan", "error");
    }
  }

  if (isLoading) return <PageLoading />;

  return (
    <div className="space-y-4">
      {/* Mission Steps + Execute */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
          Mission Steps — {operation?.codename || "PHANTOM-EYE"}
        </h2>
        <div className="flex items-center gap-2">
          {resetStatus === "done" && (
            <span className="text-[10px] font-mono text-athena-success">RESET OK</span>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowResetConfirm(true)}
            disabled={resetStatus === "resetting"}
          >
            {resetStatus === "resetting" ? "RESETTING..." : "RESET"}
          </Button>
          {oodaPhase && (
            <span className="text-[10px] font-mono text-athena-accent animate-pulse">
              {oodaPhase.toUpperCase()}...
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowOodaConfirm(true)}
          >
            OODA CYCLE
          </Button>
          <Button variant="secondary" size="sm" onClick={handleExport}>
            EXPORT
          </Button>
          <Button variant="primary" size="sm" onClick={() => setShowConfirm(true)}>
            EXECUTE MISSION
          </Button>
        </div>
      </div>
      <DataTable columns={STEP_COLUMNS} data={steps as StepRow[]} keyField="id" emptyMessage="No mission steps defined" />

      {/* OODA Timeline + Host Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <OODATimeline entries={timeline} />
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
              Target Hosts
            </h3>
            <Button variant="secondary" size="sm" onClick={() => setShowAddTarget(true)}>
              + ADD
            </Button>
          </div>
          {targets.length === 0 ? (
            <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 text-center">
              <span className="text-xs font-mono text-athena-text-secondary">No targets</span>
            </div>
          ) : (
            targets.map((t) => (
              <HostNodeCard
                key={t.id}
                id={t.id}
                hostname={t.hostname}
                ipAddress={t.ipAddress}
                role={t.role}
                isCompromised={t.isCompromised}
                privilegeLevel={t.privilegeLevel}
                isScanning={scanningTargetId === t.id}
                onScan={handleReconScan}
              />
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
    </div>
  );
}
