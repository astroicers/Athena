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

import { useLocale } from "next-intl";
import { useTransition } from "react";
import { setLocale } from "@/app/actions";

export function LocaleSwitcher() {
  const currentLocale = useLocale();
  const [isPending, startTransition] = useTransition();

  function handleSwitch() {
    const next = currentLocale === "en" ? "zh-TW" : "en";
    startTransition(async () => {
      await setLocale(next);
      window.location.reload();
    });
  }

  return (
    <button
      onClick={handleSwitch}
      disabled={isPending}
      className="text-athena-floor font-mono text-athena-text-tertiary hover:text-athena-accent transition-colors disabled:opacity-50"
    >
      {isPending ? "..." : currentLocale === "en" ? "中文" : "EN"}
    </button>
  );
}
