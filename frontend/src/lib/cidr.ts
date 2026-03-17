// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

/**
 * Expand a CIDR notation string into individual IP addresses.
 * Only supports IPv4. Caps at 256 hosts max per CIDR.
 * For prefix < /31: skips network address (first) and broadcast (last).
 * For /31 and /32: all addresses are valid hosts.
 */
export function expandCIDR(cidr: string): string[] {
  const [baseIp, prefixStr] = cidr.split("/");
  const prefix = parseInt(prefixStr, 10);

  // Convert dotted IP to 32-bit number
  const octets = baseIp.split(".").map(Number);
  const ipNum =
    ((octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]) >>>
    0;

  // Calculate host count from prefix
  const hostBits = 32 - prefix;
  const count = 1 << hostBits;

  if (count > 256) {
    throw new Error("CIDR range exceeds 256 hosts");
  }

  // Calculate network address (zero out host bits)
  const networkAddr = (ipNum >>> hostBits) << hostBits;

  const results: string[] = [];

  if (prefix >= 31) {
    // /31 and /32: all addresses are valid hosts
    for (let i = 0; i < count; i++) {
      results.push(numToIp((networkAddr + i) >>> 0));
    }
  } else {
    // Skip network address (first) and broadcast (last)
    for (let i = 1; i <= count - 2; i++) {
      results.push(numToIp((networkAddr + i) >>> 0));
    }
  }

  return results;
}

/** Convert a 32-bit unsigned integer to dotted IP string */
function numToIp(num: number): string {
  return [
    (num >>> 24) & 0xff,
    (num >>> 16) & 0xff,
    (num >>> 8) & 0xff,
    num & 0xff,
  ].join(".");
}

/**
 * Parse batch input text into individual entries.
 * Each line can be: an IP address, a hostname/FQDN, or a CIDR range.
 * CIDR ranges are expanded into individual IPs.
 * Returns { ipAddress, hostname } for each entry.
 */
export function parseBatchInput(
  text: string,
): { ipAddress: string; hostname: string }[] {
  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  const cidrPattern = /^\d+\.\d+\.\d+\.\d+\/\d+$/;
  const results: { ipAddress: string; hostname: string }[] = [];

  for (const line of lines) {
    if (cidrPattern.test(line)) {
      // CIDR range — expand into individual IPs
      const ips = expandCIDR(line);
      for (const ip of ips) {
        results.push({ ipAddress: ip, hostname: ip });
      }
    } else {
      // Individual IP or hostname/FQDN
      const value = line;
      let hostname = value;

      if (value.includes(".")) {
        const parts = value.split(".");
        const lastPart = parts[parts.length - 1];
        if (/[a-zA-Z]/.test(lastPart)) {
          hostname = parts[0];
        }
      }

      results.push({ ipAddress: value, hostname });
    }
  }

  return results;
}
