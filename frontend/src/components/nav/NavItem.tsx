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
}

export function NavItem({ href, icon: Icon, label, isActive }: NavItemProps) {
  return (
    <Link
      href={href}
      title={label}
      className={`flex items-center justify-center h-9 w-9 mx-auto rounded transition-colors
        ${
          isActive
            ? "bg-[#3b82f620] text-[#3B82F6]"
            : "text-[#6b7280] hover:text-[#9ca3af]"
        }`}
    >
      <Icon />
    </Link>
  );
}
