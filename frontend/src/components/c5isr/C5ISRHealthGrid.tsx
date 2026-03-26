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

import { C5ISRDomainCard } from "./C5ISRDomainCard";
import type { C5ISRStatus } from "@/types/c5isr";
import type { C5ISRDomain } from "@/types/enums";

const DOMAIN_ORDER = [
  "command",
  "control",
  "comms",
  "computers",
  "cyber",
  "isr",
];

interface C5ISRHealthGridProps {
  domains: C5ISRStatus[];
  onDomainClick?: (domain: C5ISRDomain) => void;
}

export function C5ISRHealthGrid({
  domains,
  onDomainClick,
}: C5ISRHealthGridProps) {
  const sorted = [...domains].sort(
    (a, b) =>
      DOMAIN_ORDER.indexOf(a.domain) - DOMAIN_ORDER.indexOf(b.domain),
  );

  return (
    <div>
      <span
        className="font-mono text-athena-floor font-bold uppercase tracking-wider mb-2 block text-[#ffffff20]"
      >
        C5ISR DOMAIN HEALTH
      </span>
      <div className="grid grid-cols-3 gap-2">
        {sorted.map((d) => (
          <C5ISRDomainCard
            key={d.domain}
            domain={d}
            onClick={
              onDomainClick
                ? () => onDomainClick(d.domain as C5ISRDomain)
                : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}
