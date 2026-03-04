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
