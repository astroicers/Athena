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

import { useState } from "react";
import { useTranslations } from "next-intl";

interface PocCommandBlockProps {
  commands: string[];
}

export function PocCommandBlock({ commands }: PocCommandBlockProps) {
  const t = useTranslations("Poc");
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(commands.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="relative bg-[#050510] border-l-2 border-athena-success rounded-athena-sm overflow-hidden athena-scanline">
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 z-10 px-2 py-1 text-xs font-mono text-athena-text-secondary hover:text-athena-text bg-athena-elevated/80 rounded transition-colors"
      >
        {copied ? "\u2713" : t("copy")}
      </button>
      <div className="p-4 space-y-1 overflow-x-auto">
        {commands.map((cmd, i) => (
          <div key={i} className="flex gap-2 text-sm font-mono">
            <span className="text-athena-success shrink-0">$</span>
            <span className="text-athena-text whitespace-pre">{cmd}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
