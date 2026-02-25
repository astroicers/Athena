"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { DataTable, Column } from "@/components/data/DataTable";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import { HostNodeCard } from "@/components/cards/HostNodeCard";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { MissionStepStatus, RiskLevel } from "@/types/enums";
import type { MissionStep } from "@/types/mission";
import type { OODATimelineEntry } from "@/types/ooda";
import type { Target } from "@/types/target";

const DEFAULT_OP_ID = "op-phantom-eye-001";

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
  const [steps, setSteps] = useState<MissionStep[]>([]);
  const [timeline, setTimeline] = useState<OODATimelineEntry[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    api.get<MissionStep[]>(`/operations/${DEFAULT_OP_ID}/mission/steps`).then(setSteps).catch(() => {});
    api.get<OODATimelineEntry[]>(`/operations/${DEFAULT_OP_ID}/ooda/timeline`).then(setTimeline).catch(() => {});
    api.get<Target[]>(`/operations/${DEFAULT_OP_ID}/targets`).then(setTargets).catch(() => {});
  }, []);

  function handleExecute() {
    setShowConfirm(false);
    api.post(`/operations/${DEFAULT_OP_ID}/mission/execute`).catch(() => {});
  }

  return (
    <div className="space-y-4">
      {/* Mission Steps + Execute */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
          Mission Steps — {operation?.codename || "PHANTOM-EYE"}
        </h2>
        <Button variant="primary" size="sm" onClick={() => setShowConfirm(true)}>
          EXECUTE MISSION
        </Button>
      </div>
      <DataTable columns={STEP_COLUMNS} data={steps as StepRow[]} keyField="id" emptyMessage="No mission steps defined" />

      {/* OODA Timeline + Host Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <OODATimeline entries={timeline} />
        </div>
        <div className="space-y-3">
          <h3 className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
            Target Hosts
          </h3>
          {targets.length === 0 ? (
            <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 text-center">
              <span className="text-xs font-mono text-athena-text-secondary">No targets</span>
            </div>
          ) : (
            targets.map((t) => (
              <HostNodeCard
                key={t.id}
                hostname={t.hostname}
                ipAddress={t.ipAddress}
                role={t.role}
                isCompromised={t.isCompromised}
                privilegeLevel={t.privilegeLevel}
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
    </div>
  );
}
