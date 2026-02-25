"use client";

import { FormEvent, useState } from "react";

interface CommandInputProps {
  onSubmit?: (command: string) => void;
}

export function CommandInput({ onSubmit }: CommandInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (value.trim() && onSubmit) {
      onSubmit(value.trim());
      setValue("");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="h-10 px-4 flex items-center gap-2 bg-athena-surface border-t border-athena-border"
    >
      <span className="text-xs font-mono text-athena-accent">&gt;</span>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Enter command..."
        className="flex-1 bg-transparent text-xs font-mono text-athena-text placeholder-athena-text-secondary outline-none"
      />
    </form>
  );
}
