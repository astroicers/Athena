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

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { NavItem } from "@/components/nav/NavItem";
import { NAV_ITEMS } from "@/lib/constants";

export function Sidebar() {
  const pathname = usePathname();
  const tNav = useTranslations("Nav");

  return (
    <aside className="w-[200px] h-full bg-athena-surface border-r border-athena-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="pt-4 pb-3 px-3 flex items-center gap-2">
        <span className="w-7 h-7 flex items-center justify-center text-sm font-sans font-bold text-athena-text bg-athena-accent rounded-athena">A</span>
        <span className="text-xs font-mono font-bold text-athena-text tracking-wider">ATHENA</span>
      </div>

      {/* Separator */}
      <div className="mx-3 border-b border-athena-border" />

      {/* Navigation */}
      <nav className="flex-1 pt-2 px-3 flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={tNav(item.labelKey)}
            isActive={pathname === item.href}
          />
        ))}
      </nav>

      {/* Bottom star link */}
      <div className="pb-4 flex justify-center">
        <a
          href="https://github.com/astroicers/Athena"
          target="_blank"
          rel="noopener noreferrer"
          title="astroicers/Athena"
          className="text-yellow-400 hover:scale-125 transition-transform"
        >
          ★
        </a>
      </div>
    </aside>
  );
}
