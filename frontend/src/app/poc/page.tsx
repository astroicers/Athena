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
import { useEffect } from "react";

export default function PocRedirect() {
  useEffect(() => {
    window.location.replace("/vulns");
  }, []);
  return null;
}
