import { describe, expect, it } from "vitest";
import { isExtensionMessage } from "../src/shared/messages";

describe("isExtensionMessage", () => {
  it("accepts request and valid metadata", () => {
    expect(isExtensionMessage({ type: "REQUEST_MEDIA_METADATA" })).toBe(true);
    expect(
      isExtensionMessage({ type: "MEDIA_METADATA", platform: "youtube", url: "https://youtu.be/x", videos: [] }),
    ).toBe(true);
  });

  it("rejects invalid platform and shape", () => {
    expect(isExtensionMessage({ type: "MEDIA_METADATA", platform: "other", url: "x", videos: [] })).toBe(false);
    expect(isExtensionMessage({ type: "UNSUPPORTED_PAGE" })).toBe(false);
  });
});
