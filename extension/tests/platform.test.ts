import { describe, expect, it } from "vitest";
import { detectPlatform } from "../src/platform-adapters/detect-platform";

describe("detectPlatform", () => {
  it.each([
    ["https://www.youtube.com/watch?v=1", "youtube"],
    ["https://youtu.be/abc", "youtube"],
    ["https://www.instagram.com/reel/abc", "instagram"],
    ["https://www.tiktok.com/@user/video/1", "tiktok"],
  ])("detects %s", (url, expected) => {
    expect(detectPlatform(url)).toBe(expected);
  });

  it("rejects deceptive and malformed hosts", () => {
    expect(detectPlatform("https://youtube.com.evil.test/watch")).toBeNull();
    expect(detectPlatform("not a url")).toBeNull();
  });
});
