// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import enMessages from "../../messages/en.json";
import zhTWMessages from "../../messages/zh-TW.json";

// Static imports so Next.js bundles messages at build time.
// Dynamic import() of JSON at runtime fails silently during RSC streaming
// in soft navigation, causing router.push() to abort with no error.
const MESSAGES: Record<string, typeof enMessages> = {
  en: enMessages,
  "zh-TW": zhTWMessages,
};

const SUPPORTED_LOCALES = Object.keys(MESSAGES);

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const raw = cookieStore.get("NEXT_LOCALE")?.value ?? "en";
  const locale = SUPPORTED_LOCALES.includes(raw) ? raw : "en";
  return {
    locale,
    messages: MESSAGES[locale],
  };
});
