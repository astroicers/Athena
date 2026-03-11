// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import type { OODAPhase } from "@/types/enums";
import { api } from "@/lib/api";

interface AutoLoopStatus {
  running: boolean;
  iterationsCompleted?: number;
  intervalSec?: number;
  maxIterations?: number;
}

interface LLMDirectiveInputProps {
  operationId: string;
  currentOodaPhase: OODAPhase | null;
  onSubmit: (directive: string) => Promise<void>;
  onOodaTrigger: () => Promise<void>;
}

export function LLMDirectiveInput({
  operationId,
  currentOodaPhase,
  onSubmit,
  onOodaTrigger,
}: LLMDirectiveInputProps) {
  const t = useTranslations("WarRoom");
  const [directive, setDirective] = useState("");
  const [lastDirective, setLastDirective] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [triggering, setTriggering] = useState(false);

  // Auto-loop state
  const [autoLoopRunning, setAutoLoopRunning] = useState(false);
  const [autoLoopIterations, setAutoLoopIterations] = useState(0);
  const [autoLoopToggling, setAutoLoopToggling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollAutoStatus = useCallback(async () => {
    try {
      const status = await api.get<AutoLoopStatus>(
        `/operations/${operationId}/ooda/auto-status`,
      );
      setAutoLoopRunning(status.running);
      setAutoLoopIterations(status.iterationsCompleted ?? 0);
      if (!status.running && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {
      // silently ignore poll errors
    }
  }, [operationId]);

  // Start polling when auto-loop is running
  useEffect(() => {
    if (autoLoopRunning && !pollRef.current) {
      pollRef.current = setInterval(pollAutoStatus, 10_000);
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [autoLoopRunning, pollAutoStatus]);

  // Check initial status on mount
  useEffect(() => {
    pollAutoStatus();
  }, [pollAutoStatus]);

  async function handleAutoLoopToggle() {
    if (autoLoopToggling) return;
    setAutoLoopToggling(true);
    try {
      if (autoLoopRunning) {
        await api.delete(`/operations/${operationId}/ooda/auto-stop`);
        setAutoLoopRunning(false);
        setAutoLoopIterations(0);
      } else {
        await api.post(`/operations/${operationId}/ooda/auto-start`, {
          intervalSec: 30,
          maxIterations: 0,
        });
        setAutoLoopRunning(true);
        setAutoLoopIterations(0);
        // Start polling immediately
        pollAutoStatus();
      }
    } catch {
      // If toggle fails, re-check actual status
      await pollAutoStatus();
    } finally {
      setAutoLoopToggling(false);
    }
  }

  const isCycleIdle = currentOodaPhase === null;

  // Save directive only (Enter key or small send button)
  async function handleSubmit() {
    const trimmed = directive.trim();
    if (!trimmed || sending) return;
    setSending(true);
    try {
      await onSubmit(trimmed);
      setLastDirective(trimmed);
      setDirective("");
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 2000);
    } finally {
      setSending(false);
    }
  }

  // Save directive (if any) + trigger OODA cycle
  async function handleOodaTrigger() {
    if (triggering) return;
    setTriggering(true);
    try {
      const trimmed = directive.trim();
      if (trimmed) {
        await onSubmit(trimmed);
        setLastDirective(trimmed);
        setDirective("");
      }
      await onOodaTrigger();
    } finally {
      setTriggering(false);
    }
  }

  return (
    <div className="px-3 py-2 space-y-1.5">
      {/* Directive textarea + save button */}
      <div
        className={`flex gap-2 items-end border rounded-athena-sm p-1.5 transition-colors ${
          isCycleIdle
            ? "border-athena-accent/60"
            : "border-athena-border"
        }`}
      >
        <textarea
          value={directive}
          onChange={(e) => setDirective(e.target.value)}
          placeholder={t("directivePlaceholder")}
          rows={2}
          className="flex-1 bg-transparent text-xs font-mono text-athena-text resize-none outline-none placeholder:text-athena-text-secondary/40"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!directive.trim() || sending}
          title={t("directiveSend")}
          className={`shrink-0 px-2 py-1 text-sm font-mono border rounded-athena-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            showSuccess
              ? "bg-athena-success/20 text-athena-success border-athena-success/50"
              : "bg-athena-accent/10 text-athena-accent border-athena-accent/30 hover:bg-athena-accent/20"
          }`}
        >
          {showSuccess ? "✓" : t("directiveSend")}
        </button>
      </div>

      {/* Last directive + OODA trigger */}
      <div className="flex items-center justify-between gap-2">
        {lastDirective ? (
          <div className="text-sm font-mono text-athena-text-secondary truncate min-w-0">
            {t("lastDirective")} {lastDirective}
          </div>
        ) : (
          <div />
        )}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={handleOodaTrigger}
            disabled={triggering || autoLoopRunning}
            title={t("oodaTriggerHint")}
            className="flex items-center gap-1 px-3 py-1 text-sm font-mono font-bold uppercase tracking-wider text-athena-accent bg-athena-accent/10 border border-athena-accent/40 rounded-athena-sm hover:bg-athena-accent/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ▶ {t("oodaTrigger")}
          </button>
          <button
            onClick={handleAutoLoopToggle}
            disabled={autoLoopToggling}
            title={autoLoopRunning ? t("autoLoopStopHint") : t("autoLoopStartHint")}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-sm font-mono font-bold uppercase tracking-wider border rounded-athena-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
              autoLoopRunning
                ? "text-red-400 bg-red-400/10 border-red-400/40 hover:bg-red-400/25"
                : "text-athena-text-secondary bg-athena-accent/5 border-athena-border hover:bg-athena-accent/15 hover:text-athena-accent"
            }`}
          >
            {autoLoopRunning && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
              </span>
            )}
            {autoLoopRunning ? t("autoLoopStop") : t("autoLoopStart")}
            {autoLoopRunning && autoLoopIterations > 0 && (
              <span className="text-xs text-athena-text-secondary">
                #{autoLoopIterations}
              </span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
