"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { SectionHeader } from "@/components/atoms/SectionHeader";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";

interface Engagement {
  id: string;
  operationId: string;
  clientName: string;
  contactEmail: string;
  scopeType: string;
  inScope: string[];
  outOfScope: string[];
  startTime: string | null;
  endTime: string | null;
  emergencyContact: string | null;
  status: string;
}

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info"> = {
  active: "success",
  draft: "warning",
  suspended: "error",
};

export function EngagementPanel({ operationId }: { operationId: string }) {
  const t = useTranslations("Engagement");
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);

  const fetchEngagement = useCallback(async () => {
    try {
      const data = await api.get<Engagement>(
        `/operations/${operationId}/engagement`,
      );
      setEngagement(data);
    } catch {
      setEngagement(null);
    } finally {
      setLoading(false);
    }
  }, [operationId]);

  useEffect(() => {
    fetchEngagement();
  }, [fetchEngagement]);

  async function handleActivate() {
    if (toggling) return;
    setToggling(true);
    try {
      const data = await api.patch<Engagement>(
        `/operations/${operationId}/engagement/activate`,
      );
      setEngagement(data);
    } catch {
      // silently fail
    } finally {
      setToggling(false);
    }
  }

  async function handleSuspend() {
    if (toggling) return;
    setToggling(true);
    try {
      const data = await api.patch<Engagement>(
        `/operations/${operationId}/engagement/suspend`,
      );
      setEngagement(data);
    } catch {
      // silently fail
    } finally {
      setToggling(false);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-6 w-32 bg-[var(--color-bg-surface)] rounded-[var(--radius)] mb-2" />
        <div className="h-20 bg-[var(--color-bg-surface)] rounded-[var(--radius)]" />
      </div>
    );
  }

  if (!engagement) {
    return (
      <div>
        <SectionHeader level="card">{t("title")}</SectionHeader>
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] p-4 text-center mt-2">
          <span className="text-[10px] font-mono text-[var(--color-text-tertiary)]">
            {t("noEngagement")}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <SectionHeader
        level="card"
        trailing={
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_VARIANT[engagement.status] ?? "info"}>
              {engagement.status.toUpperCase()}
            </Badge>
            {engagement.status === "draft" && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleActivate}
                disabled={toggling}
              >
                {t("activate")}
              </Button>
            )}
            {engagement.status === "active" && (
              <Button
                variant="danger"
                size="sm"
                onClick={handleSuspend}
                disabled={toggling}
              >
                {t("suspend")}
              </Button>
            )}
          </div>
        }
      >
        {t("title")}
      </SectionHeader>

      <div className="mt-2 border border-[var(--color-border)] rounded-[var(--radius)] bg-[var(--color-bg-surface)] px-3 py-2.5 space-y-2">
        {/* Client info */}
        <div className="flex gap-3 text-[11px] font-mono">
          <div>
            <span className="text-[var(--color-text-tertiary)]">{t("client")}: </span>
            <span className="text-[var(--color-text-primary)]">{engagement.clientName}</span>
          </div>
          <div>
            <span className="text-[var(--color-text-tertiary)]">{t("contact")}: </span>
            <span className="text-[var(--color-text-primary)]">{engagement.contactEmail}</span>
          </div>
        </div>

        {/* Scope */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <p className="text-[10px] font-mono font-bold text-[var(--color-success)] uppercase tracking-wider mb-1">
              {t("inScope")}
            </p>
            {engagement.inScope.length > 0 ? (
              <ul className="text-[11px] font-mono text-[var(--color-text-primary)] space-y-0.5">
                {engagement.inScope.map((s, i) => (
                  <li key={i} className="flex items-center gap-1">
                    <span className="text-[var(--color-success)]">+</span> {s}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-xs font-mono text-[var(--color-text-tertiary)]">--</span>
            )}
          </div>
          <div>
            <p className="text-[10px] font-mono font-bold text-[var(--color-error)] uppercase tracking-wider mb-1">
              {t("outOfScope")}
            </p>
            {engagement.outOfScope.length > 0 ? (
              <ul className="text-[11px] font-mono text-[var(--color-text-primary)] space-y-0.5">
                {engagement.outOfScope.map((s, i) => (
                  <li key={i} className="flex items-center gap-1">
                    <span className="text-[var(--color-error)]">-</span> {s}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-xs font-mono text-[var(--color-text-tertiary)]">--</span>
            )}
          </div>
        </div>

        {/* Emergency contact */}
        {engagement.emergencyContact && (
          <div className="text-[11px] font-mono">
            <span className="text-[var(--color-text-tertiary)]">{t("emergency")}: </span>
            <span className="text-[var(--color-text-primary)]">{engagement.emergencyContact}</span>
          </div>
        )}
      </div>
    </div>
  );
}
