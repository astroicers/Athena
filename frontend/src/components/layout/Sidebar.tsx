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
import { useTranslations } from "next-intl";
import { NavItem } from "@/components/nav/NavItem";
import { LocaleSwitcher } from "@/components/layout/LocaleSwitcher";

import { NAV_ITEMS } from "@/lib/constants";

export function Sidebar() {
  const pathname = usePathname();
  const t = useTranslations("Common");
  const tNav = useTranslations("Nav");

  return (
    <aside className="w-56 h-full bg-athena-surface border-r border-athena-border flex flex-col">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-athena-border">
        <h1 className="text-lg font-mono font-bold text-athena-accent tracking-wider">
          {t("appName")}
        </h1>
        <p className="text-[10px] font-mono text-athena-text-secondary mt-0.5">
          {t("subtitle")}
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-1">
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

      {/* Project Info */}
      <div className="px-4 py-3 border-t border-athena-border">
        <div className="text-xs font-mono flex items-center justify-between">
          <div>
            <a
              href="https://github.com/astroicers/Athena"
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-1.5 text-athena-text-secondary hover:text-athena-accent transition-colors"
            >
              <span className="text-yellow-400 group-hover:scale-125 transition-transform">★</span>
              astroicers/Athena
            </a>
            <p className="text-athena-text-secondary/60 mt-1">Apache-2.0</p>
          </div>
          <LocaleSwitcher />
        </div>
      </div>
    </aside>
  );
}
