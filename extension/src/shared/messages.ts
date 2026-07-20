import { supportedPlatforms, type SupportedPlatform } from "../platform-adapters/detect-platform";

export interface MediaMetadata {
  currentTimeSeconds: number;
  durationSeconds: number | null;
  hasAudio: boolean;
  height: number;
  paused: boolean;
  visible: boolean;
  width: number;
}

export type ExtensionMessage =
  | { type: "REQUEST_MEDIA_METADATA" }
  | { type: "MEDIA_METADATA"; platform: SupportedPlatform; url: string; videos: MediaMetadata[] }
  | { type: "UNSUPPORTED_PAGE"; url: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isExtensionMessage(value: unknown): value is ExtensionMessage {
  if (!isRecord(value) || typeof value.type !== "string") return false;
  if (value.type === "REQUEST_MEDIA_METADATA") return true;
  if (value.type === "UNSUPPORTED_PAGE") return typeof value.url === "string";
  return (
    value.type === "MEDIA_METADATA" &&
    typeof value.url === "string" &&
    typeof value.platform === "string" &&
    supportedPlatforms.includes(value.platform as SupportedPlatform) &&
    Array.isArray(value.videos)
  );
}
