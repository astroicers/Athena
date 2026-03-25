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
import { Button } from "@/components/atoms/Button";
import { PageLoading } from "@/components/ui/PageLoading";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { RiskLevel } from "@/types/enums";

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

const STATUS_BADGE_CLASSES: Record<string, string> = {
  planning:  "bg-[#1E609120] border-[#1E609140] text-[var(--color-accent)]",
  active:    "bg-[#05966920] border-[#05966940] text-[var(--color-success)]",
  paused:    "bg-[#B4530920] border-[#B4530940] text-[var(--color-warning)]",
  completed: "bg-[#71717A20] border-[#71717A40] text-[var(--color-text-secondary)]",
  failed:    "bg-[#B91C1C20] border-[#B91C1C40] text-[var(--color-error)]",
};

const PROFILE_BADGE_CLASSES: Record<string, string> = {
  SR: "bg-[#1E609120] border-[#1E609140] text-[var(--color-accent)]",
  CO: "bg-[#7C3AED20] border-[#7C3AED40] text-[var(--color-phase-orient)]",
  SP: "bg-[#B91C1C20] border-[#B91C1C40] text-[var(--color-error)]",
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
  const [deletingOpId, setDeletingOpId] = useState<string | null>(null);

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

  /* -- Delete operation --------------------------------------------- */
  const handleDeleteOperation = async () => {
    if (!deletingOpId) return;
    try {
      await api.delete(`/operations/${deletingOpId}`);
      setDeletingOpId(null);
      fetchOperations();
    } catch {
      // handle error
    }
  };

  /* -- Loading state ------------------------------------------------ */
  if (loading) return <PageLoading />;

  return (
    <div className="flex flex-col h-full bg-[var(--color-bg-primary)]">
      {/* ── Content Area (padding 20px 24px) ──────────────────────── */}
      <div className="flex-1 overflow-auto py-5 px-6">
        {/* Top action bar */}
        <div className="flex items-center justify-end mb-4">
          <button
            onClick={() => setShowCreate(true)}
            className="font-mono text-xs font-semibold text-[var(--color-text-primary)] bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] px-3 py-1 hover:bg-[var(--color-bg-elevated)] transition-colors cursor-pointer"
          >
            + {t("createOp")}
          </button>
        </div>
        {operations.length === 0 ? (
          /* -- Empty state ------------------------------------------ */
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-4">
              <div className="text-sm font-mono text-[var(--color-text-tertiary)]">
                {t("noOperations")}
              </div>
              <button
                onClick={() => setShowCreate(true)}
                className="font-mono text-xs font-semibold text-[var(--color-text-primary)] bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] px-3 py-1 hover:bg-[var(--color-bg-elevated)] transition-colors cursor-pointer"
              >
                + {t("createOp")}
              </button>
            </div>
          </div>
        ) : (
          /* -- Operations grid (3 cols, gap 16px) ------------------- */
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {operations.map((op) => (
              <button
                key={op.id}
                onClick={() => handleSelect(op)}
                className="group relative text-left bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] hover:bg-[var(--color-bg-elevated)] hover:border-[var(--color-border-subtle)] transition-colors cursor-pointer flex flex-col gap-2 p-4 h-[140px]"
              >
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => { e.stopPropagation(); setDeletingOpId(op.id); }}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); setDeletingOpId(op.id); } }}
                  className="absolute top-3 right-3 p-1 text-[var(--color-text-tertiary)] hover:text-[var(--color-error)] transition-colors z-10"
                  title={t("deleteOperation")}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M8 6V4h8v2M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6" />
                  </svg>
                </span>
                {/* Top row: codename + status badge */}
                <div className="flex items-center justify-between w-full pr-5">
                  <span className="font-mono text-sm font-bold text-[var(--color-text-primary)] truncate">
                    {op.codename}
                  </span>
                  <span
                    className={`text-xs font-mono font-semibold uppercase border rounded-[var(--radius)] shrink-0 px-2.5 py-1 ${STATUS_BADGE_CLASSES[op.status] ?? ""}`}
                  >
                    {op.status}
                  </span>
                </div>

                {/* Description */}
                <div className="font-mono text-xs text-[var(--color-text-secondary)] truncate">
                  {op.name}
                </div>

                {/* Meta row */}
                <div className="flex items-center gap-3 mt-auto">
                  {/* Mission profile badge */}
                  <span
                    className={`text-xs font-mono font-semibold border rounded-[var(--radius)] px-2.5 py-1 ${PROFILE_BADGE_CLASSES[op.missionProfile] ?? ""}`}
                  >
                    {op.missionProfile}
                  </span>

                  {/* OODA phase */}
                  <span className="text-xs font-mono text-[var(--color-text-secondary)]">
                    OODA: {op.currentOodaPhase}
                  </span>

                  {/* Created date */}
                  <span className="text-xs font-mono text-[var(--color-text-tertiary)] ml-auto">
                    {new Date(op.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))}

            {/* Empty card placeholder -- "+ New Operation" */}
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center justify-center border border-[var(--color-border)] rounded-[var(--radius)] hover:border-[var(--color-border-subtle)] transition-colors cursor-pointer h-[140px]"
            >
              <span className="font-mono text-xs text-[var(--color-text-tertiary)]">
                +
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

      {/* -- Delete operation confirm modal ---------------------------- */}
      <HexConfirmModal
        isOpen={deletingOpId !== null}
        title={t("confirmDeleteOp")}
        riskLevel={RiskLevel.CRITICAL}
        onConfirm={handleDeleteOperation}
        onCancel={() => setDeletingOpId(null)}
      />
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
    "w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-2 text-sm font-mono text-[var(--color-text-primary)] placeholder-[var(--color-text-secondary)] focus:outline-none focus:border-[var(--color-accent)]";
  const labelClass =
    "block text-xs font-mono text-[var(--color-text-secondary)] uppercase tracking-wider mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-bg-overlay)]">
      <div className="bg-[var(--color-bg-surface)] border-2 border-[var(--color-border)] rounded-[var(--radius)] p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <h2 className="text-lg font-mono font-bold text-[var(--color-text-primary)]">
            {t("createOp")}
          </h2>
          <p className="text-xs font-mono text-[var(--color-text-tertiary)] mt-1">
            {t("subtitle")}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Code */}
          <div>
            <label className={labelClass}>
              {t("code")} <span className="text-[var(--color-error)]">*</span>
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
              {t("name")} <span className="text-[var(--color-error)]">*</span>
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
              {t("codename")} <span className="text-[var(--color-error)]">*</span>
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
            <p className="text-xs font-mono text-[var(--color-error)]">{error}</p>
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
    "w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-2 text-sm font-mono text-[var(--color-text-primary)] placeholder-[var(--color-text-secondary)] focus:outline-none focus:border-[var(--color-accent)]";
  const labelClass =
    "block text-xs font-mono text-[var(--color-text-secondary)] uppercase tracking-wider mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-bg-overlay)]">
      <div className="bg-[var(--color-bg-surface)] border-2 border-[var(--color-border)] rounded-[var(--radius)] p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <h2 className="text-lg font-mono font-bold text-[var(--color-text-primary)]">
            {t("editOp")}
          </h2>
          <p className="text-xs font-mono text-[var(--color-text-tertiary)] mt-1">
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
            <p className="text-xs font-mono text-[var(--color-error)]">{error}</p>
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
