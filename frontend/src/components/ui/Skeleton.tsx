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

interface SkeletonProps {
  className?: string;
}

/** Base skeleton block with shimmer animation */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`bg-athena-elevated/30 rounded-[var(--radius)] animate-pulse ${className}`}
    />
  );
}

/** Skeleton matching MetricCard layout */
export function MetricCardSkeleton() {
  return (
    <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] p-3 space-y-2">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-6 w-14" />
    </div>
  );
}

/** Skeleton matching DataTable layout */
export function DataTableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] p-3 space-y-2">
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
      className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] flex items-center justify-center"
      style={{ height }}
    >
      <div className="space-y-3 text-center">
        <Skeleton className="h-16 w-16 rounded-full mx-auto" />
        <Skeleton className="h-3 w-24 mx-auto" />
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
      <Skeleton className="h-8 w-full rounded-[var(--radius)]" />
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 space-y-3">
          <TopologySkeleton />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-32 rounded-[var(--radius)]" />
          <Skeleton className="h-48 rounded-[var(--radius)]" />
        </div>
      </div>
    </div>
  );
}

/** Full page skeleton for Planner page */
export function PlannerPageSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-full rounded-[var(--radius)]" />
      <DataTableSkeleton rows={5} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Skeleton className="h-48 rounded-[var(--radius)]" />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-24 rounded-[var(--radius)]" />
          <Skeleton className="h-24 rounded-[var(--radius)]" />
        </div>
      </div>
    </div>
  );
}
