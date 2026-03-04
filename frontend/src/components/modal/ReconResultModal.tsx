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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Button } from "@/components/atoms/Button";
import type { ReconScanResult } from "@/types/recon";

interface ReconResultModalProps {
  isOpen: boolean;
  operationId: string;
  result: ReconScanResult | null;
  onClose: () => void;
}

export function ReconResultModal({
  isOpen,
  operationId,
  result,
  onClose,
}: ReconResultModalProps) {
  const t = useTranslations("ReconResult");
  const tCommon = useTranslations("Common");
  const [triggering, setTriggering] = useState(false);
  const [triggered, setTriggered] = useState(false);

  if (!isOpen || !result) return null;

  async function handleTriggerOoda() {
    setTriggering(true);
    try {
      await api.post(`/operations/${operationId}/ooda/trigger`);
      setTriggered(true);
    } finally {
      setTriggering(false);
      onClose();
    }
  }

  const ia = result.initialAccess;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-athena-bg/80 backdrop-blur-sm">
      <div className="bg-athena-surface border-2 border-athena-border rounded-athena-lg p-6 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div className="mb-4 border-b border-athena-border pb-3">
          <span className="text-xs font-mono text-athena-text-secondary">{t("scanComplete")}</span>
          <h2 className="text-lg font-mono font-bold text-athena-text mt-1">{t("title")}</h2>
        </div>

        {/* Summary */}
        <div className="space-y-1 text-xs font-mono mb-4">
          <div className="flex justify-between">
            <span className="text-athena-text-secondary">{t("ip")}</span>
            <span className="text-athena-text">{result.ipAddress}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-athena-text-secondary">{t("os")}</span>
            <span className="text-athena-text">{result.osGuess ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-athena-text-secondary">{t("services")}</span>
            <span className="text-athena-accent">{t("servicesFound", { count: result.servicesFound })}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-athena-text-secondary">{t("factsWritten")}</span>
            <span className="text-athena-text">{result.factsWritten}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-athena-text-secondary">{t("duration")}</span>
            <span className="text-athena-text">{result.scanDurationSec.toFixed(1)}s</span>
          </div>
        </div>

        {/* Initial Access */}
        <div className="border-t border-athena-border pt-3 mb-4">
          <p className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-2">
            {t("initialAccess")}
          </p>
          <div className="space-y-1 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-athena-text-secondary">{t("status")}</span>
              <span className={ia.success ? "text-athena-success" : "text-athena-error"}>
                {ia.success ? t("success") : t("failed")}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-athena-text-secondary">{t("method")}</span>
              <span className="text-athena-text">{ia.method}</span>
            </div>
            {ia.credential && (
              <div className="flex justify-between">
                <span className="text-athena-text-secondary">{t("credential")}</span>
                <span className="text-athena-accent font-bold">{ia.credential}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-athena-text-secondary">{t("agent")}</span>
              <span className={ia.agentDeployed ? "text-athena-success" : "text-athena-text-secondary"}>
                {ia.agentDeployed ? t("deployed") : t("notDeployed")}
              </span>
            </div>
            {ia.error && (
              <div className="flex justify-between">
                <span className="text-athena-text-secondary">{t("error")}</span>
                <span className="text-athena-error text-right max-w-[60%]">{ia.error}</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex gap-3 justify-end pt-2 border-t border-athena-border">
          {ia.agentDeployed && !triggered && (
            <Button variant="primary" onClick={handleTriggerOoda} disabled={triggering}>
              {triggering ? t("triggering") : t("triggerOoda")}
            </Button>
          )}
          <Button variant="secondary" onClick={onClose}>
            {tCommon("close")}
          </Button>
        </div>
      </div>
    </div>
  );
}
