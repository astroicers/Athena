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
        className="fixed inset-y-0 right-0 w-96 z-50 flex flex-col bg-athena-bg-secondary border-l border-athena-border animate-in slide-in-from-right duration-200"
        role="dialog"
        aria-label={t("title")}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-athena-border">
          <h2 className="text-xs font-mono font-bold tracking-widest text-athena-text-primary uppercase">
            {t("title")}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleClearAll}
              className="text-[10px] font-mono text-athena-text-tertiary hover:text-athena-text-primary transition-colors uppercase"
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

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          {/* Pinned constraint card */}
          {constraintAlert.active && constraintAlert.messages.length > 0 && (
            <div className="mx-3 mt-3 p-3 rounded border border-amber-500/40 bg-amber-500/10">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" />
                <span className="text-[10px] font-mono font-bold text-amber-400 uppercase tracking-wider">
                  {t("constraintActive")}
                </span>
              </div>
              {constraintAlert.messages.map((msg, i) => (
                <p
                  key={i}
                  className="text-xs font-mono text-athena-text-secondary ml-4 leading-relaxed"
                >
                  {msg}
                </p>
              ))}
            </div>
          )}

          {/* Notification list */}
          {displayAlerts.length === 0 &&
          !(constraintAlert.active && constraintAlert.messages.length > 0) ? (
            <div className="flex items-center justify-center h-48">
              <p className="text-xs font-mono text-athena-text-tertiary">
                {t("empty")}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-athena-border">
              {displayAlerts.map((alert) => (
                <li
                  key={alert.id}
                  className="px-4 py-3 hover:bg-athena-bg-tertiary/50 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    {/* Severity dot */}
                    <span
                      className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                        alert.severity === "error"
                          ? "bg-red-500"
                          : "bg-amber-400"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-athena-text-primary leading-relaxed break-words">
                        {alert.message}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] font-mono font-bold text-athena-accent uppercase tracking-wider">
                          {t("sourceOpsec")}
                        </span>
                        <span className="text-xs text-athena-text-tertiary font-mono">
                          {formatTimestamp(alert.timestamp)}
                        </span>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}
