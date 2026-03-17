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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Button } from "@/components/atoms/Button";
import type { ToolRegistryEntry } from "@/types/tool";

interface ToolExecuteModalProps {
  tool: ToolRegistryEntry | null;
  onClose: () => void;
}

interface ExecuteResult {
  output?: string;
  [key: string]: unknown;
}

export function ToolExecuteModal({ tool, onClose }: ToolExecuteModalProps) {
  const t = useTranslations("Tools");
  const [argsText, setArgsText] = useState("{}");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!tool) return null;

  const mcpServer = (tool.configJson?.mcpServer ??
    tool.configJson?.mcp_server ??
    null) as string | null;

  async function handleExecute() {
    setError(null);
    setResult(null);

    let parsedArgs: Record<string, unknown>;
    try {
      parsedArgs = JSON.parse(argsText);
    } catch {
      setError(t("invalidJson"));
      return;
    }

    setLoading(true);
    try {
      const res = await api.post<ExecuteResult>(
        `/tools/${tool!.id}/execute`,
        { arguments: parsedArgs },
        { timeoutMs: 120_000 },
      );
      setResult(JSON.stringify(res, null, 2));
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "detail" in err
          ? String((err as { detail: unknown }).detail)
          : String(err);
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="bg-[#111827] border border-[#1f2937] rounded-lg w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#1f2937]">
          <div>
            <h2 className="text-sm font-mono font-bold text-[#3b82f6]">
              {tool.name}
            </h2>
            {mcpServer && (
              <p className="text-xs font-mono text-[#9ca3af] mt-0.5">
                MCP: {mcpServer}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-[#9ca3af] hover:text-[#e5e7eb] text-lg leading-none px-1"
          >
            x
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Arguments input */}
          <div>
            <label className="block text-xs font-mono font-medium text-[#9ca3af] mb-1">
              {t("arguments")}
            </label>
            <textarea
              className="w-full h-32 bg-[#0A0E17] border border-[#1f2937] rounded-lg p-3 font-mono text-xs text-[#e5e7eb] resize-y focus:outline-none focus:border-[#3b82f6]"
              value={argsText}
              onChange={(e) => setArgsText(e.target.value)}
              spellCheck={false}
            />
          </div>

          {/* Execute button */}
          <div className="flex justify-end">
            <Button
              variant="primary"
              size="sm"
              onClick={handleExecute}
              disabled={loading}
            >
              {loading && (
                <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
              )}
              {t("execute")}
            </Button>
          </div>

          {/* Error display */}
          {error && (
            <div className="bg-[#0A0E17] border border-red-500/30 rounded-lg p-3">
              <p className="font-mono text-xs text-red-400">{error}</p>
            </div>
          )}

          {/* Result display */}
          {result && (
            <div className="bg-[#0A0E17] border border-[#1f2937] rounded-lg p-3 max-h-80 overflow-y-auto">
              <pre className="font-mono text-xs text-[#22C55E] whitespace-pre-wrap break-words">
                {result}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
