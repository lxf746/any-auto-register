/**
 * Tests for frontend-new/src/lib/api.ts v1 fallback removal.
 *
 * Verifies that:
 * - api.ts does NOT contain v1 response format fallback
 * - api.ts only handles v2 envelope format
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const apiTsPath = resolve(__dirname, "../src/lib/api.ts");
const apiTsContent = readFileSync(apiTsPath, "utf-8");

describe("api.ts v1 fallback removal", () => {
  it("does not contain v1 format fallback", () => {
    expect(apiTsContent).not.toContain("v1 format");
  });

  it("does not return raw json without envelope check", () => {
    // After the v2 envelope check, there should be no bare 'return json as T'
    // that handles non-envelope responses
    const lines = apiTsContent.split("\n");
    const envelopeCheckLine = lines.findIndex((l) => l.includes('"ok" in json'));
    expect(envelopeCheckLine).toBeGreaterThan(-1);

    // After the envelope check block, there should be no second return statement
    // that returns json without checking ok/data
    const afterEnvelope = lines.slice(envelopeCheckLine + 5);
    const bareReturn = afterEnvelope.findIndex(
      (l) => l.trim().startsWith("return") && !l.includes("error") && l.includes("json")
    );
    expect(bareReturn).toBe(-1);
  });

  it("has ApiError class", () => {
    expect(apiTsContent).toContain("export class ApiError");
  });

  it("checks json.ok for v2 envelope", () => {
    expect(apiTsContent).toContain('json.ok');
  });
});
