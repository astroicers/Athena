// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useToast } from "@/contexts/ToastContext";
import type { ToastSeverity } from "@/contexts/ToastContext";

const SEVERITY_STYLES: Record<ToastSeverity, string> = {
  info: "border-l-[var(--color-info)] text-[var(--color-info)]",
  success: "border-l-[var(--color-success)] text-[var(--color-success)]",
  warning: "border-l-[var(--color-warning)] text-[var(--color-warning)]",
  error: "border-l-[var(--color-error)] text-[var(--color-error)]",
};

const SEVERITY_LABEL: Record<ToastSeverity, string> = {
  info: "INFO",
  success: "OK",
  warning: "WARN",
  error: "ERR",
};

export function ToastContainer() {
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
          <span className="font-bold mr-2">[{SEVERITY_LABEL[toast.severity]}]</span>
          <span className="text-[var(--color-text-primary)]">{toast.message}</span>
        </div>
      ))}
    </div>
  );
}
