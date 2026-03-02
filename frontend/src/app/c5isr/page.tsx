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

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useOperation } from "@/hooks/useOperation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useToast } from "@/contexts/ToastContext";
import { PageLoading } from "@/components/ui/PageLoading";
import { MetricCard } from "@/components/cards/MetricCard";
import { RecommendCard } from "@/components/cards/RecommendCard";
import { C5ISRStatusBoard } from "@/components/c5isr/C5ISRStatusBoard";
import { OODAIndicator } from "@/components/ooda/OODAIndicator";
import { DataTable, Column } from "@/components/data/DataTable";
import type { C5ISRStatus } from "@/types/c5isr";
import type { OrientRecommendation } from "@/types/recommendation";
import type { TechniqueWithStatus } from "@/types/technique";
import type { Operation } from "@/types/operation";
import { Badge } from "@/components/atoms/Badge";
import { TechniqueStatus } from "@/types/enums";

const DEFAULT_OP_ID = "op-0001";

type TechRow = TechniqueWithStatus & Record<string, unknown>;

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  [TechniqueStatus.SUCCESS]: "success",
  [TechniqueStatus.RUNNING]: "info",
  [TechniqueStatus.FAILED]: "error",
  [TechniqueStatus.PARTIAL]: "warning",
  [TechniqueStatus.QUEUED]: "info",
};

const EXEC_COLUMNS: Column<TechRow>[] = [
  { key: "mitreId", header: "MITRE ID", sortable: true },
  { key: "name", header: "Technique" },
  { key: "tactic", header: "Tactic" },
  { key: "riskLevel", header: "Risk", render: (r) => String(r.riskLevel ?? "—").toUpperCase() },
  {
    key: "latestStatus",
    header: "Status",
    sortable: true,
    render: (r) => {
      const status = r.latestStatus;
      if (!status) return <span className="text-athena-text-secondary">—</span>;
      return (
        <Badge variant={STATUS_VARIANT[status] || "info"}>
          {status.toUpperCase()}
        </Badge>
      );
    },
  },
];

export default function C5ISRPage() {
  const { operation } = useOperation(DEFAULT_OP_ID);
  const { addToast } = useToast();
  const ws = useWebSocket(DEFAULT_OP_ID);
  const [isLoading, setIsLoading] = useState(true);
  const [domains, setDomains] = useState<C5ISRStatus[]>([]);
  const [recommendation, setRecommendation] = useState<OrientRecommendation | null>(null);
  const [execRows, setExecRows] = useState<TechniqueWithStatus[]>([]);

  useEffect(() => {
    Promise.all([
      api.get<C5ISRStatus[]>(`/operations/${DEFAULT_OP_ID}/c5isr`).then(setDomains),
      api.get<OrientRecommendation>(`/operations/${DEFAULT_OP_ID}/recommendations/latest`).then(setRecommendation),
      api.get<TechniqueWithStatus[]>(`/operations/${DEFAULT_OP_ID}/techniques`).then(setExecRows),
    ]).catch(() => addToast("Failed to load C5ISR data", "error"))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // WebSocket: live C5ISR domain updates
  useEffect(() => {
    return ws.subscribe("c5isr.update", (data: any) => {
      if (data?.domains) setDomains(data.domains);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws.subscribe]);

  if (isLoading) return <PageLoading />;

  const op: Operation | null = operation;

  return (
    <div className="space-y-4">
      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard
          title="Active Agents"
          value={op?.activeAgents ?? "—"}
          accentColor="var(--color-accent)"
        />
        <MetricCard
          title="Success Rate"
          value={op ? `${op.successRate}%` : "—"}
          accentColor="var(--color-success)"
        />
        <MetricCard
          title="Techniques Executed"
          value={op?.techniquesExecuted ?? "—"}
          subtitle={op ? `of ${op.techniquesTotal} total` : undefined}
        />
        <MetricCard
          title="Threat Level"
          value={op?.threatLevel?.toFixed(1) ?? "—"}
          accentColor="var(--color-error)"
        />
      </div>

      {/* OODA + C5ISR */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 space-y-4">
          <OODAIndicator currentPhase={op?.currentOodaPhase ?? null} />
          <C5ISRStatusBoard domains={domains} />
        </div>
        <div className="space-y-4">
          <RecommendCard recommendation={recommendation} />
        </div>
      </div>

      {/* Execution Table */}
      <div>
        <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
          Active Operations
        </h2>
        <DataTable columns={EXEC_COLUMNS} data={execRows as TechRow[]} keyField="id" emptyMessage="No technique executions" />
      </div>
    </div>
  );
}
