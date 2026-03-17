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

import { useEffect, useState } from "react";

export interface ConstraintData {
  active: boolean;
  messages: string[];
  domains?: string[];
}

/**
 * Global constraint banner that warns operators when mission constraints
 * are active (e.g., ROE violations, OPSEC limits, time windows).
 *
 * Dismissible, but re-appears when new constraints arrive.
 * Provides per-domain override buttons when domain info is available.
 */
export function ConstraintBanner({
  constraints,
  onOverride,
}: {
  constraints: ConstraintData;
  onOverride?: (domain: string) => void;
}) {
  const [dismissed, setDismissed] = useState(false);
  const [lastMessages, setLastMessages] = useState<string>("");
  const [overriding, setOverriding] = useState<string | null>(null);

  // Re-show banner when messages change
  useEffect(() => {
    const key = constraints.messages.join(",");
    if (key !== lastMessages) {
      setLastMessages(key);
      setDismissed(false);
    }
  }, [constraints.messages, lastMessages]);

  if (!constraints.active || constraints.messages.length === 0 || dismissed) {
    return null;
  }

  // Severity: if any message contains "critical" or "violation", use red; otherwise amber
  const isCritical = constraints.messages.some(
    (m) => /critical|violation|breach/i.test(m)
  );

  const bgClass = isCritical ? "bg-red-500/90" : "bg-amber-600/90";
  const domains = constraints.domains ?? [];

  async function handleOverride(domain: string) {
    if (!onOverride || overriding) return;
    setOverriding(domain);
    try {
      onOverride(domain);
    } finally {
      setTimeout(() => setOverriding(null), 1000);
    }
  }

  return (
    <div
      className={`${bgClass} text-white text-xs font-mono px-4 py-1.5 text-center flex items-center justify-center gap-2`}
    >
      <span className="font-bold">CONSTRAINT ACTIVE</span>
      <span>|</span>
      <span>{constraints.messages.join(", ")}</span>
      {onOverride && domains.length > 0 && (
        <>
          <span>|</span>
          {domains.map((domain) => (
            <button
              key={domain}
              onClick={() => handleOverride(domain)}
              disabled={overriding === domain}
              className="px-1.5 py-0.5 bg-white/20 hover:bg-white/5 rounded-athena-sm text-[10px] uppercase font-bold tracking-wider transition-colors disabled:opacity-50 focus:outline-none focus:ring-1 focus:ring-white/20"
            >
              {overriding === domain ? "..." : `Override ${domain}`}
            </button>
          ))}
        </>
      )}
      <button
        onClick={() => setDismissed(true)}
        className="ml-2 hover:text-white/70 transition-colors focus:outline-none focus:ring-1 focus:ring-white/20"
        aria-label="Dismiss constraint banner"
      >
        x
      </button>
    </div>
  );
}
