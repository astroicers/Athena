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

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  ToolRegistryEntry,
  ToolRegistryCreate,
  ToolHealthCheck,
} from "@/types/tool";

interface UseToolsReturn {
  tools: ToolRegistryEntry[];
  loading: boolean;
  fetchTools: () => Promise<void>;
  toggleEnabled: (toolId: string, enabled: boolean) => Promise<void>;
  checkHealth: (toolId: string) => Promise<ToolHealthCheck>;
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

  const checkHealth = useCallback(async (toolId: string) => {
    return api.post<ToolHealthCheck>(`/tools/${toolId}/check`);
  }, []);

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
    checkHealth,
    deleteTool,
    createTool,
  };
}
