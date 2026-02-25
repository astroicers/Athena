"use client";

import Link from "next/link";

interface NavItemProps {
  href: string;
  icon: string;
  label: string;
  isActive: boolean;
}

export function NavItem({ href, icon, label, isActive }: NavItemProps) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-3 py-2 rounded-athena-md text-sm font-mono transition-colors
        ${
          isActive
            ? "bg-athena-accent/10 text-athena-accent border-l-2 border-athena-accent"
            : "text-athena-text-secondary hover:text-athena-text hover:bg-athena-elevated"
        }`}
    >
      <span className="text-base">{icon}</span>
      <span>{label}</span>
    </Link>
  );
}
