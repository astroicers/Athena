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

// tech-debt: test-pending (SPEC-018)

"use client";

export function PageLoading() {
  return (
    <div className="flex items-center justify-center h-full relative overflow-hidden">
      {/* Scan line */}
      <div
        className="absolute left-0 w-full h-px bg-[var(--color-accent)] opacity-40"
        style={{ animation: "scanLine 2s linear infinite" }}
      />
      <div className="text-center space-y-3">
        <div className="text-xs font-mono text-[var(--color-accent)] tracking-[0.3em] animate-pulse">
          INITIALIZING SYSTEMS
        </div>
        <div className="flex gap-1 justify-center">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]"
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
