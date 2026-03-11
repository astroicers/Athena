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

interface MockStatus {
  llm?: boolean;
  c2?: boolean;
  metasploit?: boolean;
}

/**
 * Banner that warns operators when mock modes are active.
 * Polls /api/health on mount and reads mock_mode from services.
 */
export function MockBanner() {
  const [mocks, setMocks] = useState<MockStatus | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || "/api";
    fetch(`${base}/health`)
      .then((r) => r.json())
      .then((data) => {
        const mockMode = data?.services?.mock_mode;
        if (mockMode && Object.keys(mockMode).length > 0) {
          setMocks(mockMode);
        }
      })
      .catch(() => {
        // health check failed — don't show banner
      });
  }, []);

  if (!mocks) return null;

  const active = Object.entries(mocks)
    .filter(([, v]) => v)
    .map(([k]) => k.toUpperCase());

  return (
    <div className="bg-amber-500/90 text-black text-xs font-mono px-4 py-1.5 text-center flex items-center justify-center gap-2">
      <span className="font-bold">MOCK MODE</span>
      <span>|</span>
      <span>
        {active.join(", ")} — using simulated data, not real services
      </span>
    </div>
  );
}
