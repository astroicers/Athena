"use client";

import { useEffect, useState, useCallback } from "react";

interface MCPServerInfo {
  name: string;
  transport: string;
  enabled: boolean;
  connected: boolean;
  tool_count: number;
  description: string;
  circuit_state: string;   // "closed" | "open" | "half_open"
  failure_count: number;
}

export function useMCPServers(pollIntervalMs = 30000) {
  const [servers, setServers] = useState<MCPServerInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchServers = useCallback(async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || "/api";
      const resp = await fetch(`${base}/health`);
      const data = await resp.json();
      if (data.services?.mcp_servers) {
        setServers(data.services.mcp_servers);
      }
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchServers();
    const timer = setInterval(fetchServers, pollIntervalMs);
    return () => clearInterval(timer);
  }, [fetchServers, pollIntervalMs]);

  return { servers, loading, refetch: fetchServers };
}
