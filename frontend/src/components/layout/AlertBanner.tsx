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

import { useState } from "react";

interface AlertBannerProps {
  message: string | null;
  severity?: "warning" | "error" | "critical";
}

const SEVERITY_STYLES = {
  warning: "bg-athena-warning/10 border-athena-warning text-athena-warning",
  error: "bg-athena-error/10 border-athena-error text-athena-error",
  critical: "bg-athena-critical/10 border-athena-critical text-athena-critical",
};

export function AlertBanner({ message, severity = "warning" }: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (!message || dismissed) return null;

  return (
    <div
      className={`px-4 py-2 border-b text-xs font-mono flex items-center justify-between
        ${SEVERITY_STYLES[severity]}`}
    >
      <span>{message}</span>
      <button
        onClick={() => setDismissed(true)}
        className="ml-4 opacity-60 hover:opacity-100"
      >
        DISMISS
      </button>
    </div>
  );
}
