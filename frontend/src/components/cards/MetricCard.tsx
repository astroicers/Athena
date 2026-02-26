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

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  accentColor?: string;
}

export function MetricCard({ title, value, subtitle, accentColor }: MetricCardProps) {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-4 flex flex-col gap-1">
      <span className="text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider">
        {title}
      </span>
      <span
        className="text-2xl font-mono font-bold"
        style={accentColor ? { color: accentColor } : undefined}
      >
        {value}
      </span>
      {subtitle && (
        <span className="text-[10px] font-mono text-athena-text-secondary">
          {subtitle}
        </span>
      )}
    </div>
  );
}
