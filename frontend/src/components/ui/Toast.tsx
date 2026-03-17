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
import { useToast } from "@/contexts/ToastContext";
import type { ToastSeverity } from "@/contexts/ToastContext";

const SEVERITY_STYLES: Record<ToastSeverity, string> = {
  info: "border-l-[var(--color-info)] text-[var(--color-info)]",
  success: "border-l-[var(--color-success)] text-[var(--color-success)]",
  warning: "border-l-[var(--color-warning)] text-[var(--color-warning)]",
  error: "border-l-[var(--color-error)] text-[var(--color-error)]",
};

const SEVERITY_KEY: Record<ToastSeverity, "info" | "ok" | "warn" | "err"> = {
  info: "info",
  success: "ok",
  warning: "warn",
  error: "err",
};

export function ToastContainer() {
  const t = useTranslations("UI");
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            bg-[var(--color-bg-elevated)] border border-[var(--color-border)]
            border-l-4 ${SEVERITY_STYLES[toast.severity]}
            px-3 py-2 rounded font-mono text-xs
            animate-[slideIn_0.2s_ease-out]
            cursor-pointer hover:opacity-80 transition-opacity
          `}
          onClick={() => removeToast(toast.id)}
        >
          <span className="font-bold mr-2">[{t(SEVERITY_KEY[toast.severity])}]</span>
          <span className="text-[var(--color-text-primary)]">{toast.message}</span>
        </div>
      ))}
    </div>
  );
}
