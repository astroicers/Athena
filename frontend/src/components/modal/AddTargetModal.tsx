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

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/atoms/Button";

interface AddTargetModalProps {
  isOpen: boolean;
  operationId: string;
  onSuccess: () => void;
  onCancel: () => void;
}

export function AddTargetModal({
  isOpen,
  operationId,
  onSuccess,
  onCancel,
}: AddTargetModalProps) {
  const [hostname, setHostname] = useState("");
  const [ipAddress, setIpAddress] = useState("");
  const [role, setRole] = useState("target");
  const [os, setOs] = useState("");
  const [networkSegment, setNetworkSegment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hostname.trim() || !ipAddress.trim()) {
      setError("Hostname and IP address are required.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await api.post(`/operations/${operationId}/targets`, {
        hostname: hostname.trim(),
        ip_address: ipAddress.trim(),
        role,
        os: os.trim() || null,
        network_segment: networkSegment.trim() || null,
      });
      setHostname("");
      setIpAddress("");
      setRole("target");
      setOs("");
      setNetworkSegment("");
      onSuccess();
    } catch {
      setError("Failed to add target. Please check the values and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-athena-surface border-2 border-athena-border rounded-athena-lg p-6 max-w-md w-full mx-4">
        <div className="mb-4">
          <span className="text-xs font-mono text-athena-text-secondary">NEW TARGET</span>
          <h2 className="text-lg font-mono font-bold text-athena-text mt-1">Add Target Host</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Hostname <span className="text-athena-error">*</span>
            </label>
            <input
              type="text"
              value={hostname}
              onChange={(e) => setHostname(e.target.value)}
              placeholder="metasploitable"
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              IP Address <span className="text-athena-error">*</span>
            </label>
            <input
              type="text"
              value={ipAddress}
              onChange={(e) => setIpAddress(e.target.value)}
              placeholder="192.168.x.x"
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Role
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text focus:outline-none focus:border-athena-accent"
            >
              <option value="target">target</option>
              <option value="pivot">pivot</option>
              <option value="c2">c2</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              OS (optional)
            </label>
            <input
              type="text"
              value={os}
              onChange={(e) => setOs(e.target.value)}
              placeholder="Linux"
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono text-athena-text-secondary uppercase tracking-wider mb-1">
              Network Segment (optional)
            </label>
            <input
              type="text"
              value={networkSegment}
              onChange={(e) => setNetworkSegment(e.target.value)}
              placeholder="192.168.0.0/24"
              className="w-full bg-athena-bg border border-athena-border rounded-athena-sm px-3 py-2 text-sm font-mono text-athena-text placeholder-athena-text-secondary/50 focus:outline-none focus:border-athena-accent"
            />
          </div>

          {error && (
            <p className="text-xs font-mono text-athena-error">{error}</p>
          )}

          <div className="flex gap-3 justify-end pt-2">
            <Button variant="secondary" type="button" onClick={onCancel} disabled={submitting}>
              CANCEL
            </Button>
            <Button variant="primary" type="submit" disabled={submitting}>
              {submitting ? "ADDING..." : "ADD TARGET"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
