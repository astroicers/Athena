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
    ? "bg-[#3b82f610]"
    : isCompromised
      ? "bg-[#EF444410]"
      : "bg-[#22C55E10]";

  return (
    <div className={`shrink-0 w-8 h-8 rounded flex items-center justify-center ${bgColor}`}>
      {isScanning ? (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="animate-spin" style={{ animationDuration: "3s" }}>
          <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" strokeDasharray="22 22" className="text-[#3b82f6]" />
          <circle cx="10" cy="10" r="2" fill="currentColor" className="text-[#3b82f6]" />
        </svg>
      ) : isCompromised ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#EF4444]">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 9l6 6M15 9l-6 6" />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#22C55E]">
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
      className={`bg-[#111827] border rounded-lg p-3 ${
        isCompromised
          ? "border-[#EF4444]/60"
          : isActive
            ? "border-[#3b82f6]"
            : "border-[#1f2937]"
      }`}
    >
      <div className="flex gap-3">
        <ShieldIcon isCompromised={isCompromised} isScanning={isScanning} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-mono font-bold text-[#e5e7eb]">
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
          <div className="space-y-1 text-xs font-mono text-[#9ca3af]">
            <div className="flex justify-between">
              <span>{t("ip")}</span>
              <span className="text-[#e5e7eb]">{ipAddress}</span>
            </div>
            <div className="flex justify-between">
              <span>{t("role")}</span>
              <span className="text-[#e5e7eb]">{role}</span>
            </div>
            {privilegeLevel && (
              <div className="flex justify-between">
                <span>{t("privilege")}</span>
                <span className="text-[#3b82f6]">{privilegeLevel}</span>
              </div>
            )}
          </div>
          {/* Scan results summary */}
          {openPorts != null && openPorts > 0 && !isScanning && (
            <div className="mt-2 pt-2 border-t border-[#1f2937]/30 space-y-1">
              {os && (
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-[#9ca3af]">{t("os")}</span>
                  <span className="text-[#e5e7eb]">{os}</span>
                </div>
              )}
              <div className="flex justify-between text-xs font-mono">
                <span className="text-[#9ca3af]">{t("ports")}</span>
                <span className="text-[#3b82f6]">{openPorts} open</span>
              </div>
              {services && services.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {services.slice(0, 3).map((svc) => (
                    <span
                      key={svc.port}
                      className="text-sm font-mono bg-[#0A0E17] border border-[#1f293780] rounded px-1.5 py-0.5 text-[#9ca3af]"
                    >
                      {svc.port}/{svc.service}
                    </span>
                  ))}
                  {services.length > 3 && (
                    <span className="text-sm font-mono text-[#9ca3af]">
                      +{services.length - 3}
                    </span>
                  )}
                </div>
              )}
              {credentialFound && (
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-[#9ca3af]">{t("credential")}</span>
                  <span className="text-[#FBBF24]">{credentialFound}</span>
                </div>
              )}
              {lastScanAt && (
                <div className="text-sm font-mono text-[#9ca3af] text-right">
                  {lastScanAt.split("T")[1]?.slice(0, 8)}
                </div>
              )}
              {onViewScanResult && (
                <button
                  onClick={onViewScanResult}
                  className="text-sm font-mono text-[#3b82f6] hover:underline"
                >
                  {t("viewDetails")}
                </button>
              )}
            </div>
          )}
          {isScanning && (
            <div className="mt-2 space-y-1">
              <div className="flex items-center justify-between text-sm font-mono">
                <span className="text-[#3b82f6] animate-pulse">
                  {scanPhase
                    ? t(`phase_${scanPhase}` as Parameters<typeof t>[0])
                    : t("scanning")}
                </span>
                {scanTotalSteps > 0 && (
                  <span className="text-[#9ca3af]">
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
