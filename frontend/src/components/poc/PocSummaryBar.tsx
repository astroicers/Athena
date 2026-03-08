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
import { MetricCard } from "@/components/cards/MetricCard";
import type { PocSummary } from "@/types/poc";

interface PocSummaryBarProps {
  summary: PocSummary;
}

export function PocSummaryBar({ summary }: PocSummaryBarProps) {
  const t = useTranslations("Poc");

  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard
        title={t("totalPocs")}
        value={summary.total}
        accentColor="var(--color-accent)"
      />
      <MetricCard
        title={t("reproducible")}
        value={summary.reproducible}
        accentColor="var(--color-success)"
        gauge={{ value: summary.reproducible, max: summary.total }}
      />
      <MetricCard
        title={t("targets")}
        value={summary.targets}
        accentColor="var(--color-warning)"
      />
      <MetricCard
        title={t("techniques")}
        value={summary.techniques}
        accentColor="var(--color-accent)"
      />
    </div>
  );
}
