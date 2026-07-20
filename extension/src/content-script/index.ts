import { detectPlatform } from "../platform-adapters/detect-platform";
import { isExtensionMessage, type MediaMetadata } from "../shared/messages";

function metadata(video: HTMLVideoElement): MediaMetadata {
  const rect = video.getBoundingClientRect();
  return {
    currentTimeSeconds: video.currentTime,
    durationSeconds: Number.isFinite(video.duration) ? video.duration : null,
    hasAudio: !video.muted && video.volume > 0,
    height: video.videoHeight,
    paused: video.paused,
    visible: rect.width > 0 && rect.height > 0,
    width: video.videoWidth,
  };
}

chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
  if (!isExtensionMessage(message) || message.type !== "REQUEST_MEDIA_METADATA") return false;
  const platform = detectPlatform(window.location.href);
  sendResponse(
    platform === null
      ? { type: "UNSUPPORTED_PAGE", url: window.location.href }
      : {
          type: "MEDIA_METADATA",
          platform,
          url: window.location.href,
          videos: [...document.querySelectorAll("video")].map(metadata),
        },
  );
  return false;
});
