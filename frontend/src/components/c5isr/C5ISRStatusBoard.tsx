"use client";

import { DomainCard } from "./DomainCard";
import type { C5ISRStatus } from "@/types/c5isr";

interface C5ISRStatusBoardProps {
  domains: C5ISRStatus[];
}

export function C5ISRStatusBoard({ domains }: C5ISRStatusBoardProps) {
  if (domains.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 text-center">
        <span className="text-xs font-mono text-athena-text-secondary">
          No C5ISR domain data available
        </span>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-3">
        C5ISR Domain Status
      </h2>
      <div className="grid grid-cols-3 gap-3">
        {domains.map((d) => (
          <DomainCard key={d.id} domain={d} />
        ))}
      </div>
    </div>
  );
}
