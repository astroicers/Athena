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

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";

interface Playbook {
  id: string;
  mitreId: string;
  platform: string;
  command: string;
  outputParser: string | null;
  factsTraits: string[];
  source: string;
  tags: string[];
  createdAt: string;
}

interface PlaybookFormData {
  mitreId: string;
  platform: string;
  command: string;
  outputParser: string;
  factsTraits: string;
  tags: string;
}

const EMPTY_FORM: PlaybookFormData = {
  mitreId: "",
  platform: "linux",
  command: "",
  outputParser: "",
  factsTraits: "",
  tags: "",
};

const PLATFORM_VARIANT: Record<string, "info" | "success" | "warning"> = {
  linux: "info",
  windows: "warning",
  darwin: "success",
};

export function PlaybookBrowser() {
  const t = useTranslations("Playbooks");
  const { addToast } = useToast();

  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<PlaybookFormData>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const fetchPlaybooks = useCallback(async () => {
    try {
      const data = await api.get<Playbook[]>("/playbooks");
      setPlaybooks(data);
    } catch {
      addToast(t("loadError"), "error");
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchPlaybooks();
  }, [fetchPlaybooks]);

  const filtered = useMemo(() => {
    if (!search.trim()) return playbooks;
    const q = search.toLowerCase();
    return playbooks.filter(
      (p) =>
        p.mitreId.toLowerCase().includes(q) ||
        p.command.toLowerCase().includes(q),
    );
  }, [playbooks, search]);

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEditForm(pb: Playbook) {
    setEditingId(pb.id);
    setForm({
      mitreId: pb.mitreId,
      platform: pb.platform,
      command: pb.command,
      outputParser: pb.outputParser || "",
      factsTraits: pb.factsTraits.join(", "),
      tags: pb.tags.join(", "),
    });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  function parseCSV(val: string): string[] {
    return val
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function handleSubmit() {
    if (!form.mitreId.trim() || !form.command.trim()) return;
    setSubmitting(true);
    try {
      if (editingId) {
        const updated = await api.patch<Playbook>(`/playbooks/${editingId}`, {
          command: form.command,
          outputParser: form.outputParser || null,
          factsTraits: parseCSV(form.factsTraits),
          tags: parseCSV(form.tags),
        });
        setPlaybooks((prev) =>
          prev.map((p) => (p.id === editingId ? updated : p)),
        );
        addToast(t("updated"), "success");
      } else {
        const created = await api.post<Playbook>("/playbooks", {
          mitreId: form.mitreId,
          platform: form.platform,
          command: form.command,
          outputParser: form.outputParser || undefined,
          factsTraits: parseCSV(form.factsTraits),
          tags: parseCSV(form.tags),
        });
        setPlaybooks((prev) => [created, ...prev]);
        addToast(t("created"), "success");
      }
      closeForm();
    } catch {
      addToast(editingId ? t("updateError") : t("createError"), "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm(t("confirmDelete"))) return;
    try {
      await api.delete(`/playbooks/${id}`);
      setPlaybooks((prev) => prev.filter((p) => p.id !== id));
      addToast(t("deleted"), "success");
    } catch {
      addToast(t("deleteError"), "error");
    }
  }

  if (loading) {
    return (
      <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] p-6 text-center">
        <span className="text-athena-floor font-mono text-athena-text-tertiary">
          {t("loading")}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("search")}
          className="flex-1 bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-athena-text-light placeholder:text-athena-text-tertiary focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        />
        <Button variant="secondary" size="sm" onClick={openCreateForm}>
          {t("addPlaybook")}
        </Button>
      </div>

      {/* Create / Edit Form */}
      {showForm && (
        <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] p-4 space-y-3">
          <h3 className="text-athena-floor font-mono font-bold text-athena-text-light uppercase tracking-wider">
            {editingId ? t("editing") : t("addPlaybook")}
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-athena-floor font-mono text-athena-text-tertiary mb-1">
                {t("mitreId")} *
              </label>
              <input
                type="text"
                value={form.mitreId}
                onChange={(e) => setForm({ ...form, mitreId: e.target.value })}
                disabled={!!editingId}
                placeholder="T1059.001"
                className="w-full bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-athena-text-light disabled:opacity-50 focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
              />
            </div>
            <div>
              <label className="block text-athena-floor font-mono text-athena-text-tertiary mb-1">
                {t("platform")}
              </label>
              <select
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
                disabled={!!editingId}
                className="w-full bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-athena-text-light disabled:opacity-50 focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
              >
                <option value="linux">{t("linux")}</option>
                <option value="windows">{t("windows")}</option>
                <option value="darwin">{t("darwin")}</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-athena-floor font-mono text-athena-text-tertiary mb-1">
              {t("command")} *
            </label>
            <textarea
              value={form.command}
              onChange={(e) => setForm({ ...form, command: e.target.value })}
              rows={3}
              className="w-full bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-athena-text-light focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)] resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-athena-floor font-mono text-athena-text-tertiary mb-1">
                {t("outputParser")}
              </label>
              <input
                type="text"
                value={form.outputParser}
                onChange={(e) =>
                  setForm({ ...form, outputParser: e.target.value })
                }
                className="w-full bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-athena-text-light focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
              />
            </div>
            <div>
              <label className="block text-athena-floor font-mono text-athena-text-tertiary mb-1">
                {t("factsTraits")}
              </label>
              <input
                type="text"
                value={form.factsTraits}
                onChange={(e) =>
                  setForm({ ...form, factsTraits: e.target.value })
                }
                placeholder="trait1, trait2"
                className="w-full bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-athena-text-light focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
              />
            </div>
          </div>
          <div>
            <label className="block text-athena-floor font-mono text-athena-text-tertiary mb-1">
              {t("tags")}
            </label>
            <input
              type="text"
              value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.target.value })}
              placeholder="tag1, tag2"
              className="w-full bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-athena-text-light focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
            />
          </div>
          <div className="flex items-center gap-2 justify-end">
            <Button variant="secondary" size="sm" onClick={closeForm}>
              {t("cancel")}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSubmit}
              disabled={submitting || !form.mitreId.trim() || !form.command.trim()}
            >
              {submitting ? (editingId ? t("saving") : t("creating")) : editingId ? t("editing") : t("addPlaybook")}
            </Button>
          </div>
        </div>
      )}

      {/* Playbook List */}
      {filtered.length === 0 ? (
        <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] p-6 text-center">
          <span className="text-athena-floor font-mono text-athena-text-tertiary">
            {t("noPlaybooks")}
          </span>
        </div>
      ) : (
        <div className="bg-athena-surface border border-[var(--color-border)] rounded-[var(--radius)] overflow-hidden">
          <table className="w-full text-athena-floor font-mono">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-3 py-2 text-left text-athena-text-tertiary font-medium uppercase tracking-wider">
                  {t("mitreId")}
                </th>
                <th className="px-3 py-2 text-center text-athena-text-tertiary font-medium uppercase tracking-wider w-24">
                  {t("platform")}
                </th>
                <th className="px-3 py-2 text-left text-athena-text-tertiary font-medium uppercase tracking-wider">
                  {t("command")}
                </th>
                <th className="px-3 py-2 text-center text-athena-text-tertiary font-medium uppercase tracking-wider w-20">
                  {t("source")}
                </th>
                <th className="px-3 py-2 text-left text-athena-text-tertiary font-medium uppercase tracking-wider w-40">
                  {t("tags")}
                </th>
                <th className="px-3 py-2 text-center text-athena-text-tertiary font-medium uppercase tracking-wider w-28">
                  {t("actions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((pb) => (
                <tr
                  key={pb.id}
                  className="border-b border-[var(--color-border)]/50 hover:bg-athena-elevated cursor-pointer"
                  onClick={() => openEditForm(pb)}
                >
                  <td className="px-3 py-2 text-athena-accent font-bold">
                    {pb.mitreId}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <Badge variant={PLATFORM_VARIANT[pb.platform] || "info"}>
                      {t(pb.platform as "linux" | "windows" | "darwin")}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-athena-text-light max-w-[300px]">
                    <code className="block truncate bg-athena-bg px-2 py-1 rounded-[var(--radius)] text-athena-floor">
                      {pb.command}
                    </code>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <Badge variant={pb.source === "seed" ? "warning" : "info"}>
                      {pb.source}
                    </Badge>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {pb.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-athena-floor font-mono text-athena-accent bg-athena-accent/10 px-1.5 py-0.5 rounded-[var(--radius)]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td
                    className="px-3 py-2 text-center"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {pb.source !== "seed" && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(pb.id)}
                      >
                        {t("delete")}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
