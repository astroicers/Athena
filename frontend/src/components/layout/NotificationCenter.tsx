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

import { useCallback, useMemo } from "react";
import { useTranslations } from "next-intl";
import type { OpsecAlert } from "@/hooks/useGlobalAlerts";
import type { ConstraintAlert } from "@/hooks/useGlobalAlerts";

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
  opsecAlerts: OpsecAlert[];
  constraintAlert: ConstraintAlert;
}

const MAX_DISPLAY = 50;

// Severity → visual style mapping for OPSEC warning cards
type OpsecSeverity = OpsecAlert["severity"];

interface SeverityStyle {
  bg: string;
  border: string;
  dot: string;
  badge: string;
  badgeText: string;
}

const SEVERITY_STYLES: Record<OpsecSeverity, SeverityStyle> = {
  error: {
    bg: "bg-[#EF444410]",
    border: "border-[#EF444425]",
    dot: "bg-red-500",
    badge: "bg-red-500/20 text-red-400",
    badgeText: "CRITICAL",
  },
  warning: {
    bg: "bg-[#F9731610]",
    border: "border-[#F9731625]",
    dot: "bg-orange-500",
    badge: "bg-orange-500/20 text-orange-400",
    badgeText: "HIGH",
  },
};

export function NotificationCenter({
  isOpen,
  onClose,
  opsecAlerts,
  constraintAlert,
}: NotificationCenterProps) {
  const t = useTranslations("Notifications");

  const displayAlerts = useMemo(
    () => opsecAlerts.slice(-MAX_DISPLAY).reverse(),
    [opsecAlerts],
  );

  const totalCount =
    displayAlerts.length + (constraintAlert.active && constraintAlert.messages.length > 0 ? 1 : 0);

  const handleClearAll = useCallback(() => {
    // Clear is managed by the parent; close the panel after requesting clear
    onClose();
  }, [onClose]);

  const formatTimestamp = useCallback((iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return iso;
    }
  }, []);

  if (!isOpen) return null;

  const hasConstraint = constraintAlert.active && constraintAlert.messages.length > 0;
  const hasOpsec = displayAlerts.length > 0;
  const isEmpty = !hasConstraint && !hasOpsec;

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-in panel */}
      <aside
        className="fixed inset-y-0 right-0 w-96 z-50 flex flex-col bg-[#111827] border-l border-[#FFFFFF10] animate-in slide-in-from-right duration-200"
        style={{ fontFamily: "'JetBrains Mono', 'Courier New', monospace" }}
        role="dialog"
        aria-label={t("title")}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#FFFFFF10]">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-mono font-bold tracking-widest text-athena-text-primary uppercase">
              {t("title")}
            </h2>
            {totalCount > 0 && (
              <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-[9px] font-mono font-bold text-white leading-none">
                {totalCount > 99 ? "99+" : totalCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleClearAll}
              className="text-[10px] font-mono text-blue-400 hover:text-blue-300 transition-colors uppercase tracking-wider"
            >
              {t("clearAll")}
            </button>
            <button
              onClick={onClose}
              className="text-athena-text-tertiary hover:text-athena-text-primary transition-colors p-1"
              aria-label="Close"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* ── Scrollable content ── */}
        <div className="flex-1 overflow-y-auto">
          {isEmpty ? (
            <div className="flex items-center justify-center h-48">
              <p className="text-xs font-mono text-athena-text-tertiary">
                {t("empty")}
              </p>
            </div>
          ) : (
            <>
              {/* ── Pinned Constraints section ── */}
              {hasConstraint && (
                <section>
                  <p className="px-4 pt-4 pb-2 text-[10px] font-mono font-semibold tracking-widest text-athena-text-tertiary uppercase">
                    {t("pinnedConstraints")}
                  </p>

                  <div className="px-3 pb-3 space-y-2">
                    {constraintAlert.messages.map((msg, i) => (
                      <div
                        key={i}
                        className="rounded border border-[#F59E0B50] bg-[#F59E0B10] p-3"
                      >
                        {/* Card header row */}
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" />
                            <span className="text-[10px] font-mono font-bold text-amber-400 uppercase tracking-wider">
                              {t("constraintActive")}
                            </span>
                          </div>
                          <span className="text-[10px] font-mono text-athena-text-tertiary">
                            {new Date().toLocaleTimeString(undefined, {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>
                        </div>
                        {/* Message */}
                        <p className="text-xs font-mono text-athena-text-secondary leading-relaxed ml-4">
                          {msg}
                        </p>
                        {/* Source */}
                        {constraintAlert.domains.length > 0 && (
                          <p className="text-[10px] font-mono text-athena-text-tertiary ml-4 mt-1.5">
                            {t("source")}:{" "}
                            <span className="text-amber-500/80">
                              constraint_engine / {constraintAlert.domains[i] ?? constraintAlert.domains[0]}
                            </span>
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* ── Divider between sections ── */}
              {hasConstraint && hasOpsec && (
                <div className="mx-4 border-t border-[#FFFFFF10]" />
              )}

              {/* ── OPSEC Warnings section ── */}
              {hasOpsec && (
                <section>
                  <p className="px-4 pt-4 pb-2 text-[10px] font-mono font-semibold tracking-widest text-athena-text-tertiary uppercase">
                    {t("opsecWarnings")}
                  </p>

                  <ul className="px-3 pb-3 space-y-2">
                    {displayAlerts.map((alert) => {
                      const style = SEVERITY_STYLES[alert.severity];
                      return (
                        <li
                          key={alert.id}
                          className={`rounded border ${style.bg} ${style.border} p-3`}
                        >
                          {/* Card header row */}
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <span
                                className={`w-2 h-2 rounded-full shrink-0 ${style.dot}`}
                              />
                              <span
                                className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${style.badge}`}
                              >
                                {style.badgeText}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono text-athena-text-tertiary">
                              {formatTimestamp(alert.timestamp)}
                            </span>
                          </div>
                          {/* Message */}
                          <p className="text-xs font-mono text-athena-text-primary leading-relaxed ml-4 break-words">
                            {alert.message}
                          </p>
                          {/* Source */}
                          <p className="text-[10px] font-mono text-athena-text-tertiary ml-4 mt-1.5">
                            {t("source")}:{" "}
                            <span className="text-athena-text-secondary">
                              {t("sourceOpsec")}
                            </span>
                          </p>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
