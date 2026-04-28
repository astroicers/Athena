// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use server";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

export async function setLocale(locale: string) {
  const cookieStore = await cookies();
  cookieStore.set("NEXT_LOCALE", locale, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
  });
  const headerStore = await headers();
  const referer = headerStore.get("referer");
  const url = referer ? new URL(referer) : null;
  const pathname = url ? url.pathname + url.search : "/";
  redirect(pathname);
}
