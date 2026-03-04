// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { ApiError } from "@/types/api";
import type { AttackPathResponse } from "@/types/attackPath";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "/api";

function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

function convertKeys(
  obj: unknown,
  converter: (s: string) => string,
): unknown {
  if (Array.isArray(obj)) {
    return obj.map((item) => convertKeys(item, converter));
  }
  if (obj !== null && typeof obj === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[converter(key)] = convertKeys(value, converter);
    }
    return result;
  }
  return obj;
}

export function toApiBody(data: unknown): unknown {
  return convertKeys(data, toSnakeCase);
}

export function fromApiResponse<T>(data: unknown): T {
  return convertKeys(data, toCamelCase) as T;
}

async function request<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = 30_000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${BASE_URL}${path}`;
  try {
    const res = await fetch(url, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions.headers,
      },
      signal: controller.signal,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      const error: ApiError = {
        status: res.status,
        detail: body.detail || res.statusText,
      };
      throw error;
    }

    if (res.status === 204) return undefined as T;

    const json = await res.json();
    return fromApiResponse<T>(json);
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  get<T>(path: string, options?: { timeoutMs?: number }): Promise<T> {
    return request<T>(path, { method: "GET", ...options });
  },

  post<T>(path: string, body?: unknown, options?: { timeoutMs?: number }): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(toApiBody(body)) : undefined,
      ...options,
    });
  },

  patch<T>(path: string, body?: unknown, options?: { timeoutMs?: number }): Promise<T> {
    return request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(toApiBody(body)) : undefined,
      ...options,
    });
  },

  delete<T>(path: string, options?: { timeoutMs?: number }): Promise<T> {
    return request<T>(path, { method: "DELETE", ...options });
  },

  getAttackPath: (opId: string) =>
    api.get<AttackPathResponse>(`/operations/${opId}/attack-path`),
};
