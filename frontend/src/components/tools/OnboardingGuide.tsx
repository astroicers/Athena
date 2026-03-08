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

import { useTranslations } from "next-intl";
import { Button } from "@/components/atoms/Button";

interface OnboardingGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

const STEPS = [
  { titleKey: "guideStep1Title", cmdKey: "guideStep1Cmd", descKey: "guideStep1Desc" },
  { titleKey: "guideStep2Title", cmdKey: "guideStep2Cmd", descKey: "guideStep2Desc" },
  { titleKey: "guideStep3Title", cmdKey: "guideStep3Cmd", descKey: "guideStep3Desc" },
  { titleKey: "guideStep4Title", cmdKey: "guideStep4Cmd", descKey: "guideStep4Desc" },
] as const;

export function OnboardingGuide({ isOpen, onClose }: OnboardingGuideProps) {
  const t = useTranslations("Tools");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
      <div className="bg-athena-surface border-2 border-athena-border rounded-athena-lg p-6 max-w-lg w-full mx-4">
        {/* Header */}
        <div className="mb-4">
          <span className="text-xs font-mono text-athena-text-secondary uppercase tracking-wider">
            {t("guideTitle")}
          </span>
          <h2 className="text-lg font-mono font-bold text-athena-text mt-1">
            {t("guideSubtitle")}
          </h2>
        </div>

        {/* Steps */}
        <div className="space-y-4">
          {STEPS.map((step, i) => (
            <div key={step.titleKey}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-athena-accent text-athena-bg text-sm font-bold">
                  {i + 1}
                </span>
                <span className="text-sm font-mono text-athena-text-secondary uppercase tracking-wider font-medium">
                  {t(step.titleKey)}
                </span>
              </div>
              <pre className="bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm text-athena-accent font-mono select-all whitespace-pre-wrap">
                {t(step.cmdKey)}
              </pre>
              <p className="text-xs font-mono text-athena-text-secondary mt-1">
                {t(step.descKey)}
              </p>
            </div>
          ))}
        </div>

        {/* Close button */}
        <div className="flex justify-end pt-4">
          <Button variant="secondary" onClick={onClose}>
            {t("guideClose")}
          </Button>
        </div>
      </div>
    </div>
  );
}
