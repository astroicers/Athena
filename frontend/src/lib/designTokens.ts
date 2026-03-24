// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

/**
 * Design Tokens — Deep Gemstone v3
 *
 * Use these constants in JS/TS contexts where Tailwind classes are not available
 * (e.g., inline styles, canvas rendering, chart configs, dynamic color maps).
 *
 * For Tailwind contexts, use athena-* classes instead.
 * Source of truth: design/pencil-new-v2.pen → design-system/tokens.yaml
 */

export const COLORS = {
  // Background
  bgPrimary: "#09090B",
  bgSurface: "#18181B",
  bgElevated: "#27272A",

  // Accent (Sapphire Blue)
  accent: "#1E6091",
  accentHover: "#1A5276",

  // Text (Zinc Scale — WCAG AA)
  textPrimary: "#D4D4D8",
  textSecondary: "#A1A1AA",
  textTertiary: "#71717A",

  // Border (Zinc — enhanced)
  border: "#3F3F46",
  borderSubtle: "#52525B",

  // Status (Gemstone)
  success: "#059669",
  warning: "#B45309",
  error: "#B91C1C",
  critical: "#991B1B",
  info: "#1E6091",

  // OODA Phases
  phaseObserve: "#1E6091",
  phaseOrient: "#7C3AED",
  phaseDecide: "#B45309",
  phaseAct: "#059669",
} as const;

/** Status color map for dynamic contexts (charts, badges, severity) */
export const STATUS_COLORS: Record<string, string> = {
  success: COLORS.success,
  warning: COLORS.warning,
  error: COLORS.error,
  critical: COLORS.critical,
  info: COLORS.info,
};

/** OODA phase color map */
export const OODA_COLORS: Record<string, string> = {
  observe: COLORS.phaseObserve,
  orient: COLORS.phaseOrient,
  decide: COLORS.phaseDecide,
  act: COLORS.phaseAct,
};
