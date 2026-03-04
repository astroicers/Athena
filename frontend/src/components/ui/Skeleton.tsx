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

interface SkeletonProps {
  className?: string;
}

/** Base skeleton block with shimmer animation */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`bg-athena-border/30 rounded-athena-sm animate-pulse ${className}`}
    />
  );
}

/** Skeleton matching MetricCard layout */
export function MetricCardSkeleton() {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3 space-y-2">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-6 w-14" />
    </div>
  );
}

/** Skeleton matching DataTable layout */
export function DataTableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3 space-y-2">
      <Skeleton className="h-3 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </div>
  );
}

/** Skeleton matching NetworkTopology area */
export function TopologySkeleton({ height = 420 }: { height?: number }) {
  return (
    <div
      className="bg-athena-surface border border-athena-border rounded-athena-md flex items-center justify-center"
      style={{ height }}
    >
      <div className="space-y-3 text-center">
        <Skeleton className="h-16 w-16 rounded-full mx-auto" />
        <Skeleton className="h-3 w-24 mx-auto" />
      </div>
    </div>
  );
}

/** Skeleton for the MITRE matrix area */
export function MITREMatrixSkeleton() {
  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md p-3">
      <div className="flex gap-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="w-28 shrink-0 space-y-1">
            <Skeleton className="h-3 w-full mb-2" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Full page skeleton for C5ISR page */
export function C5ISRPageSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Skeleton className="h-32 w-full rounded-athena-md" />
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-athena-md" />
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <Skeleton className="h-48 rounded-athena-md" />
          <Skeleton className="h-32 rounded-athena-md" />
        </div>
      </div>
    </div>
  );
}

/** Full page skeleton for Monitor page */
export function MonitorPageSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)}
      </div>
      <Skeleton className="h-8 w-full rounded-athena-md" />
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 space-y-3">
          <TopologySkeleton />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-32 rounded-athena-md" />
          <Skeleton className="h-48 rounded-athena-md" />
        </div>
      </div>
    </div>
  );
}

/** Full page skeleton for Navigator page */
export function NavigatorPageSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-20 w-full rounded-athena-md" />
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3">
          <MITREMatrixSkeleton />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-athena-md" />
          <Skeleton className="h-48 rounded-athena-md" />
        </div>
      </div>
    </div>
  );
}

/** Full page skeleton for Planner page */
export function PlannerPageSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-full rounded-athena-md" />
      <DataTableSkeleton rows={5} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Skeleton className="h-48 rounded-athena-md" />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-24 rounded-athena-md" />
          <Skeleton className="h-24 rounded-athena-md" />
        </div>
      </div>
    </div>
  );
}
