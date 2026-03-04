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

import { useTranslations } from "next-intl";
import { DomainCard } from "./DomainCard";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import type { C5ISRStatus } from "@/types/c5isr";

interface C5ISRStatusBoardProps {
  domains: C5ISRStatus[];
}

export function C5ISRStatusBoard({ domains }: C5ISRStatusBoardProps) {
  const t = useTranslations("C5ISR");

  if (domains.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 text-center">
        <span className="text-xs font-mono text-athena-text-secondary">
          {t("noDomainData")}
        </span>
      </div>
    );
  }

  return (
    <div>
      <SectionHeader className="mb-3">
        {t("domainStatus")}
      </SectionHeader>
      <div className="grid grid-cols-3 gap-3">
        {domains.map((d) => (
          <DomainCard key={d.id} domain={d} />
        ))}
      </div>
    </div>
  );
}
