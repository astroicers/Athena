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

import { useState, useMemo, ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  sortable?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: string;
  emptyMessage?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  keyField,
  emptyMessage = "No data available",
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(true);

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return sortAsc ? va - vb : vb - va;
      }
      const sa = String(va);
      const sb = String(vb);
      return sortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
  }, [data, sortKey, sortAsc]);

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  if (data.length === 0) {
    return (
      <div className="bg-athena-surface border border-athena-border rounded-athena-md p-6 text-center">
        <span className="text-xs font-mono text-athena-text-secondary">{emptyMessage}</span>
      </div>
    );
  }

  return (
    <div className="bg-athena-surface border border-athena-border rounded-athena-md overflow-hidden">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-athena-border">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-3 py-2 text-left text-athena-text-secondary font-medium uppercase tracking-wider ${
                  col.sortable ? "cursor-pointer hover:text-athena-accent select-none" : ""
                }`}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                <span className="flex items-center gap-1">
                  {col.header}
                  {col.sortable && sortKey === col.key && (
                    <span>{sortAsc ? "▲" : "▼"}</span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={String(row[keyField])}
              className="border-b border-athena-border/50 hover:bg-athena-elevated/30"
            >
              {columns.map((col) => (
                <td key={col.key} className="px-3 py-2 text-athena-text">
                  {col.render ? col.render(row) : String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
