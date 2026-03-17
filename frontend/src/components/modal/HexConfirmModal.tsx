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

import { useTranslations } from "next-intl";
import { RiskLevel } from "@/types/enums";
import { Button } from "@/components/atoms/Button";

const RISK_STYLES: Record<string, { border: string; labelKey: "lowRisk" | "mediumRisk" | "highRisk" | "critical" }> = {
  [RiskLevel.LOW]: { border: "border-[#22C55E]", labelKey: "lowRisk" },
  [RiskLevel.MEDIUM]: { border: "border-[#FBBF24]", labelKey: "mediumRisk" },
  [RiskLevel.HIGH]: { border: "border-[#EF4444]", labelKey: "highRisk" },
  [RiskLevel.CRITICAL]: { border: "border-[#DC2626]", labelKey: "critical" },
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0A0E17]/80 backdrop-blur-sm">
      <div
        className={`bg-[#111827] border-2 ${style.border} rounded-athena-lg p-6 max-w-md w-full mx-4`}
      >
        <div className="text-center mb-4">
          <span className="text-xs font-mono text-[#9ca3af]">
            {t(style.labelKey)}
          </span>
          <h2 className="text-lg font-mono font-bold text-[#e5e7eb] mt-1">
            {title}
          </h2>
        </div>

        {isCritical && (
          <p className="text-xs text-[#DC2626] text-center mb-4 font-mono">
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
