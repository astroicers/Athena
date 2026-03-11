import { describe, it, expect } from "vitest";
import en from "../../../../messages/en.json";
import zhTW from "../../../../messages/zh-TW.json";

/**
 * FloatingNodeCard uses two namespaces: Topology and KillChain.
 * Rather than render-testing the full component (which has heavy API/hook deps),
 * we verify that all required i18n keys exist in both locales.
 */

const REQUIRED_TOPOLOGY_KEYS = [
  "tabFacts",
  "tabAI",
  "tabBasic",
  "compromised",
  "secure",
  "noFacts",
  "moreItems",
  "aiAnalyzing",
  "aiError",
  "aiRetry",
  "aiCached",
  "ip",
  "os",
  "role",
  "privilege",
  "killChain",
  "collectedFacts",
  "reconScan",
  "initialAccess",
];

const REQUIRED_KILL_CHAIN_KEYS = [
  "recon",
  "weaponize",
  "deliver",
  "exploit",
  "install",
  "c2",
  "action",
];

describe("FloatingNodeCard i18n keys", () => {
  it("en.json Topology namespace has all required keys", () => {
    const topology = en.Topology as Record<string, unknown>;
    const missing = REQUIRED_TOPOLOGY_KEYS.filter((k) => !(k in topology));
    expect(missing).toEqual([]);
  });

  it("zh-TW.json Topology namespace has all required keys", () => {
    const topology = zhTW.Topology as Record<string, unknown>;
    const missing = REQUIRED_TOPOLOGY_KEYS.filter((k) => !(k in topology));
    expect(missing).toEqual([]);
  });

  it("en.json KillChain namespace has all required keys", () => {
    const kc = en.KillChain as Record<string, unknown>;
    const missing = REQUIRED_KILL_CHAIN_KEYS.filter((k) => !(k in kc));
    expect(missing).toEqual([]);
  });

  it("zh-TW.json KillChain namespace has all required keys", () => {
    const kc = zhTW.KillChain as Record<string, unknown>;
    const missing = REQUIRED_KILL_CHAIN_KEYS.filter((k) => !(k in kc));
    expect(missing).toEqual([]);
  });
});
