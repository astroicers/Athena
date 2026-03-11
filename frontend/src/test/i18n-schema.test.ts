import { describe, it, expect } from "vitest";
import en from "../../messages/en.json";
import zhTW from "../../messages/zh-TW.json";

/** Recursively collect keys that contain "." (invalid for next-intl). */
function findDottedKeys(
  obj: Record<string, unknown>,
  path = "",
): string[] {
  const errors: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullPath = path ? `${path}.${key}` : key;
    if (key.includes(".")) {
      errors.push(fullPath);
    }
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      errors.push(
        ...findDottedKeys(value as Record<string, unknown>, fullPath),
      );
    }
  }
  return errors;
}

/** Recursively collect all leaf key paths. */
function getKeyPaths(
  obj: Record<string, unknown>,
  prefix = "",
): string[] {
  const paths: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullPath = prefix ? `${prefix}.${key}` : key;
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      paths.push(...getKeyPaths(value as Record<string, unknown>, fullPath));
    } else {
      paths.push(fullPath);
    }
  }
  return paths;
}

describe("i18n message schema", () => {
  it("en.json has no dotted keys (next-intl requires nested objects)", () => {
    const dotted = findDottedKeys(en);
    expect(dotted).toEqual([]);
  });

  it("zh-TW.json has no dotted keys", () => {
    const dotted = findDottedKeys(zhTW);
    expect(dotted).toEqual([]);
  });

  it("en.json and zh-TW.json have identical key structure", () => {
    const enKeys = getKeyPaths(en).sort();
    const zhKeys = getKeyPaths(zhTW).sort();

    const missingInZh = enKeys.filter((k) => !zhKeys.includes(k));
    const extraInZh = zhKeys.filter((k) => !enKeys.includes(k));

    expect(missingInZh).toEqual([]);
    expect(extraInZh).toEqual([]);
  });
});
