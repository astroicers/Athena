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

interface SituationEdgeProps {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  status: "completed" | "active" | "pending";
}

export function SituationEdge({
  fromX,
  fromY,
  toX,
  toY,
  status,
}: SituationEdgeProps) {
  const color =
    status === "completed"
      ? "#00d4ff"
      : status === "active"
        ? "#00d4ff"
        : "#2a2a4a";

  const opacity = status === "completed" ? 1 : status === "active" ? 0.8 : 0.5;

  const dashArray =
    status === "completed"
      ? undefined
      : status === "active"
        ? "8 4"
        : "4 4";

  return (
    <line
      x1={fromX}
      y1={fromY}
      x2={toX}
      y2={toY}
      stroke={color}
      strokeWidth={1.5}
      strokeDasharray={dashArray}
      opacity={opacity}
      markerEnd="url(#arrowhead)"
      className={status === "active" ? "situation-edge-flow" : undefined}
    />
  );
}
