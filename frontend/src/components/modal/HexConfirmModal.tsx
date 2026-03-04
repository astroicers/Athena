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
import { RiskLevel } from "@/types/enums";
import { Button } from "@/components/atoms/Button";

const RISK_STYLES: Record<string, { border: string; labelKey: "lowRisk" | "mediumRisk" | "highRisk" | "critical" }> = {
  [RiskLevel.LOW]: { border: "border-athena-success", labelKey: "lowRisk" },
  [RiskLevel.MEDIUM]: { border: "border-athena-warning", labelKey: "mediumRisk" },
  [RiskLevel.HIGH]: { border: "border-athena-error", labelKey: "highRisk" },
  [RiskLevel.CRITICAL]: { border: "border-athena-critical", labelKey: "critical" },
};

interface HexConfirmModalProps {
  isOpen: boolean;
  title: string;
  riskLevel: RiskLevel;
  onConfirm: () => void;
  onCancel: () => void;
}

export function HexConfirmModal({
  isOpen,
  title,
  riskLevel,
  onConfirm,
  onCancel,
}: HexConfirmModalProps) {
  const t = useTranslations("HexConfirm");
  const tCommon = useTranslations("Common");

  if (!isOpen) return null;

  const style = RISK_STYLES[riskLevel] || RISK_STYLES[RiskLevel.MEDIUM];
  const isCritical = riskLevel === RiskLevel.CRITICAL;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-athena-bg/80 backdrop-blur-sm">
      <div
        className={`bg-athena-surface border-2 ${style.border} rounded-athena-lg p-6 max-w-md w-full mx-4`}
      >
        <div className="text-center mb-4">
          <span className="text-xs font-mono text-athena-text-secondary">
            {t(style.labelKey)}
          </span>
          <h2 className="text-lg font-mono font-bold text-athena-text mt-1">
            {title}
          </h2>
        </div>

        {isCritical && (
          <p className="text-xs text-athena-critical text-center mb-4 font-mono">
            {t("criticalWarning")}
          </p>
        )}

        <div className="flex gap-3 justify-center mt-6">
          <Button variant="secondary" onClick={onCancel}>
            {tCommon("abort")}
          </Button>
          <Button
            variant={isCritical ? "danger" : "primary"}
            onClick={onConfirm}
          >
            {isCritical ? t("confirmExecute") : tCommon("execute")}
          </Button>
        </div>
      </div>
    </div>
  );
}
