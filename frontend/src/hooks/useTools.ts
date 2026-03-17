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

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  ToolRegistryEntry,
  ToolRegistryCreate,
} from "@/types/tool";

interface UseToolsReturn {
  tools: ToolRegistryEntry[];
  loading: boolean;
  fetchTools: () => Promise<void>;
  toggleEnabled: (toolId: string, enabled: boolean) => Promise<void>;
  deleteTool: (toolId: string) => Promise<void>;
  createTool: (data: ToolRegistryCreate) => Promise<ToolRegistryEntry>;
}

export function useTools(kind?: "tool" | "engine"): UseToolsReturn {
  const [tools, setTools] = useState<ToolRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTools = useCallback(async () => {
    setLoading(true);
    try {
      const query = kind ? `?kind=${kind}` : "";
      const data = await api.get<ToolRegistryEntry[]>(`/tools${query}`);
      setTools(data);
    } catch {
      setTools([]);
    } finally {
      setLoading(false);
    }
  }, [kind]);

  const toggleEnabled = useCallback(
    async (toolId: string, enabled: boolean) => {
      await api.patch<ToolRegistryEntry>(`/tools/${toolId}`, { enabled });
      setTools((prev) =>
        prev.map((t) => (t.toolId === toolId ? { ...t, enabled } : t)),
      );
    },
    [],
  );

  const deleteTool = useCallback(async (toolId: string) => {
    await api.delete(`/tools/${toolId}`);
    setTools((prev) => prev.filter((t) => t.toolId !== toolId));
  }, []);

  const createTool = useCallback(async (data: ToolRegistryCreate) => {
    const created = await api.post<ToolRegistryEntry>("/tools", data);
    setTools((prev) => [...prev, created]);
    return created;
  }, []);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  return {
    tools,
    loading,
    fetchTools,
    toggleEnabled,
    deleteTool,
    createTool,
  };
}
