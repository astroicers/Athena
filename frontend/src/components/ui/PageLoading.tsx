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

import { useTranslations } from "next-intl";

export function PageLoading() {
  const t = useTranslations("UI");
  return (
    <div className="flex items-center justify-center h-full relative overflow-hidden">
      {/* Scan line */}
      <div
        className="absolute left-0 w-full h-px bg-[var(--color-accent)] opacity-40"
        style={{ animation: "scanLine 2s linear infinite" }}
      />
      <div className="text-center space-y-3">
        <div className="text-athena-floor font-mono text-[var(--color-accent)] tracking-[0.3em] animate-pulse">
          {t("initializing")}
        </div>
        <div className="flex gap-1 justify-center">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="w-2.5 h-2.5 rounded-full bg-[var(--color-accent)]"
              style={{
                animation: "pulse 1s ease-in-out infinite",
                animationDelay: `${i * 0.15}s`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
