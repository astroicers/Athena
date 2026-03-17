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

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { parseBatchInput } from "@/lib/cidr";
import { Button } from "@/components/atoms/Button";

interface AddTargetModalProps {
  isOpen: boolean;
  operationId: string;
  onSuccess: () => void;
  onCancel: () => void;
}

export function AddTargetModal({
  isOpen,
  operationId,
  onSuccess,
  onCancel,
}: AddTargetModalProps) {
  const [target, setTarget] = useState("");
  const [role, setRole] = useState("target");
  const [os, setOs] = useState("");
  const [networkSegment, setNetworkSegment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Batch mode state
  const [mode, setMode] = useState<"single" | "batch">("single");
  const [batchText, setBatchText] = useState("");
  const [batchRole, setBatchRole] = useState("target");
  const [batchOs, setBatchOs] = useState("");
  const [batchSegment, setBatchSegment] = useState("");
  const [batchPreview, setBatchPreview] = useState<{ ipAddress: string; hostname: string }[] | null>(null);
  const [batchStage, setBatchStage] = useState<"input" | "preview" | "importing">("input");
  const [batchResult, setBatchResult] = useState<string | null>(null);

  const t = useTranslations("AddTarget");
  const tCommon = useTranslations("Common");
  const tRole = useTranslations("TargetRole");

  // Reset all state when modal opens
  useEffect(() => {
    if (isOpen) {
      setTarget("");
      setRole("target");
      setOs("");
      setNetworkSegment("");
      setError(null);
      setSubmitting(false);
      setMode("single");
      setBatchText("");
      setBatchRole("target");
      setBatchOs("");
      setBatchSegment("");
      setBatchPreview(null);
      setBatchStage("input");
      setBatchResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  function deriveHostname(value: string): string {
    const v = value.trim();
    if (v.includes("/")) return v;
    if (v.includes(".")) {
      const parts = v.split(".");
      const lastPart = parts[parts.length - 1];
      if (/[a-zA-Z]/.test(lastPart)) return parts[0];
    }
    return v;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!target.trim()) {
      setError(t("targetRequired"));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await api.post(`/operations/${operationId}/targets`, {
        hostname: deriveHostname(target),
        ip_address: target.trim(),
        role,
        os: os.trim() || null,
        network_segment: networkSegment.trim() || null,
      });
      setTarget("");
      setRole("target");
      setOs("");
      setNetworkSegment("");
      onSuccess();
    } catch (err) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || t("failedToAdd"));
    } finally {
      setSubmitting(false);
    }
  }

  function handlePreview() {
    setError(null);
    try {
      const entries = parseBatchInput(batchText);
      if (entries.length > 512) {
        setError(t("tooManyEntries"));
        return;
      }
      setBatchPreview(entries);
      setBatchStage("preview");
    } catch {
      setError(t("tooManyCidr"));
    }
  }

  async function handleBatchImport() {
    if (!batchPreview) return;
    setBatchStage("importing");
    setError(null);
    try {
      const result = await api.post<{
        created: string[];
        skippedDuplicates: string[];
        totalRequested: number;
        totalCreated: number;
      }>(
        `/operations/${operationId}/targets/batch`,
        {
          entries: batchPreview.map((e) => ({
            hostname: e.hostname,
            ip_address: e.ipAddress,
            role: batchRole || undefined,
            os: batchOs.trim() || undefined,
            network_segment: batchSegment.trim() || undefined,
          })),
          role: batchRole,
          os: batchOs.trim() || null,
          network_segment: batchSegment.trim() || null,
        },
      );
      setBatchResult(
        t("importResult", {
          created: result.totalCreated,
          skipped: result.skippedDuplicates.length,
        }),
      );
      setBatchStage("input");
      setBatchText("");
      setBatchPreview(null);
      onSuccess();
    } catch (err) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || t("failedToAdd"));
      setBatchStage("preview");
    }
  }

  const inputStyles =
    "w-full bg-[#0A0E17] border border-[#1f2937] rounded-athena-sm px-3 py-2 text-sm font-mono text-[#e5e7eb] placeholder-[#6b7280] focus:outline-none focus:border-[#3b82f6]";

  const labelStyles =
    "block text-sm font-mono text-[#9ca3af] uppercase tracking-wider mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0A0E17]/80 backdrop-blur-sm">
      <div className="bg-[#111827] border-2 border-[#1f2937] rounded-athena-lg p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <span className="text-xs font-mono text-[#9ca3af]">{t("newTarget")}</span>
          <h2 className="text-lg font-mono font-bold text-[#e5e7eb] mt-1">{t("addTargetTitle")}</h2>
        </div>

        {/* Tab buttons */}
        <div className="flex gap-2 mb-4">
          <Button
            variant={mode === "single" ? "primary" : "secondary"}
            size="sm"
            type="button"
            onClick={() => setMode("single")}
          >
            {t("single")}
          </Button>
          <Button
            variant={mode === "batch" ? "primary" : "secondary"}
            size="sm"
            type="button"
            onClick={() => {
              setMode("batch");
              setBatchPreview(null);
              setBatchStage("input");
              setBatchResult(null);
            }}
          >
            {t("batch")}
          </Button>
        </div>

        {/* Single mode: existing form */}
        {mode === "single" && (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className={labelStyles}>
                {t("target")} <span className="text-[#EF4444]">*</span>
              </label>
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder={t("targetPlaceholder")}
                className={inputStyles}
              />
            </div>

            <div>
              <label className={labelStyles}>
                {t("role")}
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className={inputStyles}
              >
                <option value="target">{tRole("target")}</option>
                <option value="pivot">{tRole("pivot")}</option>
                <option value="c2">{tRole("c2")}</option>
              </select>
            </div>

            <div>
              <label className={labelStyles}>
                {t("osOptional")}
              </label>
              <input
                type="text"
                value={os}
                onChange={(e) => setOs(e.target.value)}
                placeholder="Linux"
                className={inputStyles}
              />
            </div>

            <div>
              <label className={labelStyles}>
                {t("networkSegment")}
              </label>
              <input
                type="text"
                value={networkSegment}
                onChange={(e) => setNetworkSegment(e.target.value)}
                placeholder="192.168.0.0/24"
                className={inputStyles}
              />
            </div>

            {error && (
              <p className="text-xs font-mono text-[#EF4444]">{error}</p>
            )}

            <div className="flex gap-3 justify-end pt-2">
              <Button variant="secondary" type="button" onClick={onCancel} disabled={submitting}>
                {tCommon("cancel")}
              </Button>
              <Button variant="primary" type="submit" disabled={submitting}>
                {submitting ? t("adding") : t("addTarget")}
              </Button>
            </div>
          </form>
        )}

        {/* Batch mode */}
        {mode === "batch" && (
          <div className="space-y-3">
            {batchResult && (
              <p className="text-xs font-mono text-[#22C55E]">{batchResult}</p>
            )}

            {/* Stage: input */}
            {batchStage === "input" && (
              <>
                <div>
                  <label className={labelStyles}>
                    {t("target")} <span className="text-[#EF4444]">*</span>
                  </label>
                  <textarea
                    rows={6}
                    value={batchText}
                    onChange={(e) => setBatchText(e.target.value)}
                    placeholder={t("batchPlaceholder")}
                    className={inputStyles + " resize-none"}
                  />
                  <p className="text-sm font-mono text-[#9ca3af] mt-1">
                    {t("batchHelp")}
                  </p>
                </div>

                <div>
                  <label className={labelStyles}>
                    {t("role")}
                  </label>
                  <select
                    value={batchRole}
                    onChange={(e) => setBatchRole(e.target.value)}
                    className={inputStyles}
                  >
                    <option value="target">target</option>
                    <option value="pivot">pivot</option>
                    <option value="c2">c2</option>
                  </select>
                </div>

                <div>
                  <label className={labelStyles}>
                    {t("osOptional")}
                  </label>
                  <input
                    type="text"
                    value={batchOs}
                    onChange={(e) => setBatchOs(e.target.value)}
                    placeholder="Linux"
                    className={inputStyles}
                  />
                </div>

                <div>
                  <label className={labelStyles}>
                    {t("networkSegment")}
                  </label>
                  <input
                    type="text"
                    value={batchSegment}
                    onChange={(e) => setBatchSegment(e.target.value)}
                    placeholder="192.168.0.0/24"
                    className={inputStyles}
                  />
                </div>

                {error && (
                  <p className="text-xs font-mono text-[#EF4444]">{error}</p>
                )}

                <div className="flex gap-3 justify-end pt-2">
                  <Button variant="secondary" type="button" onClick={onCancel}>
                    {tCommon("cancel")}
                  </Button>
                  <Button
                    variant="primary"
                    type="button"
                    onClick={handlePreview}
                    disabled={!batchText.trim()}
                  >
                    {t("preview")}
                  </Button>
                </div>
              </>
            )}

            {/* Stage: preview */}
            {batchStage === "preview" && batchPreview && (
              <>
                <p className="text-xs font-mono text-[#e5e7eb]">
                  {t("previewTitle", { count: batchPreview.length })}
                </p>
                <div className="max-h-48 overflow-y-auto border border-[#1f2937] rounded-athena-sm bg-[#0A0E17] p-2">
                  {batchPreview.map((entry, idx) => (
                    <div
                      key={idx}
                      className="text-xs font-mono text-[#9ca3af] py-0.5"
                    >
                      {entry.ipAddress}
                      {entry.hostname !== entry.ipAddress && (
                        <span className="text-[#9ca3af] ml-2">
                          ({entry.hostname})
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                {error && (
                  <p className="text-xs font-mono text-[#EF4444]">{error}</p>
                )}

                <div className="flex gap-3 justify-end pt-2">
                  <Button
                    variant="secondary"
                    type="button"
                    onClick={() => {
                      setBatchStage("input");
                      setError(null);
                    }}
                  >
                    {t("backToEdit")}
                  </Button>
                  <Button
                    variant="primary"
                    type="button"
                    onClick={handleBatchImport}
                  >
                    {t("confirmImport")}
                  </Button>
                </div>
              </>
            )}

            {/* Stage: importing */}
            {batchStage === "importing" && (
              <div className="flex items-center justify-center py-8">
                <p className="text-sm font-mono text-[#9ca3af]">
                  {t("importing")}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
