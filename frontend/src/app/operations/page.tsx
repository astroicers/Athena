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

import { Suspense, useCallback, useEffect, useState } from "react";
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
  riskThreshold: "low" | "medium" | "high" | "critical";
  missionProfile: "SR" | "CO" | "SP";
  operatorId: string;
  createdAt: string;
  updatedAt: string;
}

/* ------------------------------------------------------------------ */
/*  Status / Profile badge helpers                                     */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<string, string> = {
  planning: "#FB923C",
  active: "var(--color-success)",
  paused: "var(--color-warning)",
  completed: "var(--color-accent)",
  failed: "var(--color-error)",
};

const PROFILE_COLORS: Record<string, string> = {
  SR: "#22D3EE",
  CO: "#A78BFA",
  SP: "var(--color-error)",
};

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function OperationsPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <OperationsContent />
    </Suspense>
  );
}

function OperationsContent() {
  const t = useTranslations("Operations");
  const router = useRouter();
  const { addToast } = useToast();
  const { setOperationId } = useOperationContext();

  const [operations, setOperations] = useState<Operation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingOp, setEditingOp] = useState<Operation | null>(null);

  /* -- Fetch operations -------------------------------------------- */
  const fetchOperations = useCallback(async () => {
    try {
      const data = await api.get<Operation[]>("/operations");
      setOperations(data);
    } catch {
      addToast(t("loadError"), "error");
    } finally {
      setLoading(false);
    }
  }, [addToast, t]);

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
          <Button variant="secondary" size="sm" onClick={() => setShowCreate(true)}>
            {t("createOp")}
          </Button>
        }
      />

      <div className="flex-1 overflow-auto px-6 py-4">
        {operations.length === 0 ? (
          /* -- Empty state ------------------------------------------ */
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-4">
              <div className="text-sm font-mono text-athena-text-tertiary">
                {t("noOperations")}
              </div>
              <Button variant="secondary" size="sm" onClick={() => setShowCreate(true)}>
                {t("createOp")}
              </Button>
            </div>
          </div>
        ) : (
          /* -- Operations grid -------------------------------------- */
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {operations.map((op) => (
              <button
                key={op.id}
                onClick={() => handleSelect(op)}
                className="text-left bg-athena-surface border border-athena-border rounded-athena hover:border-athena-accent/25 transition-colors cursor-pointer flex flex-col gap-2"
                style={{ padding: 16, height: 140 }}
              >
                {/* Header row: codename + status badge */}
                <div className="flex items-center justify-between w-full">
                  <span className="font-mono font-bold text-athena-accent truncate" style={{ fontSize: 16 }}>
                    {op.codename}
                  </span>
                  <span
                    className="text-[10px] font-mono font-semibold uppercase border rounded-athena shrink-0"
                    style={{
                      color: STATUS_COLORS[op.status],
                      borderColor: (STATUS_COLORS[op.status] || "") + "66",
                      padding: "2px 8px",
                    }}
                  >
                    {op.status}
                  </span>
                </div>

                {/* Name / strategic intent */}
                <div className="font-mono text-athena-text-tertiary truncate" style={{ fontSize: 11 }}>
                  {op.name}
                </div>

                {/* Meta row */}
                <div className="flex items-center gap-3 mt-auto">
                  {/* Mission profile badge */}
                  <span
                    className="text-[10px] font-mono font-semibold border rounded-athena"
                    style={{
                      color: PROFILE_COLORS[op.missionProfile],
                      borderColor: (PROFILE_COLORS[op.missionProfile] || "") + "66",
                      padding: "2px 6px",
                    }}
                  >
                    {op.missionProfile}
                  </span>

                  {/* OODA phase */}
                  <span className="text-[10px] font-mono text-athena-text-tertiary">
                    OODA: {op.currentOodaPhase}
                  </span>

                  {/* Created date */}
                  <span className="text-[10px] font-mono text-athena-text-secondary ml-auto">
                    {new Date(op.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))}

            {/* Empty card placeholder — "+ New Operation" */}
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center justify-center border border-athena-border/25 rounded-athena hover:border-athena-accent/25 transition-colors cursor-pointer"
              style={{ height: 140 }}
            >
              <span className="font-mono text-xs text-[#4b5563]">
                + {t("createOp")}
              </span>
            </button>
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

      {/* -- Edit operation modal ------------------------------------ */}
      {editingOp && (
        <EditOperationModal
          operation={editingOp}
          onSaved={(updated) => {
            setOperations((prev) =>
              prev.map((o) => (o.id === updated.id ? updated : o)),
            );
            setEditingOp(null);
            addToast(t("saved"), "success");
          }}
          onCancel={() => setEditingOp(null)}
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
      setError(t("requiredFields"));
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
      setError(detail || t("createError"));
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-athena-bg border border-[#374151] rounded-athena px-3 py-2 text-sm font-mono text-athena-text-light placeholder-athena-text-secondary focus:outline-none focus:border-athena-accent";
  const labelClass =
    "block text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
      <div className="bg-athena-surface border-2 border-athena-border rounded-athena p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <h2 className="text-lg font-mono font-bold text-athena-text-light">
            {t("createOp")}
          </h2>
          <p className="text-xs font-mono text-athena-text-tertiary mt-1">
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
            <Button variant="secondary" type="submit" disabled={submitting}>
              {submitting ? t("creating") : t("createOp")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Edit Operation Modal                                               */
/* ------------------------------------------------------------------ */

interface EditModalProps {
  operation: Operation;
  onSaved: (op: Operation) => void;
  onCancel: () => void;
}

function EditOperationModal({ operation, onSaved, onCancel }: EditModalProps) {
  const t = useTranslations("Operations");
  const tCommon = useTranslations("Common");

  const [status, setStatus] = useState(operation.status);
  const [automationMode, setAutomationMode] = useState(operation.automationMode);
  const [riskThreshold, setRiskThreshold] = useState(operation.riskThreshold);
  const [missionProfile, setMissionProfile] = useState(operation.missionProfile);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const updated = await api.patch<Operation>(`/operations/${operation.id}`, {
        status,
        automationMode,
        riskThreshold,
        missionProfile,
      });
      onSaved(updated);
    } catch (err) {
      const detail = (err as { detail?: string })?.detail;
      setError(detail || t("saveError"));
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-athena-bg border border-[#374151] rounded-athena px-3 py-2 text-sm font-mono text-athena-text-light placeholder-athena-text-secondary focus:outline-none focus:border-athena-accent";
  const labelClass =
    "block text-xs font-mono text-athena-text-secondary uppercase tracking-wider mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
      <div className="bg-athena-surface border-2 border-athena-border rounded-athena p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <h2 className="text-lg font-mono font-bold text-athena-text-light">
            {t("editOp")}
          </h2>
          <p className="text-xs font-mono text-athena-text-tertiary mt-1">
            {operation.codename}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Status */}
          <div>
            <label className={labelClass}>{t("editStatus")}</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as Operation["status"])}
              className={inputClass}
            >
              <option value="planning">planning</option>
              <option value="active">active</option>
              <option value="paused">paused</option>
              <option value="completed">completed</option>
              <option value="failed">failed</option>
            </select>
          </div>

          {/* Automation Mode */}
          <div>
            <label className={labelClass}>{t("automationMode")}</label>
            <select
              value={automationMode}
              onChange={(e) => setAutomationMode(e.target.value)}
              className={inputClass}
            >
              <option value="manual">{t("manual")}</option>
              <option value="semi_auto">{t("semiAuto")}</option>
              <option value="auto_full">{t("autoFull")}</option>
            </select>
          </div>

          {/* Risk Threshold */}
          <div>
            <label className={labelClass}>{t("riskThreshold")}</label>
            <select
              value={riskThreshold}
              onChange={(e) => setRiskThreshold(e.target.value as Operation["riskThreshold"])}
              className={inputClass}
            >
              <option value="low">{t("riskLow")}</option>
              <option value="medium">{t("riskMedium")}</option>
              <option value="high">{t("riskHigh")}</option>
              <option value="critical">{t("riskCritical")}</option>
            </select>
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
            <Button variant="secondary" type="submit" disabled={submitting}>
              {submitting ? t("saving") : t("editOp")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
