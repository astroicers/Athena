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
        <div className="h-6 w-32 bg-[#111827] rounded-athena-sm mb-2" />
        <div className="h-20 bg-[#111827] rounded-athena-sm" />
      </div>
    );
  }

  if (!engagement) {
    return (
      <div>
        <SectionHeader level="card">{t("title")}</SectionHeader>
        <div className="bg-[#111827] border border-white/5 rounded-athena-md p-6 text-center mt-2">
          <span className="text-xs font-mono text-[#9ca3af]">
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
                variant="primary"
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

      <div className="mt-2 border border-[#1f2937] rounded-athena-sm bg-[#111827] p-3 space-y-2">
        {/* Client info */}
        <div className="flex gap-4 text-xs font-mono">
          <div>
            <span className="text-[#9ca3af]">{t("client")}: </span>
            <span className="text-[#e5e7eb]">{engagement.clientName}</span>
          </div>
          <div>
            <span className="text-[#9ca3af]">{t("contact")}: </span>
            <span className="text-[#e5e7eb]">{engagement.contactEmail}</span>
          </div>
        </div>

        {/* Scope */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs font-mono font-bold text-[#22C55E] uppercase tracking-wider mb-1">
              {t("inScope")}
            </p>
            {engagement.inScope.length > 0 ? (
              <ul className="text-xs font-mono text-[#e5e7eb] space-y-0.5">
                {engagement.inScope.map((s, i) => (
                  <li key={i} className="flex items-center gap-1">
                    <span className="text-[#22C55E]">+</span> {s}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-xs font-mono text-[#9ca3af]">--</span>
            )}
          </div>
          <div>
            <p className="text-xs font-mono font-bold text-[#EF4444] uppercase tracking-wider mb-1">
              {t("outOfScope")}
            </p>
            {engagement.outOfScope.length > 0 ? (
              <ul className="text-xs font-mono text-[#e5e7eb] space-y-0.5">
                {engagement.outOfScope.map((s, i) => (
                  <li key={i} className="flex items-center gap-1">
                    <span className="text-[#EF4444]">-</span> {s}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-xs font-mono text-[#9ca3af]">--</span>
            )}
          </div>
        </div>

        {/* Emergency contact */}
        {engagement.emergencyContact && (
          <div className="text-xs font-mono">
            <span className="text-[#9ca3af]">{t("emergency")}: </span>
            <span className="text-[#e5e7eb]">{engagement.emergencyContact}</span>
          </div>
        )}
      </div>
    </div>
  );
}
