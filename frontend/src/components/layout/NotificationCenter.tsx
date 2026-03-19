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
import { Button } from "@/components/atoms/Button";
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
    bg: "",
    border: "",
    dot: "",
    badge: "",
    badgeText: "CRITICAL",
  },
  warning: {
    bg: "",
    border: "",
    dot: "",
    badge: "",
    badgeText: "HIGH",
  },
};

function severityColors(sev: OpsecSeverity) {
  if (sev === "error") return { fill: "color-mix(in srgb, var(--color-error) 6%, transparent)", border: "color-mix(in srgb, var(--color-error) 15%, transparent)", text: "var(--color-error)" };
  return { fill: "#F9731610", border: "#F9731625", text: "#F97316" };
}

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
        className="fixed inset-0 z-40"
        style={{ backgroundColor: "#00000060" }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-in panel */}
      <aside
        className="fixed inset-y-0 right-0 z-50 flex flex-col animate-in slide-in-from-right duration-200"
        style={{
          width: 384,
          backgroundColor: "var(--color-bg-surface)",
          borderLeft: "1px solid #FFFFFF10",
          fontFamily: "'JetBrains Mono', 'Courier New', monospace",
        }}
        role="dialog"
        aria-label={t("title")}
      >
        {/* ── Header ── */}
        <div
          className="flex items-center justify-between shrink-0"
          style={{ height: 56, backgroundColor: "var(--color-bg-elevated)", padding: "0 20px" }}
        >
          <div className="flex items-center gap-2">
            <h2
              className="font-mono font-bold uppercase"
              style={{ fontSize: 13, color: "#FFFFFF" }}
            >
              {t("title")}
            </h2>
            {totalCount > 0 && (
              <span
                className="inline-flex items-center justify-center font-mono font-bold text-white leading-none rounded-[10px]"
                style={{
                  minWidth: 20,
                  height: 20,
                  padding: "2px 8px",
                  backgroundColor: "var(--color-error)",
                  fontSize: 9,
                }}
              >
                {totalCount > 99 ? "99+" : totalCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleClearAll}
              className="text-[10px] text-athena-accent bg-transparent border-transparent hover:bg-transparent"
            >
              {t("clearAll")}
            </Button>
            <button
              onClick={onClose}
              className="transition-colors p-1"
              style={{ color: "#FFFFFF50", fontSize: 14, fontWeight: 700 }}
              aria-label="Close"
            >
              X
            </button>
          </div>
        </div>

        {/* ── Scrollable content ── */}
        <div className="flex-1 overflow-y-auto">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <span
                className="font-mono font-bold"
                style={{ fontSize: 40, color: "#FFFFFF15" }}
              >
                {"[ ]"}
              </span>
              <span
                className="font-mono"
                style={{ fontSize: 13, fontWeight: 600, color: "#FFFFFF30" }}
              >
                {t("empty")}
              </span>
            </div>
          ) : (
            <>
              {/* ── Pinned Constraints section ── */}
              {hasConstraint && (
                <section style={{ padding: "12px 16px" }} className="flex flex-col gap-2">
                  <p
                    className="font-mono font-bold uppercase"
                    style={{ fontSize: 8, color: "#FFFFFF40", letterSpacing: "1.5px" }}
                  >
                    {t("pinnedConstraints")}
                  </p>

                  {constraintAlert.messages.map((msg, i) => (
                    <div
                      key={i}
                      className="flex flex-col rounded-athena"
                      style={{
                        backgroundColor: "color-mix(in srgb, var(--color-warning) 6%, transparent)",
                        border: "1px solid color-mix(in srgb, var(--color-warning) 30%, transparent)",
                        padding: "12px 14px",
                        gap: 6,
                      }}
                    >
                      {/* Card header row */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: "var(--color-warning)" }}
                          />
                          <span
                            className="font-mono font-bold uppercase tracking-wider"
                            style={{ fontSize: 10, color: "var(--color-warning)" }}
                          >
                            {t("constraintActive")}
                          </span>
                        </div>
                        <span
                          className="font-mono"
                          style={{ fontSize: 8, color: "#FFFFFF30" }}
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
                        className="font-mono leading-relaxed"
                        style={{ fontSize: 10, color: "#FFFFFFB0" }}
                      >
                        {msg}
                      </p>
                      {/* Source */}
                      {constraintAlert.domains.length > 0 && (
                        <span
                          className="font-mono"
                          style={{ fontSize: 8, color: "#FFFFFF30" }}
                        >
                          {t("source")}: constraint_engine / {constraintAlert.domains[i] ?? constraintAlert.domains[0]}
                        </span>
                      )}
                    </div>
                  ))}
                </section>
              )}

              {/* ── Divider between sections ── */}
              {hasConstraint && hasOpsec && (
                <div style={{ borderTop: "1px solid #FFFFFF08", margin: "0 16px" }} />
              )}

              {/* ── OPSEC Warnings section ── */}
              {hasOpsec && (
                <section
                  className="flex flex-col gap-2 flex-1 overflow-y-auto"
                  style={{ padding: "12px 16px" }}
                >
                  <p
                    className="font-mono font-bold uppercase"
                    style={{ fontSize: 8, color: "#FFFFFF40", letterSpacing: "1.5px" }}
                  >
                    {t("opsecWarnings")}
                  </p>

                  {displayAlerts.map((alert) => {
                    const colors = severityColors(alert.severity);
                    const style = SEVERITY_STYLES[alert.severity];
                    return (
                      <div
                        key={alert.id}
                        className="flex flex-col rounded-athena"
                        style={{
                          backgroundColor: colors.fill,
                          border: `1px solid ${colors.border}`,
                          padding: "10px 12px",
                          gap: 6,
                        }}
                      >
                        {/* Card header row */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ backgroundColor: colors.text }}
                            />
                            <span
                              className="font-mono font-bold uppercase tracking-wider"
                              style={{ fontSize: 10, color: colors.text }}
                            >
                              {style.badgeText}
                            </span>
                          </div>
                          <span
                            className="font-mono"
                            style={{ fontSize: 8, color: "#FFFFFF30" }}
                          >
                            {formatTimestamp(alert.timestamp)}
                          </span>
                        </div>
                        {/* Message */}
                        <p
                          className="font-mono leading-relaxed break-words"
                          style={{ fontSize: 9, color: "#FFFFFFA0" }}
                        >
                          {alert.message}
                        </p>
                        {/* Source */}
                        <span
                          className="font-mono"
                          style={{ fontSize: 8, color: "#FFFFFF25" }}
                        >
                          {t("source")}: {t("sourceOpsec")}
                        </span>
                      </div>
                    );
                  })}
                </section>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
