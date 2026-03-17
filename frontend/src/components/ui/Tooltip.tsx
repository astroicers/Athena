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

import { ReactNode } from "react";

interface TooltipProps {
  text: string;
  children: ReactNode;
}

export function Tooltip({ text, children }: TooltipProps) {
  return (
    <span className="relative group inline-block">
      {children}
      <span className="pointer-events-none absolute bottom-full left-0 mb-1.5 px-2 py-1 text-sm font-mono text-[#e5e7eb] bg-[#1f2937] border border-[#1f2937] rounded-athena-sm max-w-[320px] break-all whitespace-normal hidden group-hover:block z-50">
        {text}
      </span>
    </span>
  );
}
