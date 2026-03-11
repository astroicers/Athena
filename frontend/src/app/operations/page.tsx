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

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import { useOperationContext } from "@/contexts/OperationContext";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/atoms/Button";
import { PageLoading } from "@/components/ui/PageLoading";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Operation {
  id: string;
  code: string;
  name: string;
  codename: string;
  strategicIntent: string;
  status: "planning" | "active" | "paused" | "completed" | "failed";
  currentOodaPhase: "observe" | "orient" | "decide" | "act";
  oodaIterationCount: number;
  threatLevel: number;
  successRate: number;
  techniquesExecuted: number;
  techniquesTotal: number;
  activeAgents: number;
  automationMode: string;
  riskThreshold: number;
  missionProfile: "SR" | "CO" | "SP";
  operatorId: string;
  createdAt: string;
  updatedAt: string;
}

/* ------------------------------------------------------------------ */
/*  Status / Profile badge helpers                                     */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<string, string> = {
  planning: "text-yellow-400 border-yellow-400/40",
  active: "text-green-400 border-green-400/40",
  paused: "text-orange-400 border-orange-400/40",
  completed: "text-blue-400 border-blue-400/40",
  failed: "text-red-400 border-red-400/40",
};

const PROFILE_COLORS: Record<string, string> = {
  SR: "text-cyan-400 border-cyan-400/40",
  CO: "text-purple-400 border-purple-400/40",
  SP: "text-red-400 border-red-400/40",
};

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function OperationsPage() {
  const t = useTranslations("Operations");
  const router = useRouter();
  const { addToast } = useToast();
  const { setOperationId } = useOperationContext();

  const [operations, setOperations] = useState<Operation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  /* -- Fetch operations -------------------------------------------- */
  const fetchOperations = useCallback(async () => {
    try {
      const data = await api.get<Operation[]>("/operations");
      setOperations(data);
    } catch {
      addToast("Failed to load operations", "error");
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchOperations();
  }, [fetchOperations]);

  /* -- Select operation & navigate --------------------------------- */
  function handleSelect(op: Operation) {
    setOperationId(op.id);
    router.push("/warroom");
  }

  /* -- Loading state ------------------------------------------------ */
  if (loading) return <PageLoading />;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title={t("title")}
        trailing={
          <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
            {t("createOp")}
          </Button>
        }
      />

      <div className="flex-1 overflow-auto p-4">
        {operations.length === 0 ? (
          /* -- Empty state ------------------------------------------ */
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-4">
              <div className="text-sm font-mono text-athena-text-secondary">
                {t("noOperations")}
              </div>
              <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
                {t("createOp")}
              </Button>
            </div>
          </div>
        ) : (
          /* -- Operations grid -------------------------------------- */
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {operations.map((op) => (
              <button
                key={op.id}
                onClick={() => handleSelect(op)}
                className="text-left bg-athena-surface border border-athena-border rounded-athena-md p-4 hover:border-athena-accent/50 transition-colors cursor-pointer"
              >
                {/* Header row: codename + status badge */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-mono font-bold text-athena-accent truncate">
                    {op.codename}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold uppercase border rounded-athena-sm px-1.5 py-0.5 ${STATUS_COLORS[op.status] ?? "text-athena-text-secondary border-athena-border"}`}
                  >
                    {op.status}
                  </span>
                </div>

                {/* Name */}
                <div className="text-xs font-mono text-athena-text mb-3 truncate">
                  {op.name}
                </div>

                {/* Meta row */}
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Mission profile badge */}
                  <span
                    className={`text-[10px] font-mono font-bold border rounded-athena-sm px-1.5 py-0.5 ${PROFILE_COLORS[op.missionProfile] ?? "text-athena-text-secondary border-athena-border"}`}
                  >
                    {op.missionProfile}
                  </span>

                  {/* OODA phase */}
                  <span className="text-[10px] font-mono text-athena-text-secondary uppercase">
                    {op.currentOodaPhase}
                  </span>

                  {/* Created date */}
                  <span className="text-[10px] font-mono text-athena-text-secondary ml-auto">
                    {new Date(op.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* -- Create operation modal ---------------------------------- */}
      {showCreate && (
        <CreateOperationModal
          onCreated={(op) => {
            setOperations((prev) => [op, ...prev]);
            setShowCreate(false);
            addToast(t("created"), "success");
          }}
          onCancel={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Create Operation Modal                                             */
/* ------------------------------------------------------------------ */

interface CreateModalProps {
  onCreated: (op: Operation) => void;
  onCancel: () => void;
}

function CreateOperationModal({ onCreated, onCancel }: CreateModalProps) {
  const t = useTranslations("Operations");
  const tCommon = useTranslations("Common");

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [codename, setCodename] = useState("");
  const [strategicIntent, setStrategicIntent] = useState("");
  const [missionProfile, setMissionProfile] = useState<"SR" | "CO" | "SP">("SR");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim() || !name.trim() || !codename.trim()) {
      setError("Code, name, and codename are required.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.post<Operation>("/operations", {
        code: code.trim(),
        name: name.trim(),
        codename: codename.trim(),
        strategicIntent: strategicIntent.trim(),
        missionProfile,
      });
      onCreated(created);
    } catch (err) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || "Failed to create operation.");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent";
  const labelClass =
    "block text-sm font-mono text-athena-text-secondary uppercase tracking-wider mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
      <div className="bg-athena-surface border-2 border-athena-border rounded-athena-lg p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <h2 className="text-lg font-mono font-bold text-athena-text">
            {t("createOp")}
          </h2>
          <p className="text-xs font-mono text-athena-text-secondary mt-1">
            {t("subtitle")}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Code */}
          <div>
            <label className={labelClass}>
              {t("code")} <span className="text-athena-error">*</span>
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="op-0002"
              className={inputClass}
            />
          </div>

          {/* Name */}
          <div>
            <label className={labelClass}>
              {t("name")} <span className="text-athena-error">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="External Pentest Q1"
              className={inputClass}
            />
          </div>

          {/* Codename */}
          <div>
            <label className={labelClass}>
              {t("codename")} <span className="text-athena-error">*</span>
            </label>
            <input
              type="text"
              value={codename}
              onChange={(e) => setCodename(e.target.value)}
              placeholder="IRON TEMPEST"
              className={inputClass}
            />
          </div>

          {/* Strategic Intent */}
          <div>
            <label className={labelClass}>{t("strategicIntent")}</label>
            <textarea
              value={strategicIntent}
              onChange={(e) => setStrategicIntent(e.target.value)}
              placeholder="Assess external attack surface..."
              rows={3}
              className={`${inputClass} resize-none`}
            />
          </div>

          {/* Mission Profile */}
          <div>
            <label className={labelClass}>{t("missionProfile")}</label>
            <select
              value={missionProfile}
              onChange={(e) => setMissionProfile(e.target.value as "SR" | "CO" | "SP")}
              className={inputClass}
            >
              <option value="SR">{t("profileSR")}</option>
              <option value="CO">{t("profileCO")}</option>
              <option value="SP">{t("profileSP")}</option>
            </select>
          </div>

          {error && (
            <p className="text-xs font-mono text-athena-error">{error}</p>
          )}

          <div className="flex gap-3 justify-end pt-2">
            <Button
              variant="secondary"
              type="button"
              onClick={onCancel}
              disabled={submitting}
            >
              {tCommon("cancel")}
            </Button>
            <Button variant="primary" type="submit" disabled={submitting}>
              {submitting ? t("creating") : t("createOp")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
