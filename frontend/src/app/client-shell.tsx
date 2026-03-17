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

import { ReactNode, useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { PageHeader } from "@/components/layout/PageHeader";
import { MockBanner } from "@/components/layout/MockBanner";
import { ConstraintBanner } from "@/components/layout/ConstraintBanner";
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import { useGlobalAlerts } from "@/hooks/useGlobalAlerts";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";

import { ToastProvider } from "@/contexts/ToastContext";
import { OperationProvider, useOperationId } from "@/contexts/OperationContext";
import { ToastContainer } from "@/components/ui/Toast";

function ShellInner({ children }: { children: ReactNode }) {
  const operationId = useOperationId();
  const ws = useWebSocket(operationId);
  const { constraints, opsecAlerts } = useGlobalAlerts(ws);
  const [notifOpen, setNotifOpen] = useState(false);
  const [opCodename, setOpCodename] = useState<string | null>(null);

  useEffect(() => {
    if (!operationId) return;
    api
      .get<{ codename?: string }>(`/operations/${operationId}`)
      .then((op) => setOpCodename(op?.codename ?? null))
      .catch(() => setOpCodename(null));
  }, [operationId]);

  const alertCount = opsecAlerts.length + (constraints.active ? 1 : 0);

  const handleConstraintOverride = useCallback(
    (domain: string) => {
      api
        .post(`/operations/${operationId}/constraints/override`, { domain })
        .catch(() => {});
    },
    [operationId],
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <MockBanner />
        <ConstraintBanner constraints={constraints} onOverride={handleConstraintOverride} />
        <PageHeader
          title="Athena"
          operationCode={opCodename ?? undefined}
          trailing={
            <button
              onClick={() => setNotifOpen(true)}
              className="relative p-1.5 text-[#9ca3af] hover:text-[#3b82f6] transition-colors"
              aria-label="Notifications"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M8 1.5a4 4 0 0 1 4 4v2.5l1.5 2H2.5L4 8V5.5a4 4 0 0 1 4-4z" />
                <path d="M6 12.5a2 2 0 0 0 4 0" />
              </svg>
              {alertCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-[#EF444420] rounded-full text-[8px] font-mono font-bold text-white flex items-center justify-center">
                  {alertCount > 9 ? "9+" : alertCount}
                </span>
              )}
            </button>
          }
        />
        <main className="flex-1 overflow-auto p-4">{children}</main>
      </div>
      <NotificationCenter
        isOpen={notifOpen}
        onClose={() => setNotifOpen(false)}
        opsecAlerts={opsecAlerts}
        constraintAlert={constraints}
      />
    </div>
  );
}

export function ClientShell({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <OperationProvider>
        <ShellInner>{children}</ShellInner>
        <ToastContainer />
      </OperationProvider>
    </ToastProvider>
  );
}
