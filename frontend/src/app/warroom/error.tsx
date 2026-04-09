// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0

"use client";

/**
 * War Room error boundary (Next.js App Router convention).
 *
 * Any uncaught render error in the War Room subtree lands here instead of
 * the default empty "Application error" screen. This matters because the
 * War Room consumes several streaming data sources (WebSocket events,
 * polling, optimistic updates) and a malformed frame can throw during
 * render before upstream guards kick in.
 *
 * This boundary is intentionally minimal: it surfaces the error message,
 * writes the full error to the browser console for DevTools inspection,
 * and offers a Retry button that re-invokes the router's reset handler.
 */

import { useEffect } from "react";
import { useTranslations } from "next-intl";

export default function WarRoomError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("WarRoom");

  useEffect(() => {
    // Emit to console so DevTools shows the full stack trace; the UI
    // only shows the message for brevity.
    // eslint-disable-next-line no-console
    console.error("[WarRoom crash]", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8 bg-zinc-950 text-zinc-200">
      <h2 className="text-xl font-mono text-red-400">
        {t("errorBoundaryTitle")}
      </h2>
      <p className="text-sm text-zinc-400 max-w-xl text-center">
        {t("errorBoundaryHint")}
      </p>
      <pre className="text-xs text-zinc-500 max-w-3xl overflow-auto whitespace-pre-wrap border border-zinc-800 rounded p-3 bg-zinc-900">
        {error.message}
      </pre>
      {error.digest && (
        <p className="text-xs text-zinc-600">digest: {error.digest}</p>
      )}
      <button
        type="button"
        onClick={reset}
        className="px-4 py-2 border border-zinc-600 rounded hover:bg-zinc-800 font-mono text-sm"
      >
        {t("errorBoundaryRetry")}
      </button>
    </div>
  );
}
