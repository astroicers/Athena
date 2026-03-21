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
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { ProgressBar } from "@/components/atoms/ProgressBar";
import { Tooltip } from "@/components/ui/Tooltip";

interface HostNodeCardProps {
  id?: string;
  hostname: string;
  ipAddress: string;
  role: string;
  isCompromised: boolean;
  privilegeLevel: string | null;
  isScanning?: boolean;
  isActive?: boolean;
  scanPhase?: string | null;
  scanStep?: number;
  scanTotalSteps?: number;
  os?: string | null;
  openPorts?: number;
  services?: Array<{ port: number; service: string }>;
  credentialFound?: string | null;
  lastScanAt?: string | null;
  onScan?: (targetId: string) => void;
  onSetActive?: (targetId: string, active: boolean) => void;
  onDelete?: (targetId: string) => void;
  onViewScanResult?: () => void;
}

function ShieldIcon({ isCompromised, isScanning }: { isCompromised: boolean; isScanning: boolean }) {
  const bgColor = isScanning
    ? "bg-[var(--color-accent)]/10"
    : isCompromised
      ? "bg-[var(--color-error)]/10"
      : "bg-[var(--color-success)]/10";

  return (
    <div className={`shrink-0 w-8 h-8 rounded-[var(--radius)] flex items-center justify-center ${bgColor}`}>
      {isScanning ? (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="animate-spin" style={{ animationDuration: "3s" }}>
          <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" strokeDasharray="22 22" className="text-[var(--color-accent)]" />
          <circle cx="10" cy="10" r="2" fill="currentColor" className="text-[var(--color-accent)]" />
        </svg>
      ) : isCompromised ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--color-error)]">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 9l6 6M15 9l-6 6" />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--color-success)]">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      )}
    </div>
  );
}

export function HostNodeCard({
  id,
  hostname,
  ipAddress,
  role,
  isCompromised,
  privilegeLevel,
  isScanning = false,
  isActive = false,
  scanPhase = null,
  scanStep = 0,
  scanTotalSteps = 0,
  os,
  openPorts,
  services,
  credentialFound,
  lastScanAt,
  onScan,
  onSetActive,
  onDelete,
  onViewScanResult,
}: HostNodeCardProps) {
  const t = useTranslations("HostCard");

  return (
    <div
      className={`bg-[var(--color-bg-surface)] border rounded-[var(--radius)] p-3 ${
        isCompromised
          ? "border-[var(--color-error)]/60"
          : isActive
            ? "border-[var(--color-accent)]"
            : "border-[var(--color-border)]"
      }`}
    >
      <div className="flex gap-3">
        <ShieldIcon isCompromised={isCompromised} isScanning={isScanning} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-mono font-bold text-[var(--color-text-primary)]">
              {hostname}
            </span>
            <div className="flex items-center gap-1">
              {isActive && (
                <Badge variant="success">
                  {t("active")}
                </Badge>
              )}
              <Badge variant={isCompromised ? "error" : "info"}>
                {isCompromised ? t("compromised") : t("secure")}
              </Badge>
            </div>
          </div>
          <div className="space-y-1 text-xs font-mono text-[var(--color-text-tertiary)]">
            <div className="flex justify-between">
              <span>{t("ip")}</span>
              <span className="text-[var(--color-text-primary)]">{ipAddress}</span>
            </div>
            <div className="flex justify-between">
              <span>{t("role")}</span>
              <span className="text-[var(--color-text-primary)]">{role}</span>
            </div>
            {privilegeLevel && (
              <div className="flex justify-between">
                <span>{t("privilege")}</span>
                <span className="text-[var(--color-accent)]">{privilegeLevel}</span>
              </div>
            )}
          </div>
          {/* Scan results summary */}
          {openPorts != null && openPorts > 0 && !isScanning && (
            <div className="mt-2 pt-2 border-t border-[var(--color-border)]/30 space-y-1">
              {os && (
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-[var(--color-text-tertiary)]">{t("os")}</span>
                  <span className="text-[var(--color-text-primary)]">{os}</span>
                </div>
              )}
              <div className="flex justify-between text-xs font-mono">
                <span className="text-[var(--color-text-tertiary)]">{t("ports")}</span>
                <span className="text-[var(--color-accent)]">{openPorts} open</span>
              </div>
              {services && services.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {services.slice(0, 3).map((svc) => (
                    <span
                      key={svc.port}
                      className="text-[9px] font-mono bg-[var(--color-border-subtle)] rounded-[var(--radius)] px-1.5 py-px text-[var(--color-text-secondary)]"
                    >
                      {svc.port}/{svc.service}
                    </span>
                  ))}
                  {services.length > 3 && (
                    <span className="text-[9px] font-mono text-[var(--color-text-secondary)]">
                      +{services.length - 3}
                    </span>
                  )}
                </div>
              )}
              {credentialFound && (
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-[var(--color-text-tertiary)]">{t("credential")}</span>
                  <span className="text-[var(--color-warning)]">{credentialFound}</span>
                </div>
              )}
              {lastScanAt && (
                <div className="text-sm font-mono text-[var(--color-text-tertiary)] text-right">
                  {lastScanAt.split("T")[1]?.slice(0, 8)}
                </div>
              )}
              {onViewScanResult && (
                <button
                  onClick={onViewScanResult}
                  className="text-sm font-mono text-[var(--color-accent)] hover:underline"
                >
                  {t("viewDetails")}
                </button>
              )}
            </div>
          )}
          {isScanning && (
            <div className="mt-2 space-y-1">
              <div className="flex items-center justify-between text-sm font-mono">
                <span className="text-[var(--color-accent)] animate-pulse">
                  {scanPhase
                    ? t(`phase_${scanPhase}` as Parameters<typeof t>[0])
                    : t("scanning")}
                </span>
                {scanTotalSteps > 0 && (
                  <span className="text-[var(--color-text-tertiary)]">
                    {scanStep}/{scanTotalSteps}
                  </span>
                )}
              </div>
              <ProgressBar
                value={scanStep}
                max={scanTotalSteps || 1}
              />
            </div>
          )}
          {(onScan || onSetActive || onDelete) && id && (
            <div className="mt-3 flex gap-2 flex-wrap">
              {onScan && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onScan(id)}
                  disabled={isScanning}
                >
                  {isScanning ? t("scanning") : t("reconScan")}
                </Button>
              )}
              {onSetActive && (
                <Tooltip text={t(isActive ? "deactivateHint" : "setActiveHint")}>
                  <Button
                    variant={isActive ? "secondary" : "primary"}
                    size="sm"
                    onClick={() => onSetActive(id, !isActive)}
                  >
                    {isActive ? t("deactivate") : t("setActive")}
                  </Button>
                </Tooltip>
              )}
              {onDelete && (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => onDelete(id)}
                  disabled={isActive || isScanning}
                  title={isActive ? t("cannotDeleteActive") : undefined}
                >
                  {t("delete")}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
