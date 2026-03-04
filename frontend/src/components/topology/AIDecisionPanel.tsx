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

import { useTranslations } from "next-intl";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { KillChainStage } from "@/types/enums";
import { KILL_CHAIN_COLORS } from "./NetworkTopology";

interface AIDecisionPanelProps {
  activeTechniqueId: string | null;
  activeEngine: string | null;
  activeStatus: string | null;
  activeTechniqueName: string | null;
  activeKillChainStage: KillChainStage | null;
  activeConfidence: number | null;
  llmThinking?: boolean;
  llmBackend?: string | null;
  llmLatencyMs?: number | null;
}

export function AIDecisionPanel({
  activeTechniqueId,
  activeEngine,
  activeStatus,
  activeTechniqueName,
  activeKillChainStage,
  activeConfidence,
  llmThinking,
  llmBackend,
  llmLatencyMs,
}: AIDecisionPanelProps) {
  const t = useTranslations("AIDecision");
  const tHints = useTranslations("Hints");

  const isRunning = activeStatus === "running";
  const stageColor = activeKillChainStage ? KILL_CHAIN_COLORS[activeKillChainStage] : null;

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3">
      {/* Header with left accent bar when active */}
      <div className="flex items-center gap-2 mb-1">
        {stageColor && (
          <div
            className={`w-0.5 h-4 rounded-full ${isRunning ? "animate-pulse" : ""}`}
            style={{ backgroundColor: stageColor }}
          />
        )}
        <SectionHeader level="card">
          {t("title")}
        </SectionHeader>
      </div>
      <p className="text-[10px] font-mono text-athena-text-secondary/60 mb-2">{tHints("aiDecision")}</p>

      {/* Empty state */}
      {!activeTechniqueId ? (
        <div className="py-2 text-center">
          <span className="text-[10px] font-mono text-athena-text-secondary/50">
            {t("noActiveTechnique")}
          </span>
        </div>
      ) : (
        <div className="space-y-1.5">
          {/* Technique ID + Kill Chain stage */}
          <div className="flex items-center gap-2">
            <span
              className={`text-sm font-mono font-bold ${isRunning ? "animate-pulse" : ""}`}
              style={{ color: stageColor ?? "var(--color-accent)" }}
            >
              {activeTechniqueId}
            </span>
            {activeKillChainStage && (
              <span
                className="text-[10px] font-mono px-1 py-0.5 rounded border"
                style={{
                  color: stageColor ?? undefined,
                  borderColor: stageColor ?? undefined,
                }}
              >
                {activeKillChainStage.toUpperCase()}
              </span>
            )}
          </div>

          {/* Technique name */}
          {activeTechniqueName && (
            <div className="text-[10px] font-mono text-athena-text-secondary truncate">
              {activeTechniqueName}
            </div>
          )}

          {/* Engine + Status + Confidence row */}
          <div className="flex items-center justify-between gap-2 mt-1">
            <div className="flex items-center gap-2">
              {activeEngine && (
                <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
                  {activeEngine.toUpperCase()}
                </span>
              )}
              {activeStatus && (
                <span
                  className={`text-[10px] font-mono uppercase ${
                    activeStatus === "running"
                      ? "text-athena-warning animate-pulse"
                      : activeStatus === "success"
                      ? "text-athena-success"
                      : activeStatus === "failed"
                      ? "text-athena-error"
                      : "text-athena-text-secondary"
                  }`}
                >
                  {activeStatus === "running" ? t("running") : activeStatus.toUpperCase()}
                </span>
              )}
            </div>
            {activeConfidence !== null && (
              <span className="text-[10px] font-mono font-bold text-athena-accent">
                {Math.round(activeConfidence * 100)}%
              </span>
            )}
          </div>

          {/* LLM Status row — visible during orient phase */}
          {(llmThinking || llmLatencyMs != null) && (
            <div className="flex items-center justify-between mt-1 pt-1 border-t border-athena-border/50">
              <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
                {t("llm")}
              </span>
              <div className="flex items-center gap-2">
                {llmThinking ? (
                  <span className="text-[10px] font-mono text-athena-warning animate-pulse">
                    {t("analyzing")}
                  </span>
                ) : llmLatencyMs != null ? (
                  <span className="text-[10px] font-mono text-athena-success">
                    {llmLatencyMs}ms
                  </span>
                ) : null}
                {llmBackend && (
                  <span className="text-[10px] font-mono text-athena-text-secondary/60 uppercase">
                    {llmBackend === "api_key" ? "API" : llmBackend === "oauth" ? "OAUTH" : llmBackend}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
