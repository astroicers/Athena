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

import { usePathname } from "next/navigation";
import { NavItem } from "@/components/nav/NavItem";
import { StatusDot } from "@/components/atoms/StatusDot";
import { NAV_ITEMS } from "@/lib/constants";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 h-full bg-athena-surface border-r border-athena-border flex flex-col">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-athena-border">
        <h1 className="text-lg font-mono font-bold text-athena-accent tracking-wider">
          ATHENA
        </h1>
        <p className="text-[10px] font-mono text-athena-text-secondary mt-0.5">
          C5ISR Command Platform
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
            isActive={pathname === item.href}
          />
        ))}
      </nav>

      {/* System Status */}
      <div className="px-4 py-3 border-t border-athena-border">
        <div className="flex items-center gap-2 text-xs font-mono text-athena-text-secondary">
          <StatusDot status="operational" pulse />
          <span>System Operational</span>
        </div>
      </div>

      {/* User */}
      <div className="px-4 py-3 border-t border-athena-border">
        <div className="text-xs font-mono">
          <p className="text-athena-text">VIPER-1</p>
          <p className="text-athena-text-secondary">Commander</p>
        </div>
      </div>
    </aside>
  );
}
