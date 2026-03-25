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
  borderClass: string;
  textClass: string;
  dotClass: string;
  badgeText: string;
}

const SEVERITY_STYLES: Record<OpsecSeverity, SeverityStyle> = {
  error: {
    borderClass: "border-l-[var(--color-error)]",
    textClass: "text-[var(--color-error)]",
    dotClass: "bg-[var(--color-error)]",
    badgeText: "CRITICAL",
  },
  warning: {
    borderClass: "border-l-[var(--color-warning)]",
    textClass: "text-[var(--color-warning)]",
    dotClass: "bg-[var(--color-warning)]",
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
        className="fixed inset-0 z-50 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-in panel */}
      <aside
        className="fixed right-0 top-0 h-full w-[380px] bg-[var(--color-bg-surface)] border-l border-[var(--color-border)] z-50 flex flex-col"
        role="dialog"
        aria-label={t("title")}
      >
        {/* -- Header -- */}
        <div
          className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]"
        >
          <div className="flex items-center gap-2">
            <h2
              className="text-sm font-mono font-bold text-[var(--color-text-primary)]"
            >
              {t("title")}
            </h2>
            {totalCount > 0 && (
              <span
                className="bg-[var(--color-error)] text-white text-xs font-bold px-2 py-1 rounded-full min-w-[20px] text-center"
              >
                {totalCount > 99 ? "99+" : totalCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleClearAll}
              className="text-xs font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors"
            >
              {t("clearAll")}
            </button>
            <button
              onClick={onClose}
              className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* -- Scrollable content -- */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center h-64">
              <span
                className="text-xs font-mono text-[var(--color-text-tertiary)]"
              >
                {t("empty")}
              </span>
            </div>
          ) : (
            <>
              {/* -- Pinned Constraints section -- */}
              {hasConstraint && (
                <>
                  <p
                    className="text-xs font-mono font-bold uppercase text-[var(--color-text-tertiary)] tracking-wider px-1"
                  >
                    {t("pinnedConstraints")}
                  </p>

                  {constraintAlert.messages.map((msg, i) => (
                    <div
                      key={i}
                      className="bg-[var(--color-bg-primary)] rounded-[var(--radius)] p-3 border-l-[3px] border-l-[var(--color-warning)]"
                    >
                      {/* Card header row */}
                      <div className="flex items-center justify-between mb-1.5">
                        <span
                          className="text-xs font-mono font-bold uppercase text-[var(--color-warning)]"
                        >
                          {t("constraintActive")}
                        </span>
                        <span
                          className="text-xs font-mono text-[var(--color-text-tertiary)]"
                        >
                          {new Date().toLocaleTimeString(undefined, {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                      </div>
                      {/* Message */}
                      <p
                        className="text-xs font-mono text-[var(--color-text-secondary)] leading-relaxed"
                      >
                        {msg}
                      </p>
                      {/* Source */}
                      {constraintAlert.domains.length > 0 && (
                        <span
                          className="text-xs font-mono text-[var(--color-text-tertiary)] mt-1.5 block"
                        >
                          {t("source")}: constraint_engine / {constraintAlert.domains[i] ?? constraintAlert.domains[0]}
                        </span>
                      )}
                    </div>
                  ))}
                </>
              )}

              {/* -- Divider between sections -- */}
              {hasConstraint && hasOpsec && (
                <div className="border-t border-[var(--color-border-subtle)] mx-1" />
              )}

              {/* -- OPSEC Warnings section -- */}
              {hasOpsec && (
                <>
                  <p
                    className="text-xs font-mono font-bold uppercase text-[var(--color-text-tertiary)] tracking-wider px-1"
                  >
                    {t("opsecWarnings")}
                  </p>

                  {displayAlerts.map((alert) => {
                    const sevStyle = SEVERITY_STYLES[alert.severity];
                    return (
                      <div
                        key={alert.id}
                        className={`bg-[var(--color-bg-primary)] rounded-[var(--radius)] p-3 border-l-[3px] ${sevStyle.borderClass}`}
                      >
                        {/* Card header row */}
                        <div className="flex items-center justify-between mb-1.5">
                          <span
                            className={`text-xs font-mono font-bold uppercase ${sevStyle.textClass}`}
                          >
                            {sevStyle.badgeText}
                          </span>
                          <span
                            className="text-xs font-mono text-[var(--color-text-tertiary)]"
                          >
                            {formatTimestamp(alert.timestamp)}
                          </span>
                        </div>
                        {/* Message */}
                        <p
                          className="text-xs font-mono text-[var(--color-text-secondary)] leading-relaxed"
                        >
                          {alert.message}
                        </p>
                        {/* Source */}
                        <span
                          className="text-xs font-mono text-[var(--color-text-tertiary)] mt-1.5 block"
                        >
                          {t("source")}: {t("sourceOpsec")}
                        </span>
                      </div>
                    );
                  })}
                </>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
