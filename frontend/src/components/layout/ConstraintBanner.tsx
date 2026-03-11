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

import { useEffect, useState } from "react";

export interface ConstraintData {
  active: boolean;
  messages: string[];
}

/**
 * Global constraint banner that warns operators when mission constraints
 * are active (e.g., ROE violations, OPSEC limits, time windows).
 *
 * Dismissible, but re-appears when new constraints arrive.
 */
export function ConstraintBanner({
  constraints,
}: {
  constraints: ConstraintData;
}) {
  const [dismissed, setDismissed] = useState(false);
  const [lastMessages, setLastMessages] = useState<string>("");

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

  return (
    <div
      className={`${bgClass} text-white text-xs font-mono px-4 py-1.5 text-center flex items-center justify-center gap-2`}
    >
      <span className="font-bold">CONSTRAINT ACTIVE</span>
      <span>|</span>
      <span>{constraints.messages.join(", ")}</span>
      <button
        onClick={() => setDismissed(true)}
        className="ml-2 hover:text-white/70 transition-colors"
        aria-label="Dismiss constraint banner"
      >
        x
      </button>
    </div>
  );
}
