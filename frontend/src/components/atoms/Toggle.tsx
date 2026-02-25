"use client";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
}

export function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <label className="inline-flex items-center gap-2 cursor-pointer">
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors
          ${checked ? "bg-athena-accent" : "bg-athena-border"}`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform
            ${checked ? "translate-x-4.5" : "translate-x-0.5"}`}
        />
      </button>
      {label && (
        <span className="text-xs font-mono text-athena-text-secondary">
          {label}
        </span>
      )}
    </label>
  );
}
