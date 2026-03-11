"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { DomainReport, RiskVector } from "@/types/c5isr";

interface DomainReportModalProps {
  operationId: string;
  domain: string;
  domainLabel: string;
  onClose: () => void;
}

const SEVERITY_STYLE: Record<string, string> = {
  CRIT: "bg-red-500/20 text-red-400 border-red-500/30",
  WARN: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  INFO: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

export function DomainReportModal({
  operationId,
  domain,
  domainLabel,
  onClose,
}: DomainReportModalProps) {
  const t = useTranslations("C5ISR");
  const [report, setReport] = useState<DomainReport | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<DomainReport>(
        `/operations/${operationId}/c5isr/${domain}/report`,
      );
      setReport(data);
    } catch {
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [operationId, domain]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="bg-athena-surface border border-athena-border rounded-athena-md w-[640px] max-h-[80vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-athena-border">
          <h2 className="text-sm font-mono font-bold text-athena-text uppercase tracking-wider">
            {domainLabel} — Domain Report
          </h2>
          <button
            onClick={onClose}
            className="text-athena-text-secondary hover:text-athena-text transition-colors text-sm"
          >
            x
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <span className="text-xs font-mono text-athena-text-secondary animate-pulse">
                Loading...
              </span>
            </div>
          )}

          {!loading && !report && (
            <div className="text-center py-8 text-xs font-mono text-athena-text-secondary">
              No report data available
            </div>
          )}

          {!loading && report && (
            <>
              {/* Executive Summary */}
              <p className="text-xs font-mono text-athena-text leading-relaxed">
                {report.executive_summary}
              </p>

              {/* Metrics */}
              {report.metrics.length > 0 && (
                <Section title={t("reportMetrics")}>
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="text-athena-text-secondary">
                        <th className="text-left py-1">{t("reportMetricName")}</th>
                        <th className="text-right py-1 w-20">{t("reportMetricValue")}</th>
                        <th className="text-right py-1 w-16">{t("reportMetricWeight")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.metrics.map((m) => (
                        <tr key={m.name} className="border-t border-athena-border/30">
                          <td className="py-1 text-athena-text">{m.name}</td>
                          <td className="py-1 text-right text-athena-accent font-bold">
                            {Math.round(m.value)}%
                          </td>
                          <td className="py-1 text-right text-athena-text-secondary">
                            {m.weight.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Section>
              )}

              {/* Tactical Assessment */}
              {report.tactical_assessment && (
                <Section title={t("reportTacticalAssessment")}>
                  <p className="text-xs font-mono text-athena-text leading-relaxed">
                    {report.tactical_assessment}
                  </p>
                </Section>
              )}

              {/* Risk Vectors */}
              {report.risk_vectors.length > 0 && (
                <Section title={t("reportRiskVectors")}>
                  <div className="space-y-1">
                    {report.risk_vectors.map((rv: RiskVector, i: number) => (
                      <div
                        key={i}
                        className={`px-2 py-1 rounded border text-xs font-mono ${SEVERITY_STYLE[rv.severity] ?? SEVERITY_STYLE.INFO}`}
                      >
                        <span className="font-bold mr-2">{rv.severity}</span>
                        {rv.message}
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Recommended Actions */}
              {report.recommended_actions.length > 0 && (
                <Section title={t("reportRecommendedActions")}>
                  <ul className="list-disc list-inside text-xs font-mono text-athena-text space-y-0.5">
                    {report.recommended_actions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </Section>
              )}

              {/* Cross-Domain Impacts */}
              {report.cross_domain_impacts.length > 0 && (
                <Section title={t("reportCrossDomainImpacts")}>
                  <ul className="list-disc list-inside text-xs font-mono text-athena-text-secondary space-y-0.5">
                    {report.cross_domain_impacts.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </Section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-xs font-mono font-bold text-athena-text-secondary uppercase tracking-wider mb-1.5">
        {title}
      </h3>
      {children}
    </div>
  );
}
