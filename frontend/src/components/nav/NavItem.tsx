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

import React from "react";
import Link from "next/link";

interface NavItemProps {
  href: string;
  icon: React.ComponentType;
  label: string;
  isActive: boolean;
}

export function NavItem({ href, icon: Icon, label, isActive }: NavItemProps) {
  return (
    <Link
      href={href}
      title={label}
      className={`flex items-center gap-2.5 h-9 w-full px-2 rounded-athena transition-colors
        ${
          isActive
            ? "bg-athena-accent-bg border-l-[3px] border-athena-accent text-athena-accent font-semibold"
            : "text-athena-text-tertiary hover:text-athena-text-light hover:bg-athena-elevated"
        }`}
    >
      <Icon />
      <span className="text-xs font-mono truncate">{label}</span>
    </Link>
  );
}
