// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useLocale } from "next-intl";
import { useTransition } from "react";
import { setLocale } from "@/app/actions";

export function LocaleSwitcher() {
  const currentLocale = useLocale();
  const [isPending, startTransition] = useTransition();

  function handleSwitch() {
    const next = currentLocale === "en" ? "zh-TW" : "en";
    startTransition(() => {
      setLocale(next);
    });
  }

  return (
    <button
      onClick={handleSwitch}
      disabled={isPending}
      className="text-xs font-mono text-athena-text-secondary hover:text-athena-accent transition-colors disabled:opacity-50"
    >
      {isPending ? "..." : currentLocale === "en" ? "中文" : "EN"}
    </button>
  );
}
