// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { Toggle } from "@/components/atoms/Toggle";

interface PageHeaderProps {
  title: string;
  operationCode?: string;
  automationMode?: string;
  onModeToggle?: (checked: boolean) => void;
}

export function PageHeader({
  title,
  operationCode,
  automationMode,
  onModeToggle,
}: PageHeaderProps) {
  const isSemiAuto = automationMode === "semi_auto";

  return (
    <header className="h-12 px-4 flex items-center justify-between bg-athena-surface border-b border-athena-border">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-mono font-bold text-athena-text">
          {title}
        </h2>
        {operationCode && (
          <span className="text-xs font-mono text-athena-accent bg-athena-accent/10 px-2 py-0.5 rounded">
            {operationCode}
          </span>
        )}
      </div>

      {onModeToggle && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-athena-text-secondary">
            {isSemiAuto ? "SEMI-AUTO" : "MANUAL"}
          </span>
          <Toggle
            checked={isSemiAuto}
            onChange={onModeToggle}
          />
        </div>
      )}
    </header>
  );
}
