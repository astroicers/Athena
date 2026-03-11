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

import { ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { PageHeader } from "@/components/layout/PageHeader";
import { MockBanner } from "@/components/layout/MockBanner";

import { ToastProvider } from "@/contexts/ToastContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { ToastContainer } from "@/components/ui/Toast";

export function ClientShell({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <SidebarProvider>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <MockBanner />
            <PageHeader title="Athena" operationCode="PHANTOM-EYE" />
            <main className="flex-1 overflow-auto p-4">{children}</main>
          </div>
        </div>
      </SidebarProvider>
      <ToastContainer />
    </ToastProvider>
  );
}
