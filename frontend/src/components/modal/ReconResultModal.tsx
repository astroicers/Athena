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
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-black/50"
        onClick={onClose}
      />

      {/* Right slide panel */}
      <div className="fixed right-0 top-0 h-full w-[420px] bg-[var(--color-bg-surface)] border-l border-[var(--color-border)] z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)] shrink-0">
          <div>
            <span className="text-xs font-mono text-[var(--color-text-tertiary)]">{t("scanComplete")}</span>
            <h2 className="text-sm font-mono font-bold text-[var(--color-text-primary)]">{t("title")}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] text-sm font-mono px-1"
          >
            ✕
          </button>
        </div>

        {/* Content (scrollable) */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono">
          {/* Summary */}
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-[var(--color-text-tertiary)]">{t("ip")}</span>
              <span className="text-[var(--color-text-primary)]">{result.ipAddress}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-tertiary)]">{t("os")}</span>
              <span className="text-[var(--color-text-primary)]">{result.osGuess ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-tertiary)]">{t("services")}</span>
              <span className="text-[var(--color-accent)]">{t("servicesFound", { count: result.servicesFound })}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-tertiary)]">{t("factsWritten")}</span>
              <span className="text-[var(--color-text-primary)]">{result.factsWritten}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-tertiary)]">{t("duration")}</span>
              <span className="text-[var(--color-text-primary)]">{result.scanDurationSec.toFixed(1)}s</span>
            </div>
          </div>

          {/* Open Ports */}
          {result.services && result.services.length > 0 && (
            <div className="border-t border-[var(--color-border)] pt-3">
              <p className="text-sm font-bold text-[var(--color-text-primary)] mb-2">
                {t("openPorts")}
              </p>
              <div className="border border-[var(--color-border)] rounded-[var(--radius)] overflow-hidden">
                {/* Table header */}
                <div className="flex text-xs bg-[var(--color-bg-surface)] border-b border-[var(--color-border)] px-2 py-1">
                  <span className="w-20 text-[var(--color-text-tertiary)]">Port</span>
                  <span className="w-24 text-[var(--color-text-tertiary)]">Service</span>
                  <span className="flex-1 text-[var(--color-text-tertiary)]">Version</span>
                </div>
                {/* Table rows */}
                <div className="max-h-48 overflow-y-auto">
                  {result.services.map((svc) => (
                    <div
                      key={`${svc.port}-${svc.protocol}`}
                      className="flex text-xs px-2 py-1 border-b border-[var(--color-border)] last:border-b-0"
                    >
                      <span className="w-20 text-[var(--color-accent)]">{svc.port}/{svc.protocol}</span>
                      <span className="w-24 text-[var(--color-text-primary)]">{svc.service}</span>
                      <span className="flex-1 text-[var(--color-text-tertiary)] truncate">{svc.version || "\u2014"}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Initial Access */}
          <div className="border-t border-[var(--color-border)] pt-3">
            <p className="text-sm font-bold text-[var(--color-text-primary)] mb-2">
              {t("initialAccess")}
            </p>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--color-text-tertiary)]">{t("status")}</span>
                <span className={ia.success ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}>
                  {ia.success ? t("success") : t("failed")}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-text-tertiary)]">{t("method")}</span>
                <span className="text-[var(--color-text-primary)]">{ia.method}</span>
              </div>
              {ia.credential && (
                <div className="flex justify-between">
                  <span className="text-[var(--color-text-tertiary)]">{t("credential")}</span>
                  <span className="text-[var(--color-accent)] font-bold">{ia.credential}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-[var(--color-text-tertiary)]">{t("agent")}</span>
                <span className={ia.agentDeployed ? "text-[var(--color-success)]" : "text-[var(--color-text-tertiary)]"}>
                  {ia.agentDeployed ? t("deployed") : t("notDeployed")}
                </span>
              </div>
              {ia.error && (
                <div className="flex justify-between">
                  <span className="text-[var(--color-text-tertiary)]">{t("error")}</span>
                  <span className="text-[var(--color-error)] text-right max-w-[60%]">{ia.error}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-4 py-3 border-t border-[var(--color-border)] shrink-0">
          {ia.agentDeployed && !triggered && (
            <Button variant="secondary" onClick={handleTriggerOoda} disabled={triggering}>
              {triggering ? t("triggering") : t("triggerOoda")}
            </Button>
          )}
          <Button variant="secondary" onClick={onClose}>
            {tCommon("close")}
          </Button>
        </div>
      </div>
    </>
  );
}
