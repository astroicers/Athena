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

import { ReactNode } from "react";

const VARIANT_STYLES = {
  success: "bg-athena-success/20 text-athena-success border-athena-success/40",
  warning: "bg-athena-warning/20 text-athena-warning border-athena-warning/40",
  error: "bg-athena-error/20 text-athena-error border-athena-error/40",
  info: "bg-athena-accent/20 text-athena-accent border-athena-accent/40",
} as const;

interface BadgeProps {
  variant?: keyof typeof VARIANT_STYLES;
  children: ReactNode;
}

export function Badge({ variant = "info", children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono border
        ${VARIANT_STYLES[variant]}`}
    >
      {children}
    </span>
  );
}
