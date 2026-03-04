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

import React from "react";
import Link from "next/link";

interface NavItemProps {
  href: string;
  icon: React.ComponentType;
  label: string;
  isActive: boolean;
  collapsed?: boolean;
}

export function NavItem({ href, icon: Icon, label, isActive, collapsed = false }: NavItemProps) {
  return (
    <Link
      href={href}
      title={collapsed ? label : undefined}
      className={`flex items-center ${collapsed ? "justify-center px-2" : "gap-3 px-3"} py-2 rounded-athena-md text-sm font-mono transition-colors
        ${
          isActive
            ? "bg-athena-accent/10 text-athena-accent border-l-2 border-athena-accent"
            : "text-athena-text-secondary hover:text-athena-text hover:bg-athena-elevated"
        }`}
    >
      <Icon />
      {!collapsed && <span>{label}</span>}
    </Link>
  );
}
