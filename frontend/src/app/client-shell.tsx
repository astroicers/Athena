"use client";

import { ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { PageHeader } from "@/components/layout/PageHeader";
import { AlertBanner } from "@/components/layout/AlertBanner";
import { CommandInput } from "@/components/layout/CommandInput";

export function ClientShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <AlertBanner message={null} />
        <PageHeader title="Athena" operationCode="PHANTOM-EYE" />
        <main className="flex-1 overflow-auto p-4">{children}</main>
        <CommandInput />
      </div>
    </div>
  );
}
