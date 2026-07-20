export const supportedPlatforms = ["youtube", "instagram", "tiktok"] as const;
export type SupportedPlatform = (typeof supportedPlatforms)[number];

export function detectPlatform(url: string): SupportedPlatform | null {
  let hostname: string;
  try {
    hostname = new URL(url).hostname.toLowerCase();
  } catch {
    return null;
  }
  if (hostname === "youtu.be" || hostname === "youtube.com" || hostname.endsWith(".youtube.com")) {
    return "youtube";
  }
  if (hostname === "instagram.com" || hostname.endsWith(".instagram.com")) {
    return "instagram";
  }
  if (hostname === "tiktok.com" || hostname.endsWith(".tiktok.com")) {
    return "tiktok";
  }
  return null;
}
